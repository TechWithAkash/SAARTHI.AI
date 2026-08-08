"use client";

import { useEffect, useState } from "react";
import { api, type AlertsResponse } from "@/lib/api";
import AlertBanner from "@/components/AlertBanner";

export default function AlertsPage() {
  const [data, setData] = useState<AlertsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAlerts = () => {
    const userId = sessionStorage.getItem("saarthi_user_id") ?? sessionStorage.getItem("darpan_user_id") ?? "user_demo_001";
    api.getAlerts(userId)
      .then(setData)
      .catch((e: any) => setError(e.detail ?? e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchAlerts();
  }, []);

  async function handleAcknowledge(alertId: string) {
    try {
      await api.acknowledgeAlert(alertId);
      // Optimistic update or refresh
      fetchAlerts();
    } catch (e: any) {
      alert("Failed to acknowledge: " + e.message);
    }
  }

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-8 h-8 border-2 border-[#22C55E] border-t-transparent rounded-full animate-spin" />
    </div>
  );

  if (error) return (
    <div className="bg-red-50 border border-red-200 rounded-2xl p-6 text-center">
      <p className="text-sm text-red-600 font-bold">{error}</p>
    </div>
  );

  if (!data) return null;

  const criticalCount = data.alerts.filter((a) => a.severity === "critical" || a.severity === "high").length;

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-8 bg-slate-50/60 min-h-screen pb-24">

      {/* ── 1. HEADER BANNER (Clinical Blue Theme) ── */}
      <div className="bg-gradient-to-r from-blue-950 via-blue-900 to-indigo-950 text-white rounded-2xl p-6 sm:p-7 border border-blue-800/60 shadow-md relative overflow-hidden flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_80%_0%,rgba(59,130,246,0.25),transparent_60%)] pointer-events-none" />

        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 backdrop-blur-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Diagnostic Stack Active
            </span>
            <span className="text-xs text-blue-200/70 font-medium">· Real-Time Anomaly Stream</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">Clinical Alerts & Telemetry</h1>
          <p className="text-xs sm:text-sm text-blue-100/80 font-medium mt-1">Anomalies and out-of-bounds vitals detected by Aura's multi-layered diagnostic stack.</p>
        </div>

        {data.alerts.length > 0 && (
          <div className="relative z-10 flex items-center gap-3 bg-white/10 border border-white/20 backdrop-blur-xs px-4 py-2.5 rounded-xl">
            <div className="text-right">
              <span className="text-[11px] font-semibold text-blue-200 uppercase tracking-wider block">{data.alerts.length} Total Alerts</span>
              {criticalCount > 0 ? (
                <span className="text-xs font-black text-rose-300 block">{criticalCount} Critical Action Required</span>
              ) : (
                <span className="text-xs font-bold text-emerald-300 block">0 Critical Blockers</span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── 2. ALERT BANNER LIST ── */}
      <div className="animate-in fade-in duration-500">
        <AlertBanner 
          alerts={data.alerts} 
          onAcknowledge={handleAcknowledge}
        />
      </div>

      {/* ── 3. DIAGNOSTIC ACCURACY FOOTER ── */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-2">
        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Diagnostic Architecture</span>
        <h3 className="text-sm font-bold text-slate-900">3-Layer Multi-Stage Validation Stack</h3>
        <p className="text-xs text-slate-600 leading-relaxed font-medium">
          Alerts are generated using a 3-layer validation stack: 
          <strong> (1) Clinical Reference Range Bounds</strong>, 
          <strong> (2) Rolling Personal Z-Score Baseline</strong>, and 
          <strong> (3) Isolation Forest Unsupervised Anomaly Model</strong>. 
          Acknowledging alerts trains Aura's feedback loop to refine sensitivity for your unique physiological baseline.
        </p>
      </div>
    </div>
  );
}
