"use client";

import { useEffect, useRef, useState, useCallback } from "react";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
}

interface DocSession {
  session_id: string;
  filename: string;
  chunk_count: number;
  preview: string;
}

const INITIAL_CHIPS = [
  "What's driving my risk score?",
  "Explain my causal chain",
  "What if my stress drops to 3?",
  "Which metric should I fix first?",
];

const DOC_CHIPS = [
  "Summarise this report",
  "What are the abnormal values?",
  "What do these results mean for me?",
  "What should I do about this?",
];

const WELCOME_MSG: Message = {
  id: "welcome",
  role: "assistant",
  content: `**Hello, I'm Saarthi** — your Smart AI Health Guide.\n\nI have full access to your health profile including your risk score, SHAP explainability data, causal analysis, and 120-day simulation projections.\n\nYou can also **upload a blood report or any medical document** (PDF, image) and I'll answer questions directly from it.\n\nAsk me anything about your health data — I'll give you specific, data-driven answers.`,
};

const ACCEPTED_TYPES = ".pdf,.txt,.md,.png,.jpg,.jpeg,.webp,.csv";

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([WELCOME_MSG]);
  const [input, setInput] = useState("");
  const [chips, setChips] = useState<string[]>(INITIAL_CHIPS);
  const [isStreaming, setIsStreaming] = useState(false);
  const [userId, setUserId] = useState("");
  const [docSession, setDocSession] = useState<DocSession | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const uid = sessionStorage.getItem("saarthi_user_id") ?? sessionStorage.getItem("darpan_user_id") ?? "user_demo_001";
    setUserId(uid);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── Document upload ──────────────────────────────────────────────────────
  async function handleUpload(file: File) {
    if (!file || !userId) return;
    setUploading(true);
    setUploadError(null);

    try {
      const form = new FormData();
      form.append("user_id", userId);
      form.append("file", file);

      const res = await fetch(`${BASE}/chat/upload`, {
        method: "POST",
        body: form,
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Upload failed");

      setDocSession(data);
      setChips(DOC_CHIPS);

      // Add system message showing doc loaded
      const sysMsg: Message = {
        id: `doc-${Date.now()}`,
        role: "assistant",
        content: `📄 **Document loaded: ${data.filename}**\n\nI've read and indexed ${data.chunk_count} sections from your document. You can now ask me anything about it — I'll answer directly from the content and cross-reference it with your health profile.\n\n_Preview: ${data.preview.slice(0, 180)}${data.preview.length > 180 ? "..." : ""}_`,
      };
      setMessages((prev) => [...prev, sysMsg]);
    } catch (err: any) {
      setUploadError(err.message ?? "Failed to process document");
    } finally {
      setUploading(false);
    }
  }

  function handleFileInput(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
    e.target.value = "";
  }

  async function handleRemoveDoc() {
    if (!docSession) return;
    await fetch(`${BASE}/chat/upload/${docSession.session_id}`, { method: "DELETE" });
    setDocSession(null);
    setChips(INITIAL_CHIPS);
    const sysMsg: Message = {
      id: `undoc-${Date.now()}`,
      role: "assistant",
      content: "Document removed. I'm back to answering from your live health profile.",
    };
    setMessages((prev) => [...prev, sysMsg]);
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(true);
  }
  function handleDragLeave() { setDragOver(false); }
  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleUpload(file);
  }

  // ── Chat ─────────────────────────────────────────────────────────────────
  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isStreaming || !userId) return;

      const userMsg: Message = {
        id: Date.now().toString(),
        role: "user",
        content: text.trim(),
      };
      const assistantId = (Date.now() + 1).toString();
      const assistantMsg: Message = { id: assistantId, role: "assistant", content: "", streaming: true };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setInput("");
      setIsStreaming(true);

      const history = messages
        .filter((m) => m.id !== "welcome" && !m.id.startsWith("doc-") && !m.id.startsWith("undoc-"))
        .map((m) => ({ role: m.role, content: m.content }));

      abortRef.current = new AbortController();

      try {
        const res = await fetch(`${BASE}/chat/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: userId,
            message: text.trim(),
            history,
            doc_session_id: docSession?.session_id ?? null,
          }),
          signal: abortRef.current.signal,
        });

        if (!res.ok || !res.body) throw new Error("Stream failed");

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            try {
              const evt = JSON.parse(line.slice(6));
              if (evt.type === "token") {
                setMessages((prev) =>
                  prev.map((m) => m.id === assistantId ? { ...m, content: m.content + evt.content } : m)
                );
              }
              if (evt.type === "done") {
                setChips(evt.chips?.length ? evt.chips : (docSession ? DOC_CHIPS : INITIAL_CHIPS));
                setMessages((prev) => prev.map((m) => m.id === assistantId ? { ...m, streaming: false } : m));
              }
              if (evt.type === "error") {
                setMessages((prev) => prev.map((m) =>
                  m.id === assistantId ? { ...m, content: evt.message, streaming: false } : m
                ));
              }
            } catch {}
          }
        }
      } catch (err: any) {
        if (err.name !== "AbortError") {
          setMessages((prev) => prev.map((m) =>
            m.id === assistantId ? { ...m, content: "Connection failed. Please try again.", streaming: false } : m
          ));
        }
      } finally {
        setIsStreaming(false);
        setMessages((prev) => prev.map((m) => m.id === assistantId ? { ...m, streaming: false } : m));
      }
    },
    [userId, messages, isStreaming, docSession]
  );

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  }

  function handleStop() {
    abortRef.current?.abort();
    setIsStreaming(false);
    setMessages((prev) => prev.map((m) => (m.streaming ? { ...m, streaming: false } : m)));
  }

  return (
    <div
      className="flex flex-col h-[100dvh] max-w-4xl mx-auto"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Drag-over overlay */}
      {dragOver && (
        <div className="absolute inset-0 z-50 bg-indigo-600/10 backdrop-blur-sm border-2 border-dashed border-indigo-400 rounded-2xl flex items-center justify-center pointer-events-none">
          <div className="text-center">
            <div className="w-16 h-16 rounded-2xl bg-indigo-100 flex items-center justify-center mx-auto mb-3">
              <svg className="w-8 h-8 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <p className="text-indigo-700 font-bold text-base">Drop your medical document</p>
            <p className="text-indigo-500 text-sm mt-1">PDF, image, or text file</p>
          </div>
        </div>
      )}

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPTED_TYPES}
        className="hidden"
        onChange={handleFileInput}
      />

      {/* ── 1. HEADER BANNER (Clinical Blue Theme) ── */}
      <div className="shrink-0 px-6 pt-6 pb-2">
        <div className="bg-gradient-to-r from-blue-950 via-blue-900 to-indigo-950 text-white rounded-2xl p-5 border border-blue-800/60 shadow-md relative overflow-hidden flex items-center justify-between gap-4">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_80%_0%,rgba(59,130,246,0.25),transparent_60%)] pointer-events-none" />

          <div className="relative z-10 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-500/20 border border-blue-400/30 flex items-center justify-center shrink-0 shadow-2xs backdrop-blur-xs">
              <svg className="w-5 h-5 text-blue-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <div>
              <h1 className="text-base sm:text-lg font-extrabold text-white tracking-tight">Saarthi AI Health Assistant</h1>
              <p className="text-[11px] text-blue-200/80 font-medium">Smart AI Health Guide · Document RAG · Causal Context</p>
            </div>
          </div>

          <div className="relative z-10 flex items-center gap-3">
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading || isStreaming}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold border backdrop-blur-xs transition-all ${
                docSession
                  ? "bg-emerald-500/20 border-emerald-400/30 text-emerald-300 hover:bg-emerald-500/30"
                  : "bg-white/10 border-white/20 text-white hover:bg-white/20"
              } disabled:opacity-40`}
            >
              {uploading ? (
                <>
                  <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Analysing…
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  {docSession ? "Replace Report" : "Upload Report"}
                </>
              )}
            </button>

            <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 backdrop-blur-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Live
            </span>
          </div>
        </div>

        {/* Document pill */}
        {docSession && (
          <div className="mt-3 flex items-center gap-3 bg-blue-50/80 border border-blue-200 rounded-xl px-4 py-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center shrink-0">
              <svg className="w-4 h-4 text-blue-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-bold text-slate-900 truncate">{docSession.filename}</p>
              <p className="text-[10px] text-slate-500 font-semibold">{docSession.chunk_count} sections indexed · RAG active</p>
            </div>
            <button
              onClick={handleRemoveDoc}
              className="w-6 h-6 rounded-lg bg-slate-200/80 hover:bg-slate-300/80 flex items-center justify-center transition-colors shrink-0"
            >
              <svg className="w-3.5 h-3.5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}

        {/* Upload error */}
        {uploadError && (
          <div className="mt-2 flex items-center gap-2 bg-rose-50 border border-rose-200 rounded-xl px-4 py-2">
            <svg className="w-4 h-4 text-rose-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-xs text-rose-700 font-medium">{uploadError}</p>
            <button onClick={() => setUploadError(null)} className="ml-auto text-rose-400 hover:text-rose-600">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}
      </div>

      {/* ── Messages ─────────────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-6 space-y-4 py-3">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        <div ref={bottomRef} />
      </div>

      {/* ── Chips ─────────────────────────────────────────────────────────────── */}
      {!isStreaming && (
        <div className="shrink-0 px-6 pb-2">
          <div className="flex flex-wrap gap-2">
            {chips.map((chip, i) => (
              <button
                key={i}
                onClick={() => sendMessage(chip)}
                className="text-xs font-semibold text-blue-700 bg-blue-50/80 border border-blue-200/80 px-3.5 py-1.5 rounded-full hover:bg-blue-100 transition-all shadow-2xs active:scale-95"
              >
                {chip}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Input ─────────────────────────────────────────────────────────────── */}
      <div className="shrink-0 px-6 pb-6 pt-2">
        <div className="bg-white border border-slate-200 rounded-2xl shadow-xs hover:border-slate-300 focus-within:border-blue-500 focus-within:shadow-md transition-all flex items-end gap-3 p-3">
          {/* Paperclip / attach button */}
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading || isStreaming}
            title="Upload medical document"
            className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 transition-all ${
              docSession
                ? "bg-emerald-50 text-emerald-600 border border-emerald-200 hover:bg-emerald-100"
                : "bg-slate-100 text-slate-500 border border-slate-200 hover:bg-blue-50 hover:text-blue-600 hover:border-blue-200"
            } disabled:opacity-40`}
          >
            {uploading ? (
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
              </svg>
            )}
          </button>

          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={docSession ? `Ask about ${docSession.filename}…` : "Ask about your health data…"}
            rows={1}
            disabled={isStreaming}
            className="flex-1 resize-none bg-transparent text-xs sm:text-sm text-slate-900 placeholder:text-slate-400 outline-none font-medium leading-relaxed max-h-32 disabled:opacity-50"
            style={{ fieldSizing: "content" } as any}
          />

          {isStreaming ? (
            <button
              onClick={handleStop}
              className="w-9 h-9 rounded-xl bg-rose-50 border border-rose-200 text-rose-600 flex items-center justify-center hover:bg-rose-100 transition-colors shrink-0"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <rect x="6" y="6" width="12" height="12" rx="2" />
              </svg>
            </button>
          ) : (
            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim()}
              className="w-9 h-9 rounded-xl bg-blue-600 text-white flex items-center justify-center hover:bg-blue-700 transition-colors disabled:opacity-30 disabled:cursor-not-allowed shrink-0 shadow-xs"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
              </svg>
            </button>
          )}
        </div>

        {/* Medical Disclaimer */}
        <div className="mt-3 flex items-start gap-2.5 bg-amber-50/80 border border-amber-200 rounded-xl px-4 py-2.5">
          <svg className="w-4 h-4 text-amber-600 shrink-0 mt-[1px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
          </svg>
          <p className="text-[11px] text-amber-800 font-medium leading-relaxed">
            <strong className="font-bold text-amber-900">Medical Disclaimer:</strong> SAARTHI.AI provides AI-generated health insights for informational purposes only. Outputs do not constitute medical advice or diagnosis. Always consult a qualified physician for clinical decisions.
          </p>
        </div>
      </div>
    </div>
  );
}

// ── Message Bubble ────────────────────────────────────────────────────────────

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end animate-in fade-in slide-in-from-bottom-2 duration-300">
        <div className="max-w-[75%] bg-indigo-600 text-white rounded-2xl rounded-br-md px-4 py-3 shadow-sm">
          <p className="text-sm font-medium leading-relaxed">{message.content}</p>
        </div>
      </div>
    );
  }

  // While content is empty and still streaming → show dots inside the bubble
  const isThinking = message.streaming && !message.content;

  return (
    <div className="flex items-start gap-3 animate-in fade-in slide-in-from-bottom-2 duration-300">
      <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shrink-0 mt-0.5 shadow-sm shadow-indigo-200">
        <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
      </div>
      <div className="max-w-[80%]">
        <div className="bg-white border border-gray-100 rounded-2xl rounded-tl-md px-4 py-3 shadow-sm min-w-[80px]">
          {isThinking ? (
            <div className="flex items-center gap-2">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce"
                  style={{ animationDelay: `${i * 150}ms` }}
                />
              ))}
            </div>
          ) : (
            <MarkdownText text={message.content} streaming={message.streaming} />
          )}
        </div>
      </div>
    </div>
  );
}

function MarkdownText({ text, streaming }: { text: string; streaming?: boolean }) {
  if (!text) return null;
  const lines = text.split("\n");
  return (
    <div className="text-sm text-gray-700 leading-relaxed space-y-1.5 font-medium">
      {lines.map((line, i) => {
        if (!line.trim()) return <div key={i} className="h-1" />;
        if (line.trim().startsWith("• ") || line.trim().startsWith("- ")) {
          return (
            <div key={i} className="flex items-start gap-2">
              <span className="w-1 h-1 bg-indigo-400 rounded-full shrink-0 mt-2" />
              <span>{renderInline(line.replace(/^[•\-]\s*/, ""))}</span>
            </div>
          );
        }
        if (line.trim().startsWith("_") && line.trim().endsWith("_")) {
          return <p key={i} className="text-xs text-gray-400 italic">{line.trim().slice(1, -1)}</p>;
        }
        return <p key={i}>{renderInline(line)}</p>;
      })}
      {streaming && (
        <span className="inline-block w-1.5 h-4 bg-indigo-500 rounded-sm animate-pulse ml-0.5 align-middle" />
      )}
    </div>
  );
}

function renderInline(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i} className="font-bold text-gray-900">{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}
