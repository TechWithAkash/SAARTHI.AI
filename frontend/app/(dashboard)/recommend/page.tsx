"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Recommendation, RecommendResponse } from "@/lib/api";
import { useRouter } from "next/navigation";
import { Brain, Zap, Target, FlaskConical, ArrowRight, RefreshCw, CheckCircle2, Clock, TrendingDown, Layers } from "lucide-react";

const DEFAULT_USER = "user_demo_001";

const STEPS = [
  { icon: FlaskConical, label: "Risk Analyst", color: "indigo", num: "01" },
  { icon: Brain,        label: "Memory Agent", color: "violet", num: "02" },
  { icon: Zap,          label: "Causal Strategist", color: "amber", num: "03" },
  { icon: Target,       label: "Recommendation Engine", color: "emerald", num: "04" },
] as const;

const IMPACT_CONFIG = {
  high:   { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200", dot: "bg-emerald-500", label: "High Impact" },
  medium: { bg: "bg-amber-50",   text: "text-amber-700",   border: "border-amber-200",   dot: "bg-amber-400",  label: "Medium Impact" },
  low:    { bg: "bg-gray-50",    text: "text-gray-600",    border: "border-gray-200",    dot: "bg-gray-400",   label: "Low Impact" },
};

export default function RecommendPage() {
  const [data, setData] = useState<RecommendResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pipelineStep, setPipelineStep] = useState(0);
  const router = useRouter();

  const userId = typeof window !== "undefined"
    ? (sessionStorage.getItem("saarthi_user_id") ?? sessionStorage.getItem("darpan_user_id") ?? DEFAULT_USER)
    : DEFAULT_USER;

  async function load() {
    setLoading(true);
    setError(null);
    setPipelineStep(0);

    // Animate pipeline steps while fetching
    const timer = setInterval(() => {
      setPipelineStep((s) => (s < 3 ? s + 1 : s));
    }, 600);

    try {
      const res = await api.getRecommend(userId);
      setData(res);
      setPipelineStep(4); // all complete
    } catch (e: any) {
      setError(e.detail ?? (e.status === 404 ? "No recommendations found yet. Please submit your health metrics first." : e.message ?? "Failed to load recommendations"));
    } finally {
      clearInterval(timer);
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  return (
    <div className="min-h-screen bg-white">
      {/* ── Hero Header ─────────────────────────────────────────────────── */}
      <div className="relative overflow-hidden bg-gradient-to-br from-gray-950 via-indigo-950 to-violet-950 px-8 py-14">
        {/* Orb decorations */}
        <div className="absolute -top-24 -right-24 w-96 h-96 rounded-full bg-indigo-500/10 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-16 -left-16 w-64 h-64 rounded-full bg-violet-500/10 blur-3xl pointer-events-none" />

        <div className="relative max-w-5xl mx-auto">
          <div className="flex items-start justify-between gap-6">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" />
                </span>
                <span className="text-[10px] font-extrabold text-emerald-400 uppercase tracking-widest">
                  Agentic Intelligence · Groq LLaMA-3 · Live
                </span>
              </div>
              <h1 className="text-4xl font-extrabold text-white tracking-tight leading-tight mb-3">
                Cognitive Health Agent
              </h1>
              <p className="text-gray-400 font-medium text-base max-w-xl leading-relaxed">
                A 4-step Groq-powered agent analyses your health data in real-time and synthesises
                personalised, causal-aware interventions ranked by biological impact.
              </p>
            </div>
            <button
              onClick={load}
              disabled={loading}
              className="shrink-0 flex items-center gap-2 px-5 py-3 rounded-2xl bg-white/10 border border-white/20 text-white text-sm font-bold hover:bg-white/20 transition-all disabled:opacity-40"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
              Re-run Agent
            </button>
          </div>

          {/* Pipeline steps */}
          <div className="mt-10 grid grid-cols-2 md:grid-cols-4 gap-3">
            {STEPS.map((step, i) => {
              const done = pipelineStep > i;
              const active = pipelineStep === i && loading;
              const Icon = step.icon;
              return (
                <div key={i} className={`relative flex items-center gap-3 p-4 rounded-2xl border transition-all duration-500 ${
                  done    ? "bg-white/10 border-white/20"
                  : active ? "bg-white/5 border-white/10 animate-pulse"
                  :          "bg-white/5 border-white/5 opacity-40"
                }`}>
                  <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 text-sm ${
                    done ? "bg-emerald-500 text-white" : "bg-white/10 text-white/50"
                  }`}>
                    {done ? <CheckCircle2 className="w-4 h-4" /> : <Icon className="w-4 h-4" />}
                  </div>
                  <div>
                    <p className="text-[9px] font-black text-white/40 uppercase tracking-widest">{step.num}</p>
                    <p className="text-xs font-bold text-white/80 leading-tight">{step.label}</p>
                  </div>
                </div>
              );
            })}
          </div>

          {pipelineStep === 4 && !loading && (
            <p className="mt-4 text-[11px] font-bold text-emerald-400 uppercase tracking-widest">
              ✓ Agent analysis complete — Groq · 4 steps · 3 LLM calls
            </p>
          )}
        </div>
      </div>

      {/* ── Body ──────────────────────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-8 py-12">

        {/* Loading skeletons */}
        {loading && (
          <div className="space-y-4 animate-pulse">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-32 bg-gray-100 rounded-2xl" />
            ))}
          </div>
        )}

        {/* Error */}
        {error && !loading && (
          <div className="flex items-center gap-4 bg-red-50 border border-red-100 rounded-2xl px-6 py-5">
            <div className="w-10 h-10 rounded-xl bg-red-100 flex items-center justify-center shrink-0">
              <span className="text-red-500 text-sm font-black">!</span>
            </div>
            <div>
              <p className="font-bold text-red-700 text-sm">{error}</p>
              <p className="text-xs text-red-500 mt-0.5">Submit vitals on Patient Vitals first to enable the agent.</p>
            </div>
            <button
              onClick={() => router.push("/dashboard")}
              className="ml-auto flex items-center gap-2 px-4 py-2 rounded-xl bg-red-600 text-white text-xs font-bold hover:bg-red-700 transition-colors"
            >
              Go to Vitals <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        )}

        {/* Agent meta + recommendations */}
        {data && !loading && (
          <div className="space-y-10">

            {/* Agent Reasoning card */}
            {data.agent && (
              <div className="bg-gradient-to-br from-indigo-50 to-violet-50 border border-indigo-100 rounded-3xl p-8">
                <div className="flex items-start justify-between gap-6 mb-6">
                  <div>
                    <p className="text-[10px] font-extrabold text-indigo-400 uppercase tracking-widest mb-1">Agent Reasoning</p>
                    <h2 className="text-xl font-extrabold text-gray-900">Agentic Intervention Plan</h2>
                    <p className="text-sm text-gray-500 mt-1 font-medium">
                      Personalised interventions generated live by the Cognitive Health Agent.
                    </p>
                  </div>
                  <div className={`px-3 py-1.5 rounded-xl text-[11px] font-bold border ${
                    data.agent.agent_confidence === "high"   ? "bg-emerald-50 text-emerald-700 border-emerald-200" :
                    data.agent.agent_confidence === "medium" ? "bg-amber-50 text-amber-700 border-amber-100" :
                    "bg-gray-50 text-gray-600 border-gray-200"
                  }`}>
                    {data.agent.agent_confidence === "high" ? "High Confidence" :
                     data.agent.agent_confidence === "medium" ? "Medium Confidence" : "Low Confidence"}
                  </div>
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                  <div className="bg-white/70 rounded-2xl p-5 border border-indigo-100/50">
                    <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-2">Reasoning</p>
                    <p className="text-sm text-gray-700 font-medium leading-relaxed">{data.agent.reasoning}</p>
                  </div>
                  <div className="bg-white/70 rounded-2xl p-5 border border-indigo-100/50">
                    <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-2">Primary Lever</p>
                    <p className="text-sm font-bold text-indigo-700">{data.agent.primary_lever}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {data.agent.tools_called.map((t) => (
                        <span key={t} className="text-[10px] font-bold px-2 py-1 bg-indigo-100 text-indigo-600 rounded-lg">
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Section header */}
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-2xl bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-200">
                <Layers className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-extrabold text-gray-900 tracking-tight">
                  {data.recommendations.length} Personalised Interventions
                </h2>
                <p className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mt-0.5">
                   Ranked by causal impact · SAARTHI.AI Ensemble v2
                </p>
              </div>
            </div>

            {/* Recommendation cards */}
            <div className="space-y-4">
              {data.recommendations.map((rec, idx) => {
                const impact = rec.impact?.toLowerCase() as keyof typeof IMPACT_CONFIG;
                const cfg = IMPACT_CONFIG[impact] ?? IMPACT_CONFIG.low;

                return (
                  <div
                    key={rec.priority}
                    className="group bg-white border border-gray-100 rounded-3xl p-6 hover:border-indigo-200 hover:shadow-lg hover:shadow-indigo-50 transition-all duration-300"
                  >
                    <div className="flex items-start gap-5">
                      {/* Number badge */}
                      <div className="w-10 h-10 rounded-2xl bg-indigo-600 text-white font-black text-sm flex items-center justify-center shrink-0 shadow-md shadow-indigo-200 group-hover:scale-110 transition-transform">
                        {idx + 1}
                      </div>

                      <div className="flex-1 min-w-0">
                        <p className="text-base font-extrabold text-gray-900 leading-snug mb-2">
                          {rec.action}
                        </p>

                        {/* Timeframe */}
                        <div className="flex items-center gap-1.5 mb-3">
                          <Clock className="w-3 h-3 text-gray-400" />
                          <span className="text-xs text-gray-500 font-medium">{rec.timeframe}</span>
                        </div>

                        <p className="text-sm text-gray-500 leading-relaxed mb-4">{rec.reason}</p>

                        {/* Causal chain */}
                        {rec.causal_mechanism && (
                          <div className="flex items-center gap-2 text-[11px] font-bold text-indigo-500 mb-4 bg-indigo-50 px-3 py-2 rounded-xl border border-indigo-100">
                            <span className="text-indigo-300">↳</span>
                            {rec.causal_mechanism}
                          </div>
                        )}

                        {/* Tags row */}
                        <div className="flex flex-wrap items-center gap-2">
                          <span className={`inline-flex items-center gap-1.5 text-[10px] font-bold px-3 py-1.5 rounded-xl border ${cfg.bg} ${cfg.text} ${cfg.border}`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
                            {cfg.label}
                          </span>

                          <span className="text-[10px] font-bold px-3 py-1.5 rounded-xl bg-gray-50 text-gray-500 border border-gray-100">
                            Mitigation
                          </span>

                          {rec.estimated_risk_reduction != null && rec.estimated_risk_reduction > 0 && (
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold px-3 py-1.5 rounded-xl bg-emerald-50 text-emerald-700 border border-emerald-100">
                              <TrendingDown className="w-3 h-3" />
                              −{rec.estimated_risk_reduction.toFixed(1)} pts risk
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Footer */}
            <div className="flex items-center gap-3 pt-6 border-t border-gray-100">
              <div className="flex-1 text-xs text-gray-400 font-medium">
                Generated by Groq LLaMA-3 · SAARTHI.AI Ensemble v2 · {new Date().toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}
              </div>
              <button
                onClick={() => router.push("/dashboard")}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gray-50 border border-gray-100 text-gray-600 text-xs font-bold hover:bg-indigo-50 hover:border-indigo-200 hover:text-indigo-700 transition-all"
              >
                Back to Vitals <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
