"use client";

import React, { useState, useRef, useEffect } from "react";
import { Play, Trophy, Swords, Shield, HeartPulse, AlignLeft, Activity, Target, CheckCircle2 } from "lucide-react";
function MarkdownText({ content, className }: { content: string, className?: string }) {
  if (!content) return null;
  const lines = content.split("\n");
  const renderInline = (str: string) => {
    const parts = str.split(/(\*\*.*?\*\*|\*.*?\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith("**")) return <strong key={i} className="font-bold text-gray-900">{part.slice(2, -2)}</strong>;
      if (part.startsWith("*")) return <em key={i} className="text-gray-800">{part.slice(1, -1)}</em>;
      return <span key={i}>{part}</span>;
    });
  };
  return (
    <div className={`leading-relaxed space-y-2 ${className || 'text-sm text-gray-700'}`}>
      {lines.map((line, i) => {
        if (!line.trim()) return <div key={i} className="h-1" />;
        if (line.match(/^#+\s/)) return <h4 key={i} className="font-bold text-gray-900 mt-2 mb-1 text-[1.1em]">{line.replace(/^#+\s/, "")}</h4>;
        if (line.trim().startsWith("- ") || line.trim().startsWith("* ")) {
          return (
            <div key={i} className="flex items-start gap-2 ml-2">
              <span className="w-1 h-1 bg-gray-400 rounded-full shrink-0 mt-2" />
              <span>{renderInline(line.replace(/^[\-\*]\s*/, ""))}</span>
            </div>
          );
        }
        return <p key={i}>{renderInline(line)}</p>;
      })}
    </div>
  );
}

const DEFAULT_USER = "user_demo_001";

interface ModelEval {
  model: string;
  scores: {
    clinical_accuracy: number;
    structural_clarity: number;
    actionability: number;
    preciseness: number;
  };
  overall: number;
  critique: string;
  thought_process?: string;
}

const ARENA_MODELS = [
  { id: "gptoss", name: "GPT OSS 120B Flagship", tag: "openai/gpt-oss-120b", color: "from-blue-500 to-cyan-500", border: "border-cyan-200" },
  { id: "llama", name: "Llama 3.3 Flagship", tag: "llama-3.3-70b-versatile", color: "from-indigo-500 to-violet-500", border: "border-indigo-200" },
  { id: "qwen", name: "Qwen 32B Benchmark", tag: "qwen/qwen3-32b", color: "from-orange-500 to-amber-500", border: "border-orange-200" },
];

export default function ArenaPage() {
  const [query, setQuery] = useState("Based on my latest vitals, what is the safest way to lower my blood pressure without medication?");
  const [isBattling, setIsBattling] = useState(false);
  const [phase, setPhase] = useState<"idle" | "generating" | "evaluating" | "complete">("idle");
  
  // Model state
  const [responses, setResponses] = useState<Record<string, string>>({ gptoss: "", llama: "", qwen: "" });
  const [evaluations, setEvaluations] = useState<Record<string, ModelEval | null>>({ gptoss: null, llama: null, qwen: null });
  const [winner, setWinner] = useState<string | null>(null);
  const [verdict, setVerdict] = useState<string | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);

  const startBattle = () => {
    if (!query.trim()) return;
    
    // Reset state
    setResponses({ gptoss: "", llama: "", qwen: "" });
    setEvaluations({ gptoss: null, llama: null, qwen: null });
    setWinner(null);
    setVerdict(null);
    setIsBattling(true);
    setPhase("generating");

    const userId = typeof sessionStorage !== "undefined" ? sessionStorage.getItem("saarthi_user_id") || sessionStorage.getItem("darpan_user_id") || DEFAULT_USER : DEFAULT_USER;
    const url = `http://localhost:8000/arena/stream?query=${encodeURIComponent(query)}&user_id=${userId}`;
    
    const sse = new EventSource(url);
    eventSourceRef.current = sse;

    sse.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        
        switch (data.type) {
          case "chunk":
            setResponses((prev) => ({
              ...prev,
              [data.model]: (prev[data.model] || "") + data.text
            }));
            break;
            
          case "generation_complete":
            // In the backend we yield this twice now (before and after evaluation).
            // We just ensure we are in evaluation phase if not already complete.
            if (setPhase) setPhase("evaluating");
            break;
            
          case "evaluation_complete":
            const results = data.evaluations;
            const evalDict: Record<string, ModelEval> = {};
            results.forEach((r: any) => { evalDict[r.model] = r; });
            setEvaluations(evalDict);
            setWinner(data.winner);
            setVerdict(data.verdict);
            setPhase("complete");
            setIsBattling(false);
            sse.close();
            break;
            
          case "error":
             console.error("Arena error:", data.error);
             break;
        }
      } catch (err) {
        console.error("Failed to parse SSE", err);
      }
    };

    sse.onerror = () => {
      sse.close();
      setIsBattling(false);
      setPhase("idle");
    };
  };

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) eventSourceRef.current.close();
    };
  }, []);


  const renderProgress = (val: number, color: string) => (
    <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
      <div className={`h-full bg-gradient-to-r ${color} transition-all duration-1000`} style={{ width: `${val}%` }} />
    </div>
  );

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-8 bg-slate-50/60 min-h-screen pb-24">

      {/* ── 1. HEADER BANNER (Clinical Blue Theme) ── */}
      <div className="bg-gradient-to-r from-blue-950 via-blue-900 to-indigo-950 text-white rounded-2xl p-6 sm:p-7 border border-blue-800/60 shadow-md relative overflow-hidden space-y-5">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_80%_0%,rgba(59,130,246,0.25),transparent_60%)] pointer-events-none" />

        <div className="relative z-10 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 backdrop-blur-xs">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Automated LLM Benchmark
              </span>
              <span className="text-xs text-blue-200/70 font-medium">· Nano Judge Evaluation Engine</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight flex items-center gap-2.5">
              <Swords className="w-7 h-7 text-blue-300" /> AI Model Arena
            </h1>
          </div>

          {phase !== "idle" && (
            <div className="px-3.5 py-2 bg-white/10 border border-white/20 text-white rounded-xl backdrop-blur-xs flex items-center gap-2.5 shadow-sm">
              {phase === "generating" && <div className="w-3.5 h-3.5 rounded-full border-2 border-t-white border-r-white border-b-white/20 border-l-white/20 animate-spin" />}
              {phase === "evaluating" && <Activity className="w-3.5 h-3.5 text-emerald-300 animate-pulse" />}
              {phase === "complete" && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-300" />}
              <span className="text-xs font-bold uppercase tracking-wider">
                {phase === "generating" ? "Models Generating..." :
                 phase === "evaluating" ? "Evaluating Output..." :
                 "Benchmarking Complete"}
              </span>
            </div>
          )}
        </div>

        {/* Clinical Scenario Input Form */}
        <div className="relative z-10 flex flex-col sm:flex-row gap-3 pt-1">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={isBattling}
            className="flex-1 bg-white/10 hover:bg-white/15 focus:bg-white/20 border border-white/20 rounded-xl px-4 py-3 text-xs sm:text-sm font-medium text-white placeholder-blue-200/60 focus:outline-none focus:ring-2 focus:ring-blue-400/40 transition-all disabled:opacity-50"
            placeholder="Enter a clinical scenario or medical question..."
          />
          <button
            onClick={startBattle}
            disabled={isBattling || !query.trim()}
            className="shrink-0 flex items-center justify-center gap-2 bg-emerald-500 hover:bg-emerald-600 text-white px-6 py-3 rounded-xl font-bold text-xs sm:text-sm shadow-sm transition-all disabled:opacity-50"
          >
            <Play className="w-4 h-4" fill="currentColor" /> Run Benchmark Battle
          </button>
        </div>
      </div>

      {/* ── 2. ARENA MODEL COLUMNS ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {ARENA_MODELS.map((model) => {
          const isWinner = winner === model.id;
          const evalData = evaluations[model.id];

          return (
            <div
              key={model.id}
              className={`flex flex-col bg-white rounded-2xl border transition-all duration-500 overflow-hidden ${
                isWinner ? "border-amber-400 shadow-md ring-2 ring-amber-400/20" : "border-slate-200 shadow-xs"
              }`}
            >
              {/* Model Header */}
              <div className="p-5 border-b border-slate-100 flex items-center justify-between relative bg-slate-50/50">
                <div className={`absolute top-0 left-0 w-full h-1 bg-gradient-to-r ${model.color}`} />
                <div>
                  <h3 className="text-base font-bold text-slate-900 flex items-center gap-1.5">
                    {model.name}
                    {isWinner && <Trophy className="w-4 h-4 text-amber-500 shrink-0" fill="currentColor" />}
                  </h3>
                  <p className="text-[10px] font-mono text-slate-400 mt-0.5">{model.tag}</p>
                </div>
                {evalData && (
                  <div className="text-right">
                    <span className="text-2xl font-black text-slate-900 tracking-tight">
                      {evalData.overall.toFixed(1)}<span className="text-xs text-slate-400 font-bold ml-0.5">/10</span>
                    </span>
                  </div>
                )}
              </div>

              {/* Streaming Output Text */}
              <div className="flex-1 p-5 min-h-[260px] max-h-[360px] overflow-y-auto text-xs text-slate-700 leading-relaxed font-medium bg-white">
                {responses[model.id] ? (
                  <MarkdownText content={responses[model.id].replace(/<think>[\s\S]*?(?:<\/think>|$)/g, '').trim()} />
                ) : (
                  <div className="h-full flex items-center justify-center text-slate-400 font-medium text-xs py-12">
                    {phase === "idle" ? "Awaiting benchmark trigger..." : "Connecting to API model..."}
                  </div>
                )}
              </div>

              {/* Nano Judge Scorecard Panel */}
              {evalData && (
                <div className="border-t border-slate-100 p-5 bg-slate-50/70 space-y-3.5">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Nano Judge Evaluation</span>

                  <div className="space-y-3">
                    <div>
                      <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                        <span className="flex items-center gap-1"><Shield className="w-3.5 h-3.5 text-blue-600"/> Clinical Accuracy</span>
                        <span>{evalData.scores.clinical_accuracy}%</span>
                      </div>
                      {renderProgress(evalData.scores.clinical_accuracy, "from-blue-500 to-blue-600")}
                    </div>

                    <div>
                      <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                        <span className="flex items-center gap-1"><AlignLeft className="w-3.5 h-3.5 text-indigo-600"/> Structural Clarity</span>
                        <span>{evalData.scores.structural_clarity}%</span>
                      </div>
                      {renderProgress(evalData.scores.structural_clarity, "from-indigo-500 to-indigo-600")}
                    </div>

                    <div>
                      <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                        <span className="flex items-center gap-1"><Activity className="w-3.5 h-3.5 text-emerald-600"/> Actionability</span>
                        <span>{evalData.scores.actionability}%</span>
                      </div>
                      {renderProgress(evalData.scores.actionability, "from-emerald-500 to-emerald-600")}
                    </div>

                    <div>
                      <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                        <span className="flex items-center gap-1"><Target className="w-3.5 h-3.5 text-rose-600"/> Preciseness</span>
                        <span>{evalData.scores.preciseness}%</span>
                      </div>
                      {renderProgress(evalData.scores.preciseness, "from-rose-500 to-rose-600")}
                    </div>
                  </div>

                  <p className="text-xs text-slate-600 font-medium italic pt-2 border-t border-slate-200/60 leading-relaxed">
                    "{evalData.critique}"
                  </p>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* ── 3. FINAL VERDICT CALLOUT ── */}
      {phase === "complete" && verdict && (
        <div className="bg-amber-50/80 border border-amber-200 rounded-2xl p-6 shadow-xs animate-in fade-in duration-500">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-amber-500 text-white flex items-center justify-center shrink-0 shadow-2xs">
              <Trophy className="w-6 h-6" fill="currentColor" />
            </div>
            <div className="space-y-2">
              <span className="text-[11px] font-bold text-amber-800 uppercase tracking-wider block">Official Judge Verdict</span>
              <p className="text-xs sm:text-sm font-semibold text-slate-800 leading-relaxed italic bg-white p-3.5 rounded-xl border border-amber-200/80">
                "{verdict}"
              </p>
              <div className="flex items-center gap-2 pt-1">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-xs font-bold text-emerald-800 uppercase">
                  Winner: {ARENA_MODELS.find((m) => m.id === winner)?.name || winner}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
