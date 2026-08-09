"use client";

import { useEffect, useState } from "react";
import { api, type SimulationResponse, type Recommendation, type AgentMeta, type WhatIfResponse } from "@/lib/api";
import SimulationChart from "@/components/SimulationChart";
import AgentTrace from "@/components/AgentTrace";
import WhatIfSimulator from "@/components/WhatIfSimulator";

export default function SimulationPage() {
  const [sim, setSim] = useState<SimulationResponse | null>(null);
  const [simLoading, setSimLoading] = useState(true);
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [agent, setAgent] = useState<AgentMeta | null>(null);
  const [agentDone, setAgentDone] = useState(false);
  const [userId, setUserId] = useState("");
  const [whatIfResult, setWhatIfResult] = useState<WhatIfResponse | null>(null);

  useEffect(() => {
    const uid = sessionStorage.getItem("saarthi_user_id") ?? sessionStorage.getItem("darpan_user_id") ?? "user_demo_001";
    setUserId(uid);

    api.getSimulation(uid)
      .then(setSim)
      .catch((err: any) => {
        if (err?.status !== 404) {
          console.error("Simulation load error:", err);
        }
      })
      .finally(() => setSimLoading(false));
  }, []);

  function handleAgentComplete(
    newRecs: Recommendation[],
    newAgent: AgentMeta,
  ) {
    setRecs(newRecs);
    setAgent(newAgent);
    setAgentDone(true);
  }

  if (simLoading) return <LoadingState />;
  if (!sim) return <EmptyState />;

  // The what-if endpoint returns one number: your risk if this state is
  // sustained for 30 days. It doesn't return a full 120-day curve, so this
  // interpolates linearly from today's real baseline (day 0) to that 30-day
  // projection, then holds flat after day 30 — the same shape the existing
  // Improved/Optimal lines already use (decline, then plateau). No new
  // backend call: reuses the same postWhatIf result already shown below.
  const whatIfLine = whatIfResult
    ? sim.timeline_days.map((day) => {
        const base = whatIfResult.baseline.composite_risk;
        const target = whatIfResult.counterfactual.composite_risk;
        if (day >= 30) return target;
        return base + (target - base) * (day / 30);
      })
    : null;

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-8 bg-slate-50/60 min-h-screen pb-24">

      {/* ── 1. HEADER BANNER (Clinical Blue Theme) ── */}
      <div className="bg-gradient-to-r from-blue-950 via-blue-900 to-indigo-950 text-white rounded-2xl p-6 sm:p-7 border border-blue-800/60 shadow-md relative overflow-hidden flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_80%_0%,rgba(59,130,246,0.25),transparent_60%)] pointer-events-none" />

        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 backdrop-blur-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Live Causal Engine Active
            </span>
            <span className="text-xs text-blue-200/70 font-medium">· 120-Day Horizon</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">Risk Trajectory Simulation</h1>
          <p className="text-xs sm:text-sm text-blue-100/80 font-medium mt-1">Real-time simulation modeling a 120-day physiological horizon using Causal AI.</p>
        </div>

        <div className="relative z-10 flex items-center gap-3">
          <a
            href="/dashboard"
            className="flex items-center gap-2 px-4 py-2.5 bg-white/10 hover:bg-white/20 border border-white/20 text-white rounded-xl text-xs font-semibold backdrop-blur-xs transition-all"
          >
            ← Back to Dashboard
          </a>
        </div>
      </div>

      {/* ── 2. 120-DAY TRAJECTORY CHART ── */}
      <div className="w-full bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
        <SimulationChart
          scenarios={sim.scenarios}
          timelineDays={sim.timeline_days}
          projectedReduction={sim.projected_risk_reduction}
          whatIfValues={whatIfLine}
        />
      </div>

      {/* ── 2b. INTERACTIVE WHAT-IF PREDICTOR ── */}
      {userId && <WhatIfSimulator userId={userId} onResult={setWhatIfResult} />}
      {whatIfResult && (
        <p className="text-xs text-slate-400 -mt-4 px-1">
          The dashed blue <span className="font-semibold text-blue-600">What-If</span> line on the graph above
          reflects the sliders you're currently moving.
        </p>
      )}

      {/* ── 3. THREE SCENARIO CARDS ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <ScenarioCard
          label="Current Baseline"
          description="Your risk trajectory if current behaviors continue uninterrupted."
          reduction={0}
          interventions={[]}
          color="#64748B"
        />
        <ScenarioCard
          label="Target Improvement"
          description="Achievable risk mitigation via targeted agentic lifestyle optimizations."
          reduction={sim.projected_risk_reduction.improved}
          interventions={recs.slice(0, 2).map((r) => r.action)}
          color="#2563EB"
        />
        <ScenarioCard
          label="Optimal Equilibrium"
          description="Mathematical minimization of all modifiable causal risk nodes."
          reduction={sim.projected_risk_reduction.optimal}
          interventions={recs.map((r) => r.action)}
          color="#10B981"
        />
      </div>

      {/* ── 4. AGENTIC INTELLIGENCE TRACE ── */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-0.5">Agentic Intelligence</span>
            <h2 className="text-base font-bold text-slate-900">4-Step Cognitive Agentic Pipeline</h2>
          </div>
        </div>

        {userId && (
          <AgentTrace userId={userId} onComplete={handleAgentComplete} />
        )}
      </div>

      {/* ── 5. AGENTIC INTERVENTION PLAN ── */}
      {/* This used to render nothing at all when the agent finished with
          zero recommendations (e.g. the Recommendation Engine step failing
          upstream, most commonly a Groq rate limit) — the whole section just
          silently vanished with no explanation. Steps 1-3 can still produce
          real, useful output (risk summary, memory, causal lever) even when
          step 4 fails, so that partial result is shown honestly instead of
          an empty page. */}
      {agentDone && recs.length === 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs text-center space-y-2">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Synthesized Interventions</span>
          <h3 className="text-base font-bold text-slate-900">Recommendation Step Didn't Complete</h3>
          <p className="text-xs text-slate-500 font-medium max-w-md mx-auto">
            The first 3 agent steps ran, but step 4 (Recommendation Engine) returned nothing —
            most often because the AI provider is temporarily rate-limited. Your risk numbers above
            are unaffected; only this synthesized action list is missing. Reloading later will retry it.
          </p>
        </div>
      )}
      {agentDone && recs.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs animate-in fade-in duration-500 space-y-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-0.5">Synthesized Interventions</span>
              <h2 className="text-lg font-bold text-slate-900">Agentic Intervention Action Plan</h2>
            </div>
            {agent && (
              <div className="mt-2 sm:mt-0">
                <ConfidenceBadge level={agent.agent_confidence} />
              </div>
            )}
          </div>

          {agent?.reasoning && (
            <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-4 space-y-2">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Agent Reasoning</span>
              <p className="text-xs text-slate-700 leading-relaxed font-medium">{agent.reasoning}</p>
              {agent.primary_lever && (
                <div className="pt-1 flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-500">Primary Lever:</span>
                  <span className="text-xs font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 rounded-full capitalize">
                    {agent.primary_lever.replace(/_/g, " ")}
                  </span>
                </div>
              )}
            </div>
          )}

          <div className="space-y-3">
            {recs.map((rec, idx) => (
              <div
                key={rec.priority}
                className="flex flex-col sm:flex-row gap-4 p-5 rounded-xl border border-slate-100 bg-slate-50/50 hover:bg-white hover:border-slate-200 transition-all"
              >
                <div className="w-9 h-9 rounded-xl bg-blue-50 text-blue-700 border border-blue-100 font-bold text-xs flex items-center justify-center shrink-0">
                  {idx + 1}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-1 gap-2">
                    <h4 className="text-sm font-bold text-slate-900 leading-snug">{rec.action}</h4>
                    <span className="text-[11px] font-medium text-slate-600 bg-slate-100 border border-slate-200/60 px-2.5 py-0.5 rounded-md">
                      {rec.timeframe}
                    </span>
                  </div>

                  <p className="text-xs text-slate-600 leading-relaxed mb-3">{rec.reason}</p>

                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 rounded-md uppercase">
                      {rec.impact} impact
                    </span>
                  </div>
                </div>

                {rec.estimated_risk_reduction != null && rec.estimated_risk_reduction > 0 && (
                  <div className="flex sm:flex-col items-center justify-center border-t sm:border-t-0 sm:border-l border-slate-100 pt-3 sm:pt-0 sm:pl-5 shrink-0">
                    <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">Mitigation</span>
                    <span className="text-xl font-black text-emerald-600">
                      −{rec.estimated_risk_reduction.toFixed(1)} <span className="text-xs font-semibold text-emerald-500">pts</span>
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ConfidenceBadge({ level }: { level: string }) {
  const config = {
    high: { label: "High Confidence", color: "text-emerald-700 bg-emerald-50 border-emerald-200" },
    medium: { label: "Medium Confidence", color: "text-amber-700 bg-amber-50 border-amber-200" },
    low: { label: "Low Confidence", color: "text-red-600 bg-red-50 border-red-200" },
  }[level] ?? { label: level, color: "text-gray-500 bg-gray-50 border-gray-100" };
  return (
    <span className={`text-[10px] font-bold uppercase tracking-widest px-3 py-1 rounded-full border ${config.color}`}>
      {config.label}
    </span>
  );
}

function ScenarioCard({ label, color, description, reduction, interventions }: {
  label: string; color: string; description: string; reduction: number; interventions: string[];
}) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs flex flex-col justify-between h-full hover:border-slate-300 transition-all">
      <div>
        <div className="flex items-center gap-2 mb-3">
          <div className="w-2.5 h-2.5 rounded-full" style={{ background: color }} />
          <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">{label}</span>
        </div>
        <p className="text-xs text-slate-500 leading-relaxed mb-4 font-medium">{description}</p>
        {interventions.length > 0 && (
          <div className="mb-4">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">
              Action Plan Interventions
            </span>
            <ul className="space-y-1.5">
              {interventions.slice(0, 2).map((inv, i) => (
                <li key={i} className="text-xs text-slate-600 font-medium flex items-start gap-2">
                  <span className="w-1.5 h-1.5 bg-blue-500 rounded-full shrink-0 mt-1.5" />
                  <span className="truncate">{inv}</span>
                </li>
              ))}
              {interventions.length > 2 && (
                <li className="text-[11px] text-blue-600 font-semibold ml-3.5">
                  +{interventions.length - 2} more items
                </li>
              )}
            </ul>
          </div>
        )}
      </div>
      <div className="pt-4 border-t border-slate-100 flex items-baseline justify-between mt-auto">
        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Projected Drop</span>
        {reduction > 0 ? (
          <span className="text-2xl font-black text-emerald-600">
            −{reduction.toFixed(1)}%
          </span>
        ) : (
          <span className="text-2xl font-black text-slate-400">0.0%</span>
        )}
      </div>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="text-center">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-sm text-gray-400">Loading simulation…</p>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-72 text-center gap-4">
      <div className="w-14 h-14 rounded-3xl bg-indigo-50 flex items-center justify-center">
        <svg className="w-7 h-7 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
        </svg>
      </div>
      <div>
        <p className="text-sm font-bold text-gray-800">No simulation data yet</p>
        <p className="text-xs text-gray-400 mt-1">Submit your vitals from the Dashboard first.</p>
      </div>
      <a href="/dashboard" className="text-xs font-bold text-indigo-600 border border-indigo-200 px-4 py-2 rounded-xl hover:bg-indigo-50 transition-colors">
        Go to Dashboard →
      </a>
    </div>
  );
}
