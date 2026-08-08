"use client";

import { useEffect, useState } from "react";
import { api, type InsightsResponse, type InsightsFactor } from "@/lib/api";
import InsightsBar from "@/components/InsightsBar";
import CausalMap from "@/components/CausalMap";

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-72 text-center gap-4">
      <div className="w-14 h-14 rounded-3xl bg-[#ECFDF5] flex items-center justify-center">
        <svg className="w-7 h-7 text-[#22C55E]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
      </div>
      <div>
        <p className="text-sm font-bold text-gray-800">No insights yet</p>
        <p className="text-xs text-gray-400 mt-1">Submit your vitals from the Dashboard to generate causal analysis.</p>
      </div>
      <a href="/" className="text-xs font-bold text-[#22C55E] border border-[#86EFAC] px-4 py-2 rounded-xl hover:bg-[#ECFDF5] transition-colors">
        Go to Dashboard →
      </a>
    </div>
  );
}

function deriveFactors(shap: Record<string, number>): {
  drivers: InsightsFactor[];
  protective: InsightsFactor[];
} {
  const drivers: InsightsFactor[] = [];
  const protective: InsightsFactor[] = [];
  for (const [factor, contribution] of Object.entries(shap)) {
    const entry: InsightsFactor = { factor, contribution, description: factor.replace(/_/g, " ") };
    if (contribution > 0) drivers.push(entry);
    else protective.push(entry);
  }
  drivers.sort((a, b) => b.contribution - a.contribution);
  protective.sort((a, b) => a.contribution - b.contribution);
  return { drivers, protective };
}

export default function InsightsPage() {
  const [data, setData] = useState<InsightsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const userId = sessionStorage.getItem("saarthi_user_id") ?? sessionStorage.getItem("darpan_user_id") ?? "user_demo_001";
    api.getInsights(userId)
      .then(setData)
      .catch((e: any) => {
        setError(e.detail ?? (e.status === 404 ? "No health insights found for user. Submit your health metrics on the dashboard to generate insights." : e.message));
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-8 h-8 border-2 border-[#22C55E] border-t-transparent rounded-full animate-spin" />
    </div>
  );

  if (error) return <EmptyState />;


  if (!data) return <EmptyState />;

  const { drivers, protective } = deriveFactors(data.shap_contributions ?? {});

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-8 bg-slate-50/60 min-h-screen pb-24">

      {/* ── 1. HEADER BANNER (Clinical Blue Theme) ── */}
      <div className="bg-gradient-to-r from-blue-950 via-blue-900 to-indigo-950 text-white rounded-2xl p-6 sm:p-7 border border-blue-800/60 shadow-md relative overflow-hidden flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_80%_0%,rgba(59,130,246,0.25),transparent_60%)] pointer-events-none" />

        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 backdrop-blur-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Causal Relationship Matrix Active
            </span>
            <span className="text-xs text-blue-200/70 font-medium">· DoWhy & SHAP Engine</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">Clinical Causal Insights</h1>
          <p className="text-xs sm:text-sm text-blue-100/80 font-medium mt-1">Deep SHAP value decomposition uncovering the exact causal drivers of your physiological baseline.</p>
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

      {/* ── 2. CAUSAL RELATIONSHIP MAP ── */}
      <CausalMap
        primaryCause={data.primary_cause}
        causalChain={data.causal_chain}
      />

      {/* ── 3. ROOT CAUSE IDENTIFICATION CALLOUT ── */}
      {data.primary_cause && (
        <div className="bg-emerald-50/70 border border-emerald-200/90 rounded-2xl p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-emerald-800 uppercase tracking-wider block">Root Cause Identification</span>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
              Primary Driver Isolated
            </span>
          </div>

          <div>
            <h2 className="text-2xl font-black text-slate-900 capitalize tracking-tight">{data.primary_cause.replace(/_/g, " ")}</h2>
            <div className="mt-2 inline-flex items-center gap-2 bg-white px-3 py-1 rounded-lg border border-emerald-200 shadow-2xs">
              <span className="text-xs font-bold text-emerald-700">Causal Path:</span>
              <span className="text-xs text-slate-700 font-semibold">{data.causal_chain}</span>
            </div>
          </div>

          <p className="text-xs text-slate-700 leading-relaxed font-medium max-w-3xl">
            The SAARTHI.AI engine has isolated <strong className="text-emerald-800">{data.primary_cause.replace(/_/g, " ")}</strong> as the primary independent lever influencing your baseline risk. Modifying this physiological factor cascades through the mapped causal chain, yielding the highest statistical mitigation in downstream health risk.
          </p>
        </div>
      )}

      {/* ── 4. SHAP VALUE DECOMPOSITION ── */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-6">
        <div className="flex justify-between items-center border-b border-slate-100 pb-4">
          <div>
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-0.5">Feature Attribution</span>
            <h3 className="text-base font-bold text-slate-900">SHAP Value Feature Attribution</h3>
          </div>
          <span className="text-xs font-semibold text-slate-500 bg-slate-100 px-3 py-1 rounded-lg border border-slate-200/60">
            Data Science Verified
          </span>
        </div>
        <InsightsBar drivers={drivers} protective={protective} />
      </div>
    </div>
  );
}
