"use client";

import { useEffect, useRef, useState, useCallback } from "react";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
  docNotice?: { filename: string; chunkCount: number; preview: string };
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

const ACCEPTED_TYPES = ".pdf,.txt,.md,.png,.jpg,.jpeg,.webp,.csv";

// Saarthi's mark — reused at two sizes: large for the empty state, small on
// every assistant message so a reply is never mistaken for page body text.
function SaarthiMark({ size = 32 }: { size?: number }) {
  return (
    <div
      className="rounded-2xl bg-blue-600 flex items-center justify-center shrink-0"
      style={{ width: size, height: size }}
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        className="text-white"
        style={{ width: size * 0.44, height: size * 0.44 }}
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    </div>
  );
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [chips, setChips] = useState<string[]>(INITIAL_CHIPS);
  const [isStreaming, setIsStreaming] = useState(false);
  const [userId, setUserId] = useState("");
  const [userName, setUserName] = useState("");
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
    const name = sessionStorage.getItem("saarthi_user_name") ?? sessionStorage.getItem("darpan_user_name");
    if (name) setUserName(name);
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

      const res = await fetch(`${BASE}/chat/upload`, { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Upload failed");

      setDocSession(data);
      setChips(DOC_CHIPS);

      // Rendered as a distinct DocumentNotice, not a chat bubble — the
      // filename/section-count is already shown in the pill above the
      // conversation, so this only carries what that pill doesn't: a short
      // preview snippet as evidence the extraction actually worked.
      const sysMsg: Message = {
        id: `doc-${Date.now()}`,
        role: "assistant",
        content: "",
        docNotice: { filename: data.filename, chunkCount: data.chunk_count, preview: data.preview },
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

  function handleDragOver(e: React.DragEvent) { e.preventDefault(); setDragOver(true); }
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

      const userMsg: Message = { id: Date.now().toString(), role: "user", content: text.trim() };
      const assistantId = (Date.now() + 1).toString();
      const assistantMsg: Message = { id: assistantId, role: "assistant", content: "", streaming: true };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setInput("");
      setIsStreaming(true);

      const history = messages
        .filter((m) => !m.id.startsWith("doc-") && !m.id.startsWith("undoc-"))
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

  function handleNewChat() {
    if (isStreaming) return;
    setMessages([]);
    setChips(docSession ? DOC_CHIPS : INITIAL_CHIPS);
  }

  const hasStarted = messages.length > 0;

  return (
    <div
      className="relative flex flex-col h-[100dvh] bg-slate-50/60"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {dragOver && (
        <div className="absolute inset-0 z-50 bg-slate-900/5 backdrop-blur-sm border-2 border-dashed border-blue-300 rounded-2xl flex items-center justify-center pointer-events-none">
          <div className="text-center">
            <div className="w-14 h-14 rounded-2xl bg-white shadow-sm flex items-center justify-center mx-auto mb-3">
              <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <p className="text-slate-800 font-semibold text-sm">Drop your medical document</p>
            <p className="text-slate-400 text-xs mt-0.5">PDF, image, or text file</p>
          </div>
        </div>
      )}

      <input ref={fileInputRef} type="file" accept={ACCEPTED_TYPES} className="hidden" onChange={handleFileInput} />

      {/* ── Top bar — only present once a conversation exists or a doc is loaded ── */}
      {(hasStarted || docSession || uploadError) && (
        <div className="shrink-0 px-5 sm:px-6 pt-4 pb-3 border-b border-slate-200 bg-white">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <SaarthiMark size={30} />
              <div>
                <h1 className="text-sm font-bold text-slate-900 leading-tight">Saarthi</h1>
                <p className="text-[11px] text-slate-400 leading-tight">AI Health Assistant</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {hasStarted && (
                <button
                  onClick={handleNewChat}
                  disabled={isStreaming}
                  className="text-xs font-semibold text-slate-500 hover:text-slate-900 px-3 py-1.5 rounded-lg hover:bg-slate-100 transition-colors disabled:opacity-40"
                >
                  New chat
                </button>
              )}
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading || isStreaming}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${
                  docSession
                    ? "bg-emerald-50 border-emerald-200 text-emerald-700 hover:bg-emerald-100"
                    : "bg-white border-slate-200 text-slate-600 hover:bg-slate-50"
                } disabled:opacity-40`}
              >
                {uploading ? (
                  <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                ) : (
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                )}
                {docSession ? "Replace report" : "Upload report"}
              </button>
            </div>
          </div>

          {docSession && (
            <div className="mt-3 flex items-center gap-2.5 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2">
              <svg className="w-4 h-4 text-slate-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-slate-800 truncate">{docSession.filename}</p>
                <p className="text-[10px] text-slate-400">{docSession.chunk_count} sections indexed</p>
              </div>
              <button onClick={handleRemoveDoc} className="w-6 h-6 rounded-lg hover:bg-slate-200/70 flex items-center justify-center transition-colors shrink-0">
                <svg className="w-3.5 h-3.5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          )}

          {uploadError && (
            <div className="mt-2 flex items-center gap-2 bg-rose-50 border border-rose-100 rounded-xl px-3 py-2">
              <p className="text-xs text-rose-700 font-medium flex-1">{uploadError}</p>
              <button onClick={() => setUploadError(null)} className="text-rose-400 hover:text-rose-600 shrink-0">
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── Body: empty-state hero, or the conversation ── */}
      {!hasStarted ? (
        <div className="flex-1 flex flex-col items-center justify-center px-6 -mt-10">
          <SaarthiMark size={56} />
          <h2 className="mt-5 text-xl sm:text-2xl font-bold text-slate-900 text-center">
            {userName ? `Hey ${userName}, how can I help?` : "How can I help today?"}
          </h2>
          <p className="mt-2.5 text-sm text-slate-500 text-center max-w-md leading-relaxed">
            Ask about your risk score, causal analysis, or simulations — I answer directly from your
            live health data. You can also upload a report and I'll read it.
          </p>

          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="mt-6 flex items-center gap-2 px-4 py-2 rounded-full bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 transition-all shadow-sm disabled:opacity-50"
          >
            {uploading ? (
              <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : (
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            )}
            Upload Health Report
          </button>

          <div className="mt-8 flex flex-wrap justify-center gap-2 max-w-lg">
            {INITIAL_CHIPS.map((chip, i) => (
              <button
                key={i}
                onClick={() => sendMessage(chip)}
                className="text-xs font-semibold text-slate-600 bg-white border border-slate-200 px-3.5 py-2 rounded-full hover:border-slate-300 hover:bg-slate-50 transition-colors shadow-2xs"
              >
                {chip}
              </button>
            ))}
          </div>
        </div>
      ) : (
        // Outer: scroll container. Inner: min-h-full + justify-end anchors
        // messages to the BOTTOM of the available space — so a short
        // conversation sits right against the input bar instead of stranded
        // at the top with a dead gap below it, and only starts scrolling
        // once it genuinely overflows. Same anchoring ChatGPT/Claude use.
        <div className="flex-1 overflow-y-auto px-5 sm:px-6">
          {/* Same max-w-3xl mx-auto as the input bar below — without this,
              messages span the full page width while the input stays
              narrow and centered, so bubbles visibly overshoot its edges. */}
          <div className="max-w-3xl mx-auto min-h-full flex flex-col justify-end py-5 space-y-5">
            {messages.map((msg) =>
              msg.docNotice ? (
                <DocumentNotice key={msg.id} notice={msg.docNotice} />
              ) : (
                <MessageBubble key={msg.id} message={msg} />
              )
            )}
            <div ref={bottomRef} />
          </div>
        </div>
      )}

      {/* ── Follow-up chips (mid-conversation) ── */}
      {hasStarted && !isStreaming && (
        <div className="shrink-0 px-5 sm:px-6 pb-3">
          <div className="max-w-3xl mx-auto flex flex-wrap gap-1.5">
            {chips.map((chip, i) => (
              <button
                key={i}
                onClick={() => sendMessage(chip)}
                className="text-xs font-semibold text-slate-600 bg-white border border-slate-200 px-3 py-1.5 rounded-full hover:border-slate-300 hover:bg-slate-50 transition-colors shadow-2xs"
              >
                {chip}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Input bar ── */}
      <div className="shrink-0 px-5 sm:px-6 pb-5 pt-1">
        <div className="max-w-3xl mx-auto">
          <div className="bg-white border border-slate-200 rounded-3xl shadow-sm focus-within:border-blue-400 focus-within:shadow-md transition-all">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={docSession ? `Ask about ${docSession.filename}…` : "Ask about your health data…"}
              rows={1}
              disabled={isStreaming}
              className="w-full resize-none bg-transparent text-sm text-slate-900 placeholder:text-slate-400 outline-none leading-relaxed max-h-32 px-4 pt-3.5 pb-1 disabled:opacity-50"
              style={{ fieldSizing: "content" } as any}
            />
            <div className="flex items-center justify-between px-2.5 pb-2.5 pt-1">
              <div className="flex items-center gap-1">
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading || isStreaming}
                  title="Upload medical document"
                  className="w-8 h-8 rounded-xl flex items-center justify-center text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors disabled:opacity-40"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                </button>
                {hasStarted && (
                  <button
                    onClick={handleNewChat}
                    disabled={isStreaming}
                    title="Start a new conversation"
                    className="w-8 h-8 rounded-xl flex items-center justify-center text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors disabled:opacity-40"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  </button>
                )}
              </div>

              <div className="flex items-center gap-2">
                {/* Real, non-decorative status — not a fake model picker.
                    This app has exactly one assistant configuration; a
                    clickable "Automatic ⌄" selector with nothing behind it
                    would misrepresent what's actually happening. This shows
                    what's actually true: whether a document is currently
                    grounding the answers. */}
                <span className="hidden sm:flex items-center gap-1.5 text-[11px] font-semibold text-slate-400 px-2">
                  {docSession ? (
                    <>
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                      Using your report
                    </>
                  ) : (
                    <>
                      <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                      Using your health data
                    </>
                  )}
                </span>

                {isStreaming ? (
                  <button
                    onClick={handleStop}
                    className="w-8 h-8 rounded-full bg-slate-100 text-slate-500 flex items-center justify-center hover:bg-slate-200 transition-colors shrink-0"
                  >
                    <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                      <rect x="6" y="6" width="12" height="12" rx="2" />
                    </svg>
                  </button>
                ) : (
                  <button
                    onClick={() => sendMessage(input)}
                    disabled={!input.trim()}
                    className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center hover:bg-blue-700 transition-colors disabled:opacity-25 disabled:cursor-not-allowed shrink-0"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10l7.5-7.5m0 0l7.5 7.5m-7.5-7.5v18" />
                    </svg>
                  </button>
                )}
              </div>
            </div>
          </div>

          <p className="mt-2.5 text-center text-[10px] text-slate-400 leading-relaxed">
            AI-generated, informational only — not medical advice. Consult a physician for clinical decisions.
          </p>
        </div>
      </div>
    </div>
  );
}

// ── Document Notice ──────────────────────────────────────────────────────────
// A distinct system notice, not an AI chat bubble — the filename and section
// count are already shown in the pill above the conversation, so this only
// adds what that pill doesn't: brief proof the extraction produced real,
// readable text. Compact and secondary by design, since even a well-cleaned
// preview is still raw document text, not something worth foregrounding.

function DocumentNotice({ notice }: { notice: NonNullable<Message["docNotice"]> }) {
  return (
    <div className="flex justify-center">
      <div className="w-full max-w-md bg-emerald-50/60 border border-emerald-100 rounded-xl px-4 py-3">
        <div className="flex items-center gap-2 text-emerald-700">
          <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <p className="text-xs font-semibold">
            Read {notice.chunkCount} sections — ready for questions about it
          </p>
        </div>
        {notice.preview && (
          <p className="mt-1.5 text-[11px] text-slate-500 leading-relaxed line-clamp-2">
            {notice.preview}
          </p>
        )}
      </div>
    </div>
  );
}

// ── Message Bubble ────────────────────────────────────────────────────────────

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] bg-blue-600 text-white rounded-2xl rounded-br-md px-4 py-2.5">
          <p className="text-sm leading-relaxed">{message.content}</p>
        </div>
      </div>
    );
  }

  const isThinking = message.streaming && !message.content;

  // Assistant replies get their own avatar + bounded card — the fix for
  // "we don't understand this is the AI's response." Plain unbounded text
  // reads as page body copy, especially for long structured answers with
  // their own headers.
  return (
    <div className="flex items-start gap-2.5">
      <div className="mt-0.5">
        <SaarthiMark size={26} />
      </div>
      <div className="max-w-[85%] bg-white border border-slate-200 rounded-2xl rounded-tl-md px-4 py-3 shadow-2xs min-w-[64px]">
        {isThinking ? (
          <div className="flex items-center gap-1.5 py-1">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="w-1.5 h-1.5 bg-slate-300 rounded-full animate-bounce"
                style={{ animationDelay: `${i * 150}ms` }}
              />
            ))}
          </div>
        ) : (
          <MarkdownText text={message.content} streaming={message.streaming} />
        )}
      </div>
    </div>
  );
}

function MarkdownText({ text, streaming }: { text: string; streaming?: boolean }) {
  if (!text) return null;
  const lines = text.split("\n");
  return (
    <div className="text-sm text-slate-700 leading-relaxed space-y-1.5">
      {lines.map((line, i) => {
        if (!line.trim()) return <div key={i} className="h-1" />;
        if (line.trim().startsWith("• ") || line.trim().startsWith("- ")) {
          return (
            <div key={i} className="flex items-start gap-2">
              <span className="w-1 h-1 bg-slate-300 rounded-full shrink-0 mt-2" />
              <span>{renderInline(line.replace(/^[•\-]\s*/, ""))}</span>
            </div>
          );
        }
        if (line.trim().startsWith("_") && line.trim().endsWith("_")) {
          return <p key={i} className="text-xs text-slate-400 italic">{line.trim().slice(1, -1)}</p>;
        }
        return <p key={i}>{renderInline(line)}</p>;
      })}
      {streaming && (
        <span className="inline-block w-1.5 h-4 bg-blue-400 rounded-sm animate-pulse ml-0.5 align-middle" />
      )}
    </div>
  );
}

function renderInline(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i} className="font-bold text-slate-900">{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}
