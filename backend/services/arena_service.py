"""
Model Arena Service — DarpanAI Automated LLM Benchmarking
Orchestrates 3 parallel flagship models streaming simultaneously,
followed by a Nano model evaluation pass.
"""

import asyncio
import json
import re
from typing import AsyncGenerator, Dict, Any, List

from groq import AsyncGroq
from backend.config import settings
from backend.db.postgres import get_db

_groq = None

def _client() -> AsyncGroq:
    global _groq
    if _groq is None:
        _groq = AsyncGroq(api_key=settings.groq_api_key)
    return _groq

def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"

def _parse_json(raw: str, default):
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    m = re.search(r"[\[\{].*[\]\}]", cleaned, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    return default

# The competitors
MODELS = {
    "qwen": "qwen/qwen3.6-27b",
    "llama": "llama-3.3-70b-versatile",
    "gptoss": "openai/gpt-oss-120b"
}

NANO_EVALUATOR = "llama-3.1-8b-instant"

async def _stream_model(model_name: str, model_id: str, prompt: str, queue: asyncio.Queue):
    """Fetches streamed completion from Groq and pushes chunks to a shared queue."""
    try:
        stream = await _client().chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": "You are an expert clinical AI. Provide clear, concise, direct health advice based on the user's clinical query. Do not use overly verbose language."},
                {"role": "user", "content": prompt}
            ],
            stream=True,
            temperature=0.4,
            max_tokens=2048,
        )
        
        full_text = ""
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                full_text += content
                await queue.put({"type": "chunk", "model": model_name, "text": content})
                
        await queue.put({"type": "done", "model": model_name, "full_text": full_text})
        
    except Exception as e:
        print(f"[Arena] {model_name} failed: {e}")
        await queue.put({"type": "error", "model": model_name, "error": str(e)})


async def _evaluate_answer(model_name: str, query: str, answer: str) -> Dict[str, Any]:
    """Runs the Nano model to evaluate a single answer across 4 KPIs."""
    if not answer.strip():
        return {"model": model_name, "scores": {"clinical_accuracy": 0, "causal_reasoning": 0, "actionability": 0, "empathy_tone": 0}, "overall": 0, "critique": "Failed to generate answer"}

    prompt = f"""You are the master Judge in the SAARTHI.AI Model Arena.
Evaluate the following AI-generated clinical response against 4 specific KPIs.

USER QUERY:
{query}

AI RESPONSE TO EVALUATE:
{answer}

Rate each KPI from 0 to 100.
1. clinical_accuracy (Medically safe, free of hallucinations, logically sound)
2. structural_clarity (Well-organized, easy to read, uses proper spacing/formatting)
3. actionability (Practical, realistic, implementable interventions)
4. preciseness (Direct to the point, avoiding unnecessary fluff or clutter)

CRITICAL RULE: If the response contains raw markdown tables, massive blocks of text, or messy formatting, you MUST penalize structural_clarity and actionability heavily (score them below 50), and cap the "overall" score at a maximum of 6.5! Messy responses are dangerous for patients.

Provide an "overall" score out of 10 based on these metrics.
Provide a 1-sentence "critique".
Provide a "thought_process" string where you explain your internal reasoning. It MUST be formatted as a strict Markdown bulleted list (- point 1\\n- point 2).

You MUST ACTUALLY EVALUATE the text and generate your OWN unique scores. DO NOT copy the example values below.

Must output ONLY valid JSON format:
{{
  "scores": {{
    "clinical_accuracy": <Generate 0-100>,
    "structural_clarity": <Generate 0-100>,
    "actionability": <Generate 0-100>,
    "preciseness": <Generate 0-100>
  }},
  "overall": <Generate 0.0-10.0>,
  "thought_process": "- Evaluated clinical safety first.\\n- Structured well but cluttered with unnecessary tables.\\n- Adjusted clarity score lower due to poor spacing.",
  "critique": "<Your actual 1 sentence critique>"
}}"""

    try:
        resp = await _client().chat.completions.create(
            model=NANO_EVALUATOR,
            messages=[
                {"role": "system", "content": "You are a stark, highly critical medical judge. You output ONLY JSON. You never copy examples. You evaluate strictly focusing on clarity, structure, and precision."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=400,
            response_format={"type": "json_object"}
        )
        
        result = _parse_json(resp.choices[0].message.content, {})
        result["model"] = model_name
        return result
    except Exception as e:
        print(f"[Arena Evaluator] Failed for {model_name}: {e}")
        return {"model": model_name, "scores": {"clinical_accuracy": 0, "structural_clarity": 0, "actionability": 0, "preciseness": 0}, "overall": 0, "thought_process": "- Error occurred.", "critique": "Evaluation failed."}


async def _generate_verdict(query: str, eval_results: list, mathematical_winner: str) -> str:
    """Runs the Nano model to write a summarizing verdict for the mathematically predetermined winner."""
    prompt = f"""You are the master Judge in the SAARTHI.AI Model Arena.
The original health query was:
{query}

Here are the individual evaluations for 3 models:
{json.dumps(eval_results, indent=2)}

The mathematically highest scoring model and absolute winner is: {mathematical_winner}

Your task:
Write a 2-3 sentence "verdict" paragraph summarizing the battle. Explain exactly why {mathematical_winner} won based on its specific score advantages. Be minimal, yet pleasing and lucid.

Must output ONLY valid JSON format:
{{
  "verdict": "<Your decisive 2-3 sentence summary>"
}}"""

    try:
        resp = await _client().chat.completions.create(
            model=NANO_EVALUATOR,
            messages=[
                {"role": "system", "content": "You are the Final Judge. Output ONLY JSON. Summarize why the predetermined winner won."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=300,
            response_format={"type": "json_object"}
        )
        return _parse_json(resp.choices[0].message.content, {}).get("verdict", "Verdict resolution failed.")
    except Exception as e:
        print(f"[Arena Evaluator] Verdict failed: {e}")
        return "Verdict resolution failed due to an error."


async def stream_arena_battle(query: str, user_id: str) -> AsyncGenerator[str, None]:
    """
    1. Spawns 3 stream tasks.
    2. Yields chunks from `queue` until all 3 models finish.
    3. Runs parallel Nano evaluator mapping.
    4. Runs Arbiter Verdict.
    5. Yields evaluation verdict.
    """
    
    yield _sse({"type": "init", "message": "Arena initialized. Fetching competitors..."})
    
    queue = asyncio.Queue()
    tasks = []
    
    for m_name, m_id in MODELS.items():
        tasks.append(asyncio.create_task(_stream_model(m_name, m_id, query, queue)))
        
    finished_count = 0
    total_models = len(MODELS)
    
    final_texts = {}
    
    while finished_count < total_models:
        event = await queue.get()
        
        if event["type"] == "chunk":
            yield _sse(event)
        elif event["type"] == "done":
            finished_count += 1
            final_texts[event["model"]] = event["full_text"]
            yield _sse({"type": "model_done", "model": event["model"]})
        elif event["type"] == "error":
            finished_count += 1
            final_texts[event["model"]] = ""
            yield _sse(event)
            
    yield _sse({"type": "generation_complete", "message": "All models generated. Activating Nano Judge..."})
    
    # Run evaluation
    eval_tasks = []
    import re
    for m_name in MODELS.keys():
        cleaned_text = re.sub(r'<think>.*?(</think>|$)', '', final_texts.get(m_name, ""), flags=re.DOTALL).strip()
        eval_tasks.append(_evaluate_answer(m_name, query, cleaned_text))
        
    eval_results = list(await asyncio.gather(*eval_tasks))
    
    # Mathematical correction & Tie-breaker resolution
    winner = None
    highest_score = -1
    best_raw = -1
    best_sc = -1
    
    for res in eval_results:
        try:
            scores = res.get("scores", {})
            ca = float(scores.get("clinical_accuracy", 0))
            sc = float(scores.get("structural_clarity", 0))
            ac = float(scores.get("actionability", 0))
            pr = float(scores.get("preciseness", 0))
            
            raw_overall = (ca + sc + ac + pr) / 40.0
            true_overall = raw_overall
            
            # Cap at 6.5 if structural clarity or actionability is very poor
            if sc < 50 or ac < 50:
                true_overall = min(true_overall, 6.5)
                
            res["overall"] = round(true_overall, 1)
            
            # Tie breaking logic
            is_new_winner = False
            
            if true_overall > highest_score:
                is_new_winner = True
            elif true_overall == highest_score:
                # Tiebreaker 1: Highest raw average (uncapped)
                if raw_overall > best_raw:
                    is_new_winner = True
                elif raw_overall == best_raw:
                    # Tiebreaker 2: Structural Clarity
                    if sc > best_sc:
                        is_new_winner = True

            if is_new_winner:
                highest_score = true_overall
                best_raw = raw_overall
                best_sc = sc
                winner = res["model"]
        except:
            pass
            
    yield _sse({"type": "generation_complete", "message": "Evaluations acquired. Supreme Arbiter summarizing..."})
    
    # Run Verdict
    verdict = await _generate_verdict(query, list(eval_results), winner)
            
    yield _sse({
        "type": "evaluation_complete",
        "evaluations": eval_results,
        "winner": winner,
        "verdict": verdict
    })
