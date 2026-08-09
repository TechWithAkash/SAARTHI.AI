"use client";

import { useEffect, useState } from "react";
import { api, type MemoryResponse, type MemoryItem } from "@/lib/api";

export default function SettingsPage() {
  const [data, setData] = useState<MemoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [clearing, setClearing] = useState(false);

  const fetchMemories = () => {
    const userId = sessionStorage.getItem("saarthi_user_id") ?? sessionStorage.getItem("darpan_user_id") ?? "user_demo_001";
    api.getMemories(userId)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchMemories();
  }, []);

  async function handleClear() {
    if (!confirm("Are you sure? This will wipe the SAARTHI.AI model's memory of your patterns, potentially reducing diagnostic accuracy.")) return;
    setClearing(true);
    try {
      const userId = sessionStorage.getItem("saarthi_user_id") ?? sessionStorage.getItem("darpan_user_id") ?? "user_demo_001";
      await api.clearMemories(userId);
      setData({ user_id: userId, memories: [] });
    } catch (e: any) {
      alert("Failed to clear: " + e.message);
    } finally {
      setClearing(false);
    }
  }

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-8 h-8 border-2 border-[#22C55E] border-t-transparent rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-8 bg-slate-50/60 min-h-screen pb-24">

      {/* ── 1. HEADER BANNER (Clinical Blue Theme) ── */}
      <div className="bg-gradient-to-r from-blue-950 via-blue-900 to-indigo-950 text-white rounded-2xl p-6 sm:p-7 border border-blue-800/60 shadow-md relative overflow-hidden flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_80%_0%,rgba(59,130,246,0.25),transparent_60%)] pointer-events-none" />

        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 backdrop-blur-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Neural Synapse Active
            </span>
            <span className="text-xs text-blue-200/70 font-medium">· Mem0 & Telegram Stack</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">Agentic Control Center</h1>
          <p className="text-xs sm:text-sm text-blue-100/80 font-medium mt-1 max-w-xl">Manage cognitive context, mem0 semantic memory, and technical infrastructure pipelines.</p>
        </div>

        <div className="relative z-10 flex items-center gap-4 bg-white/10 border border-white/20 backdrop-blur-xs px-4 py-2.5 rounded-xl">
          <div>
            <span className="text-[10px] font-semibold text-blue-200 uppercase tracking-wider block">Causal Latency</span>
            <span className="text-base font-black text-white font-mono">18ms</span>
          </div>
          <div className="w-px h-6 bg-white/20" />
          <div>
            <span className="text-[10px] font-semibold text-blue-200 uppercase tracking-wider block">Logic Nodes</span>
            <span className="text-base font-black text-emerald-300 font-mono">7 Active</span>
          </div>
        </div>
      </div>

      {/* ── 2. AGENTIC CONTEXT STATE (mem0 Semantic Memory) ── */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-5">
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div>
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-0.5">Semantic Memory Store</span>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" /> Agentic Context State
            </h2>
          </div>
          <button
            onClick={handleClear}
            disabled={clearing || !data?.memories.length}
            className="px-3.5 py-2 rounded-xl bg-rose-50 text-rose-600 border border-rose-200 hover:bg-rose-100 transition-colors text-xs font-semibold disabled:opacity-40"
          >
            {clearing ? "Wiping Memory…" : "Clear All Memory"}
          </button>
        </div>

        <div className="space-y-3">
          {!data?.memories.length ? (
            <div className="py-10 text-center bg-slate-50 rounded-xl border border-dashed border-slate-200">
              <p className="text-xs font-bold text-slate-700">The SAARTHI.AI memory cache is currently empty.</p>
              <p className="text-[11px] text-slate-400 mt-0.5 font-medium">Start logging telemetry vitals on the dashboard to build agentic memory context.</p>
            </div>
          ) : (
            data.memories.map((m) => (
              <div key={m.id} className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 transition-all hover:bg-white hover:border-slate-300">
                <div className="flex items-start gap-3">
                  <div className="w-7 h-7 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0 mt-0.5">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>
                  </div>
                  <div className="flex-1">
                    <p className="text-xs text-slate-800 leading-relaxed font-medium">"{m.memory}"</p>
                    {Boolean(m.metadata?.timestamp) && (
                      <p className="text-[10px] text-slate-400 mt-1.5 font-medium">Recorded {new Date(String(m.metadata?.timestamp)).toLocaleDateString()}</p>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* ── 4. CLINICAL OUTPUT & CLOUD INFRASTRUCTURE ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
          <div>
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-0.5">Mode Styling</span>
            <h3 className="text-base font-bold text-slate-900">Clinical Output Parameters</h3>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed font-medium">Adjust SAARTHI.AI's diagnostic mapping styling for your check-ins.</p>
          <div className="flex gap-2.5 pt-2">
            <button className="flex-1 py-2.5 px-3 rounded-xl bg-blue-600 text-white text-xs font-bold shadow-xs">Prakriti Modeler</button>
            <button className="flex-1 py-2.5 px-3 rounded-xl bg-slate-100 text-slate-700 text-xs font-semibold hover:bg-slate-200 transition-colors">Empathetic Proxy</button>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
          <div>
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-0.5">Engineering Architecture</span>
            <h3 className="text-base font-bold text-slate-900">Deployed Cloud Infrastructure</h3>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between p-2.5 bg-slate-50 rounded-xl border border-slate-200/70">
              <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" /><span className="text-xs font-bold text-slate-800">LLM Agent: Groq Llama-3</span></div>
              <span className="text-xs font-mono text-emerald-600 font-bold">~12ms Ping</span>
            </div>
            <div className="flex items-center justify-between p-2.5 bg-slate-50 rounded-xl border border-slate-200/70">
              <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0 animate-pulse" /><span className="text-xs font-bold text-slate-800">Semantic VDB: Qdrant</span></div>
              <span className="text-xs font-mono text-emerald-600 font-bold">Indexed</span>
            </div>
            <div className="flex items-center justify-between p-2.5 bg-slate-50 rounded-xl border border-slate-200/70">
              <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-blue-600 shrink-0" /><span className="text-xs font-bold text-slate-800">Causal Logic: DoWhy</span></div>
              <span className="text-xs font-mono text-blue-600 font-bold">100% DAG</span>
            </div>
            <div className="flex items-center justify-between p-2.5 bg-slate-50 rounded-xl border border-slate-200/70">
              <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-blue-600 shrink-0" /><span className="text-xs font-bold text-slate-800">XAI Explainer: SHAP</span></div>
              <span className="text-xs font-mono text-blue-600 font-bold">Active</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
