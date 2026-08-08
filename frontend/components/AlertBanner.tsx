"use client";

interface Alert {
  id: string;
  metric: string;
  severity: string;
  message: string;
  value: number;
  timestamp?: string;
}

interface Props {
  alerts: Alert[];
  onAcknowledge?: (id: string) => void;
}

const SEV_STYLES: Record<string, { bg: string; border: string; dot: string; label: string; badgeBg: string; text: string }> = {
  critical: { bg: "bg-white", border: "border-rose-200 hover:border-rose-300", dot: "bg-rose-500", label: "Critical", badgeBg: "bg-rose-50 text-rose-700 border-rose-200", text: "text-rose-900" },
  high:     { bg: "bg-white", border: "border-amber-200 hover:border-amber-300", dot: "bg-amber-500", label: "High", badgeBg: "bg-amber-50 text-amber-800 border-amber-200", text: "text-amber-900" },
  medium:   { bg: "bg-white", border: "border-amber-200 hover:border-amber-300", dot: "bg-amber-500", label: "Medium", badgeBg: "bg-amber-50 text-amber-800 border-amber-200", text: "text-amber-900" },
  moderate: { bg: "bg-white", border: "border-amber-200 hover:border-amber-300", dot: "bg-amber-500", label: "Moderate", badgeBg: "bg-amber-50 text-amber-800 border-amber-200", text: "text-amber-900" },
  low:      { bg: "bg-white", border: "border-emerald-200 hover:border-emerald-300", dot: "bg-emerald-500", label: "Low", badgeBg: "bg-emerald-50 text-emerald-800 border-emerald-200", text: "text-emerald-900" },
};

const DEFAULT_STYLE = { bg: "bg-white", border: "border-slate-200 hover:border-slate-300", dot: "bg-slate-400", label: "Info", badgeBg: "bg-slate-100 text-slate-800 border-slate-200", text: "text-slate-900" };

export default function AlertBanner({ alerts, onAcknowledge }: Props) {
  if (!alerts || alerts.length === 0) {
    return (
      <div className="bg-emerald-50/70 border border-emerald-200/90 rounded-2xl p-6 flex items-center justify-between shadow-xs">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-emerald-500 flex items-center justify-center text-white shrink-0 shadow-2xs">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" /></svg>
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900">All Physiological Systems Nominal</h3>
            <p className="text-xs text-slate-500 font-medium mt-0.5">No anomalies detected across recent diagnostic layers.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3.5">
      {alerts.map((alert) => {
        const s = SEV_STYLES[alert.severity?.toLowerCase()] ?? DEFAULT_STYLE;
        const label = alert.metric ?? "Unknown";
        return (
          <div key={alert.id} className={`${s.bg} border ${s.border} rounded-2xl p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 transition-all shadow-xs`}>
            <div className="flex items-start gap-3.5 min-w-0">
              <div className={`w-2.5 h-2.5 rounded-full ${s.dot} mt-1.5 shrink-0 animate-pulse`} />
              <div className="min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-bold text-slate-900 uppercase tracking-tight">{label.replace(/_/g, " ")}</span>
                  <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full border ${s.badgeBg}`}>{s.label}</span>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed font-medium">{alert.message}</p>
                <div className="flex items-center gap-4 mt-2">
                  <span className="text-xs font-semibold text-slate-500">Observed Value: <span className="text-slate-900 font-bold">{alert.value}</span></span>
                  {alert.timestamp && (
                    <span className="text-[11px] font-medium text-slate-400">{new Date(alert.timestamp).toLocaleTimeString()}</span>
                  )}
                </div>
              </div>
            </div>

            {onAcknowledge && (
              <button
                onClick={() => onAcknowledge(alert.id)}
                className="shrink-0 px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold border border-slate-200 transition-colors shadow-2xs"
              >
                Acknowledge Alert
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}
