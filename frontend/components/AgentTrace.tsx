"use client";

import { useEffect, useRef, useState } from "react";
import type { Recommendation, AgentMeta } from "@/lib/api";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const STEP_CONFIG: Record<number, { color: string; bg: string; border: string; ring: string }> = {
  1: { color: "text-blue-600",   bg: "bg-blue-50",   border: "border-blue-200", ring: "ring-blue-400"   },
  2: { color: "text-violet-600", bg: "bg-violet-50", border: "border-violet-200", ring: "ring-violet-400" },
  3: { color: "text-amber-600",  bg: "bg-amber-50",  border: "border-amber-200", ring: "ring-amber-400"  },
  4: { color: "text-emerald-600",bg: "bg-emerald-50",border: "border-emerald-200",ring:"ring-emerald-400"},
};

interface StepState {
  step: number;
  agent: string;
  icon: string;
  description?: string;
  summary?: string;
  detail?: Record<string, unknown>;
  status: "waiting" | "running" | "complete";
}

interface AgentTraceProps {
  userId: string;
  onComplete: (recs: Recommendation[], agent: AgentMeta, riskScore?: number) => void;
}

export default function AgentTrace({ userId, onComplete }: AgentTraceProps) {
  const [steps, setSteps] = useState<StepState[]>([]);
  const [phase, setPhase] = useState<"idle" | "running" | "done" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!userId) return;

    setPhase("running");
    setSteps([]);

    const url = `${BASE}/recommend/stream?user_id=${encodeURIComponent(userId)}`;
    const es = new EventSource(url);
    esRef.current = es;

    es.onmessage = (e) => {
      const data = JSON.parse(e.data);

      if (data.type === "step_start") {
        setSteps((prev) => [
          ...prev,
          {
            step: data.step,
            agent: data.agent,
            icon: data.icon,
            description: data.description,
            status: "running",
          },
        ]);
      }

      if (data.type === "step_complete") {
        setSteps((prev) =>
          prev.map((s) =>
            s.step === data.step
              ? { ...s, summary: data.summary, status: "complete", detail: data }
              : s
          )
        );
      }

      if (data.type === "complete") {
        setPhase("done");
        es.close();
        onComplete(data.recommendations ?? [], data.agent ?? {}, data.risk_score);
      }

      if (data.type === "error") {
        setPhase("error");
        setErrorMsg(data.message ?? "Agent failed");
        es.close();
      }
    };

    es.onerror = () => {
      if (phase !== "done") {
        setPhase("error");
        setErrorMsg("Connection to agent lost. Ensure the backend is running.");
        es.close();
      }
    };

    return () => {
      es.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  if (phase === "error") {
    return (
      <div className="bg-red-50 border border-red-200 rounded-2xl p-5 text-center">
        <p className="text-sm font-bold text-red-600 mb-1">Agent Error</p>
        <p className="text-xs text-red-400">{errorMsg}</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-[2rem] border border-gray-100 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
        <div>
          <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">
            Cognitive Health Agent
          </p>
          <h3 className="text-sm font-bold text-gray-900">4-Step Agentic Pipeline</h3>
        </div>
        <div className="flex items-center gap-2">
          {phase === "running" && (
            <>
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
              </span>
              <span className="text-[10px] font-bold text-emerald-600 uppercase tracking-widest">
                Live
              </span>
            </>
          )}
          {phase === "done" && (
            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest bg-gray-50 px-2 py-1 rounded-lg">
              Complete
            </span>
          )}
        </div>
      </div>

      {/* Steps */}
      <div className="divide-y divide-gray-50">
        {phase === "running" && steps.length === 0 && (
          <div className="px-6 py-5 flex items-center gap-3">
            <div className="w-4 h-4 border-2 border-gray-300 border-t-emerald-500 rounded-full animate-spin" />
            <p className="text-xs text-gray-400">Initialising agent…</p>
          </div>
        )}

        {steps.map((step) => {
          const cfg = STEP_CONFIG[step.step] ?? STEP_CONFIG[1];
          return (
            <div
              key={step.step}
              className="px-6 py-4 flex items-start gap-4 animate-in fade-in slide-in-from-left-4 duration-500"
            >
              {/* Icon / status */}
              <div className={`relative flex-shrink-0 w-10 h-10 rounded-xl ${cfg.bg} ${cfg.border} border flex items-center justify-center`}>
                {step.status === "running" ? (
                  <div className={`w-4 h-4 border-2 border-gray-200 border-t-current ${cfg.color} rounded-full animate-spin`} />
                ) : (
                  <span className="text-lg leading-none">{step.icon}</span>
                )}
                {step.status === "complete" && (
                  <span className={`absolute -top-1 -right-1 w-4 h-4 rounded-full bg-white ${cfg.border} border flex items-center justify-center`}>
                    <svg className={`w-2.5 h-2.5 ${cfg.color}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </span>
                )}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0 pt-0.5">
                <div className="flex items-center gap-2 mb-1">
                  <p className={`text-xs font-bold ${cfg.color} uppercase tracking-wider`}>
                    Step {step.step}
                  </p>
                  <span className="text-xs text-gray-400 font-medium">{step.agent}</span>
                </div>

                {step.status === "running" && (
                  <p className="text-xs text-gray-400 italic">{step.description}</p>
                )}

                {step.status === "complete" && step.summary && (
                  <p className="text-xs text-gray-600 leading-relaxed font-medium">{step.summary}</p>
                )}

                {/* Extra detail for specific steps */}
                {step.status === "complete" && step.step === 3 && step.detail && (
                  <div className="mt-1.5 flex items-center gap-1.5 flex-wrap">
                    {(step.detail as any).lever && (
                      <span className="text-[10px] font-bold text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full">
                        Lever: {(step.detail as any).lever}
                      </span>
                    )}
                    {(step.detail as any).mechanism && (
                      <span className="text-[10px] text-gray-400 font-medium truncate max-w-xs">
                        {(step.detail as any).mechanism}
                      </span>
                    )}
                  </div>
                )}

                {step.status === "complete" && step.step === 2 && step.detail && (
                  <p className="text-[10px] text-violet-500 font-medium mt-1 italic">
                    {(step.detail as any).insight}
                  </p>
                )}
              </div>

              {/* Step number */}
              <span className="text-[10px] font-black text-gray-200 tabular-nums pt-1">
                {String(step.step).padStart(2, "0")}
              </span>
            </div>
          );
        })}
      </div>

      {/* Footer */}
      {phase === "done" && (
        <div className="px-6 py-3 bg-emerald-50 border-t border-emerald-100 flex items-center gap-2">
          <svg className="w-3.5 h-3.5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
          <span className="text-[10px] font-bold text-emerald-600 uppercase tracking-widest">
            Agent analysis complete — Groq · {steps.length} steps · 3 LLM calls
          </span>
        </div>
      )}
    </div>
  );
}
