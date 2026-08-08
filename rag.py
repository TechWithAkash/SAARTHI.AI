"""
rag.py — Production Clinical RAG Pipeline
=========================================
Pure retrieval + generation engine. No UI, no Streamlit, no dashboard.
Enhanced chunking with clinical structure awareness, overlapping windows,
and Groq-powered answer generation with chain-of-thought reasoning.

Usage:
    from rag import ClinicalRAG

    rag = ClinicalRAG(corpus_dir="guideline_corpus", groq_api_key="gsk_...")
    answer = rag.query("why does belly fat raise diabetes risk")
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# =============================================================================
# Logging
# =============================================================================

logger = logging.getLogger("rag")
if not logger.handlers:
    logger.addHandler(logging.NullHandler())


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class RAGConfig:
    """All tunables with env var overrides."""

    # Corpus
    corpus_dir: str = field(
        default_factory=lambda: os.getenv("RAG_CORPUS_DIR", "guideline_corpus")
    )
    corpus_glob: str = "*.md"

    # Enhanced chunking
    chunk_size: int = 600
    chunk_overlap: int = 200
    min_chunk_len: int = 40
    max_chunks_per_doc: int = 200

    # Retrieval
    top_k: int = 8
    min_score_threshold: float = 0.02
    tfidf_ngram_max: int = 3
    tfidf_max_features: int = 10000

    # Generation
    groq_api_key: str = field(
        default_factory=lambda: os.getenv("GROQ_API_KEY", "")
    )
    groq_model: str = "llama-3.3-70b-versatile"
    generation_temperature: float = 0.3
    generation_max_tokens: int = 1500

    # System
    max_query_length: int = 3000
    cache_enabled: bool = True
    cache_ttl_seconds: int = 600


# =============================================================================
# Clinical Structure-Aware Chunking
# =============================================================================

class ClinicalChunker:
    """
    Structure-aware chunking that preserves:
    - Section headers (Markdown headings, numbered sections, ALL-CAPS headers)
    - Clinical context (what section does this chunk belong to?)
    - Chunk type classification (recommendation, warning, evidence, definition)
    - Overlapping windows to prevent splitting key clinical statements
    """

    # Clinical section pattern matchers
    HEADING_PATTERN = re.compile(
        r'^(#{1,6}\s+.+)$|'           # Markdown headings
        r'^(?:(\d+(?:\.\d+)*)\s+.+)$|' # Numbered sections (1.1, 2.3.1)
        r'^([A-Z][A-Z\s]{4,}:?)$|'     # ALL-CAPS headers
        r'^(\*\*[^*]+\*\*)$',          # Bold headers
        re.MULTILINE
    )

    # Clinical term patterns for better sentence splitting
    SENTENCE_SPLIT = re.compile(
        r'(?<=[.!?])\s+(?=[A-Z])|'     # Standard sentence boundaries
        r'(?<=\n)\s*(?=[A-Z#\d])|'     # New paragraph starting with capital/number/heading
        r'(?<=:)\s+(?=[A-Z])'          # Colon followed by new statement
    )

    def __init__(self, chunk_size: int = 600, overlap: int = 200, min_len: int = 40):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_len = min_len

    def chunk(self, text: str, source: str) -> List[Dict[str, Any]]:
        """
        Chunk clinical document into overlapping, context-rich segments.
        Returns list of chunks with metadata.
        """
        if not text or not text.strip():
            return []

        # Normalize text
        text = re.sub(r'\n{3,}', '\n\n', text.strip())

        # Extract section structure
        sections = self._extract_sections(text)

        # Chunk each section
        all_chunks = []
        global_idx = 0

        for section_path, section_text in sections:
            if not section_text.strip():
                continue

            # Split into sentences
            sentences = self._split_sentences(section_text)
            if not sentences:
                continue

            # Build overlapping chunks within this section
            section_chunks = self._build_chunks(
                sentences, section_path, source, global_idx
            )
            all_chunks.extend(section_chunks)
            global_idx += len(section_chunks)

        return all_chunks

    def _extract_sections(self, text: str) -> List[Tuple[List[str], str]]:
        """Parse document into hierarchical sections."""
        sections = []
        current_headers: List[str] = []
        current_lines: List[str] = []

        for line in text.split('\n'):
            line = line.strip()

            # Handle empty lines
            if not line:
                if current_lines:
                    current_lines.append('')
                continue

            # Check if this is a heading
            heading_match = self.HEADING_PATTERN.match(line)

            if heading_match:
                # Save current section
                if current_lines:
                    section_text = '\n'.join(current_lines).strip()
                    if section_text:
                        sections.append((list(current_headers), section_text))
                    current_lines = []

                # Determine heading level and text
                if heading_match.group(1):  # Markdown heading
                    md = heading_match.group(1)
                    level = len(md) - len(md.lstrip('#'))
                    heading_text = md.lstrip('#').strip()
                elif heading_match.group(2):  # Numbered section
                    level = heading_match.group(2).count('.') + 1
                    heading_text = line
                elif heading_match.group(3):  # ALL-CAPS
                    level = 2
                    heading_text = line.rstrip(':')
                else:  # Bold
                    level = 2
                    heading_text = line.strip('* ')

                # Update header hierarchy
                current_headers = current_headers[:max(0, level - 1)]
                current_headers.append(heading_text)
            else:
                current_lines.append(line)

        # Don't forget the last section
        if current_lines:
            section_text = '\n'.join(current_lines).strip()
            if section_text:
                sections.append((list(current_headers), section_text))

        return sections

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences, preserving clinical abbreviations."""
        # Protect common clinical abbreviations
        protected = text
        abbreviations = [
            ('Dr.', 'Dr__DOT__'),
            ('Mr.', 'Mr__DOT__'),
            ('Ms.', 'Ms__DOT__'),
            ('Prof.', 'Prof__DOT__'),
            ('e.g.', 'eg__DOT__'),
            ('i.e.', 'ie__DOT__'),
            ('etc.', 'etc__DOT__'),
            ('vs.', 'vs__DOT__'),
            ('Fig.', 'Fig__DOT__'),
            ('mg/dL', 'mg__PER__dL'),
            ('mmol/L', 'mmol__PER__L'),
        ]

        for abbr, replacement in abbreviations:
            protected = protected.replace(abbr, replacement)

        # Split sentences
        raw_sentences = self.SENTENCE_SPLIT.split(protected)

        # Restore abbreviations
        sentences = []
        for s in raw_sentences:
            s = s.strip()
            if not s:
                continue
            for abbr, replacement in abbreviations:
                s = s.replace(replacement, abbr)
            sentences.append(s)

        return sentences

    def _build_chunks(
        self,
        sentences: List[str],
        section_path: List[str],
        source: str,
        start_idx: int,
    ) -> List[Dict[str, Any]]:
        """Build overlapping chunks from sentences within a section."""
        chunks = []
        current_chunk: List[str] = []
        current_len = 0
        chunk_idx = start_idx

        for sentence in sentences:
            sent_len = len(sentence)

            # If adding this sentence exceeds chunk size, save current chunk
            if current_len + sent_len > self.chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                if len(chunk_text) >= self.min_len:
                    chunk_type = self._classify_chunk(chunk_text, section_path)
                    chunks.append({
                        'text': chunk_text,
                        'source': source,
                        'chunk_index': chunk_idx,
                        'section_path': section_path,
                        'chunk_type': chunk_type,
                        'char_length': len(chunk_text),
                        'section_depth': len(section_path),
                    })
                    chunk_idx += 1

                # Create overlap: keep last N chars worth of sentences
                overlap_sentences: List[str] = []
                overlap_len = 0
                for s in reversed(current_chunk):
                    if overlap_len + len(s) <= self.overlap:
                        overlap_sentences.insert(0, s)
                        overlap_len += len(s)
                    else:
                        break

                current_chunk = overlap_sentences
                current_len = overlap_len

            current_chunk.append(sentence)
            current_len += sent_len

        # Last chunk in section
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            if len(chunk_text) >= self.min_len:
                chunk_type = self._classify_chunk(chunk_text, section_path)
                chunks.append({
                    'text': chunk_text,
                    'source': source,
                    'chunk_index': chunk_idx,
                    'section_path': section_path,
                    'chunk_type': chunk_type,
                    'char_length': len(chunk_text),
                    'section_depth': len(section_path),
                })

        return chunks

    def _classify_chunk(self, text: str, section_path: List[str]) -> str:
        """
        Classify chunk as: recommendation, warning, evidence, definition, mechanism, or general.
        Uses weighted keyword matching against both chunk text and section headers.
        """
        combined = ' '.join(section_path + [text]).lower()

        # Weighted classification rules
        rules = [
            ('warning', ['contraindication', 'warning', 'caution', 'do not use',
                        'avoid', 'adverse effect', 'side effect', 'risk of',
                        'not recommended', 'should not'], 3),
            ('recommendation', ['recommend', 'should be', 'guideline recommends',
                               'class i', 'class ii', 'indicated for', 'first-line',
                               'standard of care', 'treatment of choice'], 3),
            ('evidence', ['study shows', 'trial demonstrated', 'meta-analysis',
                         'cohort study', 'odds ratio', 'hazard ratio', 'p <',
                         'p=', 'confidence interval', 'n =', 'n=', 'significant',
                         'randomized', 'controlled trial'], 3),
            ('mechanism', ['mechanism', 'pathway', 'signaling', 'receptor',
                          'enzyme', 'metabolism', 'oxidative', 'inflammatory',
                          'cytokine', 'insulin resistance', 'glucose uptake'], 2),
            ('definition', ['defined as', 'refers to', 'is a condition',
                           'characterized by', 'diagnosis of', 'classified as',
                           'measured by', 'calculated as'], 2),
        ]

        scores = defaultdict(int)
        for chunk_type, keywords, weight in rules:
            for kw in keywords:
                if kw in combined:
                    scores[chunk_type] += weight

        if scores:
            return max(scores, key=scores.get)
        return 'general'


# =============================================================================
# Document Loader
# =============================================================================

class DocumentLoader:
    """Loads and manages clinical guideline documents."""

    def __init__(self, corpus_dir: str, glob_pattern: str = "*.md"):
        self.corpus_dir = Path(corpus_dir)
        self.glob_pattern = glob_pattern

    def load_all(self) -> List[Dict[str, Any]]:
        """Load all documents with metadata."""
        if not self.corpus_dir.exists():
            logger.warning(f"Corpus directory not found: {self.corpus_dir}")
            return []

        documents = []
        for filepath in sorted(self.corpus_dir.glob(self.glob_pattern)):
            try:
                text = filepath.read_text(encoding='utf-8')
                documents.append({
                    'source': filepath.stem,
                    'filename': filepath.name,
                    'text': text,
                    'size_bytes': len(text.encode('utf-8')),
                    'mtime': filepath.stat().st_mtime,
                })
                logger.info(f"Loaded: {filepath.name} ({len(text)} chars)")
            except Exception as e:
                logger.error(f"Failed to load {filepath}: {e}")

        logger.info(f"Loaded {len(documents)} documents")
        return documents


# =============================================================================
# TF-IDF Retriever
# =============================================================================

class TfidfRetriever:
    """TF-IDF + cosine similarity retrieval with n-gram support."""

    def __init__(self, ngram_max: int = 3, max_features: int = 10000):
        self.ngram_max = ngram_max
        self.max_features = max_features
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.matrix = None
        self.chunks: List[Dict[str, Any]] = []
        self.is_fitted = False
        self._lock = threading.RLock()

    def fit(self, chunks: List[Dict[str, Any]]) -> None:
        """Build TF-IDF index from chunks."""
        with self._lock:
            self.chunks = chunks
            texts = []
            for c in chunks:
                # Enrich text with section context and type
                section = ' > '.join(c.get('section_path', []))
                chunk_type = c.get('chunk_type', 'general')
                text = c['text']

                # Build enriched search text
                parts = []
                if section:
                    parts.append(f"[{section}]")
                parts.append(f"[{chunk_type}]")
                parts.append(text)
                enriched = ' '.join(parts)
                texts.append(enriched)

            self.vectorizer = TfidfVectorizer(
                ngram_range=(1, self.ngram_max),
                stop_words='english',
                max_features=self.max_features,
                sublinear_tf=True,
                strip_accents='unicode',
            )

            self.matrix = self.vectorizer.fit_transform(texts)
            self.is_fitted = True

            logger.info(
                f"TF-IDF index built: {len(chunks)} chunks, "
                f"vocab={len(self.vectorizer.vocabulary_)}, "
                f"ngram_range=(1,{self.ngram_max})"
            )

    def query(self, query: str, top_k: int = 8, min_score: float = 0.02) -> List[Dict[str, Any]]:
        """Retrieve top-k chunks for a query."""
        with self._lock:
            if not self.is_fitted:
                return []

            # Expand query with clinical synonyms for better matching
            expanded_query = self._expand_query(query)

            # Vectorize and score
            query_vec = self.vectorizer.transform([expanded_query])
            scores = cosine_similarity(query_vec, self.matrix).flatten()

            # Get top-k efficiently
            if len(scores) <= top_k:
                top_indices = np.argsort(scores)[::-1]
            else:
                top_indices = np.argpartition(scores, -top_k)[-top_k:]
                top_indices = top_indices[np.argsort(scores[top_indices])][::-1]

            # Build results
            results = []
            for idx in top_indices:
                score = float(scores[idx])
                if score < min_score:
                    continue

                chunk = dict(self.chunks[idx])
                chunk['score'] = round(score, 4)
                chunk['confidence'] = self._confidence(score)
                results.append(chunk)

            return results

    def _expand_query(self, query: str) -> str:
        """Expand query with clinical synonyms for better recall."""
        synonyms = {
            'diabetes': 'diabetes diabetic dm type2 t2dm hyperglycemia',
            'blood pressure': 'blood pressure bp hypertension hypertensive systolic diastolic',
            'heart': 'heart cardiac cardiovascular cvd coronary',
            'obesity': 'obesity obese overweight bmi adiposity abdominal central visceral',
            'cholesterol': 'cholesterol ldl hdl lipid hyperlipidemia dyslipidemia',
            'glucose': 'glucose sugar blood sugar fasting glucose hba1c a1c',
            'kidney': 'kidney renal nephropathy ckd',
            'liver': 'liver hepatic nafld fatty liver',
            'inflammation': 'inflammation inflammatory cytokine crp',
            'risk': 'risk risk factor odds ratio hazard ratio relative risk',
        }

        expanded = query
        for term, expansion in synonyms.items():
            if term in query.lower():
                expanded += ' ' + expansion

        return expanded

    def _confidence(self, score: float) -> float:
        """Calibrated confidence from raw cosine similarity."""
        if score >= 0.30:
            return min(1.0, 0.7 + (score - 0.30) / 0.20 * 0.3)
        elif score >= 0.15:
            return 0.4 + (score - 0.15) / 0.15 * 0.3
        elif score >= 0.05:
            return 0.1 + (score - 0.05) / 0.10 * 0.3
        elif score > 0:
            return score / 0.05 * 0.1
        return 0.0


# =============================================================================
# Groq Generator — Enhanced Reasoning
# =============================================================================

class GroqGenerator:
    """Generates answers using Groq with chain-of-thought reasoning."""

    def __init__(
        self,
        api_key: str,
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.3,
        max_tokens: int = 1500,
    ):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize Groq client."""
        if not self.api_key:
            logger.warning("No Groq API key provided — generation disabled")
            return
        try:
            from groq import Groq
            self.client = Groq(api_key=self.api_key)
            logger.info(f"Groq client ready: {self.model}")
        except ImportError:
            logger.error("Install groq: pip install groq")
        except Exception as e:
            logger.error(f"Groq init failed: {e}")

    @property
    def available(self) -> bool:
        return self.client is not None

    def generate(self, query: str, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate answer with chain-of-thought reasoning from retrieved context."""
        if not self.available:
            return {
                'answer': None,
                'error': 'Groq API key not configured',
                'sources_used': [],
            }

        if not context_chunks:
            return {
                'answer': (
                    "No relevant clinical guidelines were found for this question. "
                    "The system honestly reports this rather than fabricating an answer. "
                    "Consider rephrasing your question or consulting a different source."
                ),
                'error': None,
                'sources_used': [],
            }

        # Build structured context with provenance
        context_blocks = []
        sources_used = set()

        for i, chunk in enumerate(context_chunks):
            source = chunk['source'].replace('_', ' ').title()
            chunk_type = chunk.get('chunk_type', 'general')
            section = ' > '.join(chunk.get('section_path', []))
            score = chunk.get('score', 0)

            sources_used.add(source)

            header = f"[EXCERPT {i+1}] Source: {source}"
            if section:
                header += f" | Section: {section}"
            header += f" | Type: {chunk_type.upper()} | Relevance: {score:.3f}"

            context_blocks.append(f"{header}\n{chunk['text']}")

        context = '\n\n' + '\n\n---\n\n'.join(context_blocks) + '\n\n'

        # Build system prompt for chain-of-thought reasoning
        system_prompt = """You are a clinical reasoning assistant. Follow this structure:

STEP 1 — IDENTIFY KEY FACTS: Extract the most relevant clinical facts from the excerpts provided.

STEP 2 — ANALYZE MECHANISMS: If the question asks "why" or "how", explain the biological/physiological mechanisms using ONLY information from the excerpts.

STEP 3 — CITE EVIDENCE: For each claim, cite the specific source and excerpt number in parentheses. Note the evidence type (recommendation, warning, evidence from studies, mechanism explanation).

STEP 4 — STATE LIMITATIONS: If the excerpts don't fully answer the question, explicitly state what's missing. Never invent or assume information not in the excerpts.

STEP 5 — SUMMARIZE: Provide a clear, concise answer that synthesizes all relevant excerpts.

RULES:
- Use ONLY the provided excerpts. Do not use external knowledge.
- Cite sources: [Excerpt 1], [Excerpt 2], etc.
- Note when an excerpt is a [RECOMMENDATION] vs [EVIDENCE] vs [WARNING]
- If excerpts conflict, note the conflict
- If the question cannot be answered from the excerpts, say so clearly
- Be specific about study findings when cited (e.g., "a cohort study of 10,000+ individuals showed...")"""

        user_prompt = f"""CLINICAL GUIDELINE EXCERPTS:
{context}

USER QUESTION: {query}

Please analyze the excerpts and answer the question following the reasoning steps."""

        start_time = time.time()

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )

            elapsed = time.time() - start_time
            answer = response.choices[0].message.content

            return {
                'answer': answer,
                'error': None,
                'sources_used': sorted(sources_used),
                'elapsed_seconds': round(elapsed, 2),
                'model': self.model,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens if hasattr(response, 'usage') else 0,
                    'completion_tokens': response.usage.completion_tokens if hasattr(response, 'usage') else 0,
                    'total_tokens': response.usage.total_tokens if hasattr(response, 'usage') else 0,
                },
            }

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return {
                'answer': None,
                'error': str(e),
                'sources_used': sorted(sources_used),
                'elapsed_seconds': time.time() - start_time,
            }


# =============================================================================
# Complete Clinical RAG Pipeline
# =============================================================================

class ClinicalRAG:
    """
    Complete clinical RAG pipeline: Load → Chunk → Index → Retrieve → Generate.

    Usage:
        rag = ClinicalRAG(corpus_dir="guideline_corpus", groq_api_key="gsk_...")
        result = rag.query("why does belly fat raise diabetes risk?")
        print(result['answer'])
    """

    def __init__(
        self,
        corpus_dir: str = "guideline_corpus",
        groq_api_key: str = "",
        config: Optional[RAGConfig] = None,
    ):
        self.config = config or RAGConfig(
            corpus_dir=corpus_dir,
            groq_api_key=groq_api_key or os.getenv("GROQ_API_KEY", ""),
        )

        # Initialize components
        self.loader = DocumentLoader(self.config.corpus_dir, self.config.corpus_glob)
        self.chunker = ClinicalChunker(
            chunk_size=self.config.chunk_size,
            overlap=self.config.chunk_overlap,
            min_len=self.config.min_chunk_len,
        )
        self.retriever = TfidfRetriever(
            ngram_max=self.config.tfidf_ngram_max,
            max_features=self.config.tfidf_max_features,
        )
        self.generator = GroqGenerator(
            api_key=self.config.groq_api_key,
            model=self.config.groq_model,
            temperature=self.config.generation_temperature,
            max_tokens=self.config.generation_max_tokens,
        )

        # State
        self.documents: List[Dict[str, Any]] = []
        self.chunks: List[Dict[str, Any]] = []
        self.is_ready = False

        # Cache
        self._cache: Dict[str, Tuple[float, Any]] = {}
        self._cache_lock = threading.RLock()

        # Build index
        self._build()

    def _build(self):
        """Load documents, chunk, and build retrieval index."""
        logger.info("=" * 50)
        logger.info("Building Clinical RAG Pipeline")
        logger.info("=" * 50)

        start = time.time()

        # Load
        self.documents = self.loader.load_all()
        if not self.documents:
            logger.warning("No documents found — knowledge base is empty")
            return

        logger.info(f"Documents: {len(self.documents)}")

        # Chunk
        self.chunks = []
        for doc in self.documents:
            doc_chunks = self.chunker.chunk(doc['text'], doc['source'])
            self.chunks.extend(doc_chunks)
            logger.info(f"  {doc['source']}: {len(doc_chunks)} chunks")

        logger.info(f"Total chunks: {len(self.chunks)}")

        # Chunk type distribution
        type_counts = defaultdict(int)
        for c in self.chunks:
            type_counts[c.get('chunk_type', 'general')] += 1
        logger.info(f"Chunk types: {dict(type_counts)}")

        # Average chunk size
        avg_size = int(np.mean([c['char_length'] for c in self.chunks]))
        logger.info(f"Average chunk size: {avg_size} chars")

        # Index
        self.retriever.fit(self.chunks)
        self.is_ready = True

        elapsed = time.time() - start
        logger.info(f"Pipeline ready in {elapsed:.1f}s")
        logger.info("=" * 50)

    def query(self, query: str) -> Dict[str, Any]:
        """
        End-to-end RAG query: Retrieve → Generate.

        Args:
            query: Clinical question string

        Returns:
            Dict with keys: answer, chunks_retrieved, sources_used,
                           retrieval_ms, generation_ms, total_ms, error
        """
        if not self.is_ready:
            return {
                'answer': "System not ready — no documents loaded. Check corpus directory.",
                'chunks_retrieved': [],
                'sources_used': [],
                'retrieval_ms': 0,
                'generation_ms': 0,
                'total_ms': 0,
                'error': 'system_not_ready',
            }

        if not query or not query.strip():
            return {
                'answer': None,
                'chunks_retrieved': [],
                'sources_used': [],
                'retrieval_ms': 0,
                'generation_ms': 0,
                'total_ms': 0,
                'error': 'empty_query',
            }

        # Truncate
        query = query.strip()[:self.config.max_query_length]

        # Check cache
        cache_key = hashlib.md5(query.encode()).hexdigest()
        if self.config.cache_enabled:
            with self._cache_lock:
                cached = self._cache.get(cache_key)
                if cached:
                    cache_time, cached_result = cached
                    if time.time() - cache_time < self.config.cache_ttl_seconds:
                        logger.info(f"Cache hit: {cache_key[:8]}")
                        return cached_result

        total_start = time.time()

        # Step 1: Retrieve
        retrieval_start = time.time()
        retrieved = self.retriever.query(
            query,
            top_k=self.config.top_k,
            min_score=self.config.min_score_threshold,
        )
        retrieval_ms = (time.time() - retrieval_start) * 1000

        logger.info(
            f"Query: '{query[:80]}...' → {len(retrieved)} chunks in {retrieval_ms:.0f}ms"
        )

        if retrieved:
            top_chunk = retrieved[0]
            logger.info(
                f"  Top: [{top_chunk['source']}] [{top_chunk.get('chunk_type', '?')}] "
                f"score={top_chunk['score']:.4f}"
            )

        # Step 2: Generate
        generation_start = time.time()
        gen_result = self.generator.generate(query, retrieved)
        generation_ms = (time.time() - generation_start) * 1000

        total_ms = (time.time() - total_start) * 1000

        # Build result
        result = {
            'query': query,
            'answer': gen_result.get('answer'),
            'chunks_retrieved': [
                {
                    'text': c['text'][:300],
                    'source': c['source'],
                    'score': c['score'],
                    'confidence': c['confidence'],
                    'chunk_type': c.get('chunk_type', 'general'),
                    'section_path': c.get('section_path', []),
                }
                for c in retrieved
            ],
            'num_chunks_retrieved': len(retrieved),
            'sources_used': gen_result.get('sources_used', []),
            'retrieval_ms': round(retrieval_ms, 2),
            'generation_ms': round(generation_ms, 2),
            'total_ms': round(total_ms, 2),
            'model': gen_result.get('model'),
            'token_usage': gen_result.get('usage', {}),
            'error': gen_result.get('error'),
        }

        # Cache result
        if self.config.cache_enabled and not gen_result.get('error'):
            with self._cache_lock:
                self._cache[cache_key] = (time.time(), result)

        return result

    def retrieve_only(self, query: str) -> List[Dict[str, Any]]:
        """Retrieve without generation — for debugging or external use."""
        if not self.is_ready:
            return []

        query = query.strip()[:self.config.max_query_length]
        return self.retriever.query(
            query,
            top_k=self.config.top_k,
            min_score=self.config.min_score_threshold,
        )

    def reload(self):
        """Force rebuild of the entire pipeline."""
        self._cache.clear()
        self._build()

    def stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        type_counts = defaultdict(int)
        source_counts = defaultdict(int)
        for c in self.chunks:
            type_counts[c.get('chunk_type', 'general')] += 1
            source_counts[c['source']] += 1

        return {
            'ready': self.is_ready,
            'documents': len(self.documents),
            'chunks': len(self.chunks),
            'avg_chunk_size': int(np.mean([c['char_length'] for c in self.chunks])) if self.chunks else 0,
            'chunk_types': dict(type_counts),
            'chunks_by_source': dict(source_counts),
            'generator_available': self.generator.available,
            'model': self.config.groq_model,
            'cache_size': len(self._cache),
            'corpus_dir': self.config.corpus_dir,
        }


# =============================================================================
# Quick test
# =============================================================================

if __name__ == "__main__":
    import sys

    # Setup logging for CLI
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        stream=sys.stderr,
    )

    # Get config from env
    corpus_dir = os.getenv("RAG_CORPUS_DIR", "guideline_corpus")
    groq_key = os.getenv("GROQ_API_KEY", "")

    print("=" * 60)
    print("Clinical RAG Pipeline — CLI Test")
    print("=" * 60)

    # Initialize
    rag = ClinicalRAG(corpus_dir=corpus_dir, groq_api_key=groq_key)

    # Show stats
    stats = rag.stats()
    print(f"\nPipeline Status: {'✅ Ready' if stats['ready'] else '❌ Not Ready'}")
    print(f"Documents: {stats['documents']}")
    print(f"Chunks: {stats['chunks']}")
    print(f"Avg chunk size: {stats['avg_chunk_size']} chars")
    print(f"Chunk types: {stats['chunk_types']}")
    print(f"Generator: {'✅ Available' if stats['generator_available'] else '❌ No API key'}")

    # Test queries
    test_queries = [
        "Why does abdominal obesity increase the risk of type 2 diabetes in Indians?",
        "What are the key cardiovascular risk factors according to INTERHEART?",
        "How should hypertension be classified and managed?",
    ]

    for query in test_queries:
        print(f"\n{'=' * 60}")
        print(f"QUERY: {query}")
        print('=' * 60)

        result = rag.query(query)

        print(f"\nRetrieved: {result['num_chunks_retrieved']} chunks in {result['retrieval_ms']}ms")
        print(f"Sources found: {result['sources_used']}")

        if result['chunks_retrieved']:
            print("\nTop chunks:")
            for i, c in enumerate(result['chunks_retrieved'][:3]):
                print(f"  {i+1}. [{c['source']}] [{c['chunk_type']}] "
                      f"score={c['score']:.4f} conf={c['confidence']:.2f}")
                print(f"     {c['text'][:150]}...")

        if result['answer']:
            print(f"\n{'─' * 60}")
            print("ANSWER:")
            print(result['answer'])
            print(f"{'─' * 60}")
            print(f"Generation: {result['generation_ms']}ms | Total: {result['total_ms']}ms")
            if result['token_usage']:
                print(f"Tokens: {result['token_usage']}")
        else:
            print(f"\nNo answer generated. Error: {result.get('error', 'unknown')}")