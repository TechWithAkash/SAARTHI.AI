"use client";

interface Recommendation {
  priority: number;
  action: string;
  reason: string;
  impact: string;
  timeframe: string;
  estimated_risk_reduction?: number | null;
  risk_reduction_source?: string | null;
  causal_factor?: string | null;
}

interface Props {
  recommendations: Recommendation[];
  method?: string;
}

const IMPACT_STYLES: Record<string, { dot: string; text: string; bg: string; border: string }> = {
  high:   { dot: "bg-emerald-500", text: "text-emerald-700", bg: "bg-emerald-50", border: "border-emerald-100" },
  medium: { dot: "bg-amber-500",   text: "text-amber-700",   bg: "bg-amber-50",   border: "border-amber-100" },
  low:    { dot: "bg-slate-400",   text: "text-slate-600",   bg: "bg-slate-50",   border: "border-slate-200" },
};

export default function RecommendationCard({ recommendations, method }: Props) {
  if (!recommendations || recommendations.length === 0) return null;

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-6">
      <div className="flex items-center justify-between mb-5">
        <div>
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Clinical Action Plan</span>
          <h3 className="text-lg font-bold text-slate-900 mt-0.5">Personalised Lifestyle Recommendations</h3>
        </div>
        <span className="text-xs font-medium text-slate-500 bg-slate-100 px-3 py-1 rounded-lg">
          {recommendations.length} Action Items
        </span>
      </div>

      <div className="space-y-3">
        {recommendations.map((rec) => {
          const s = IMPACT_STYLES[rec.impact?.toLowerCase()] ?? IMPACT_STYLES.low;
          return (
            <div key={rec.priority} className="flex gap-4 p-4 rounded-xl border border-slate-100 bg-slate-50/60 hover:bg-white hover:border-slate-200 transition-all">
              <div className="w-7 h-7 rounded-lg bg-blue-50 text-blue-700 font-bold text-xs flex items-center justify-center shrink-0 mt-0.5 border border-blue-100">
                {rec.priority}
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-bold text-slate-900 leading-snug mb-1">{rec.action}</h4>
                <p className="text-xs text-slate-600 leading-relaxed mb-3">{rec.reason}</p>
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`inline-flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-0.5 rounded-md border ${s.bg} ${s.text} ${s.border}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
                    {rec.impact?.toUpperCase()} IMPACT
                  </span>
                  <span className="text-[11px] font-medium px-2.5 py-0.5 rounded-md bg-slate-100 text-slate-600 border border-slate-200/60">
                    Timeframe: {rec.timeframe}
                  </span>
                  {rec.estimated_risk_reduction != null && rec.estimated_risk_reduction > 0 && (
                    rec.risk_reduction_source === "causal_ate" ? (
                      <span
                        className="text-[11px] font-semibold px-2.5 py-0.5 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-100"
                        title={`Measured causal effect${rec.causal_factor ? ` of ${rec.causal_factor}` : ""} on risk score`}
                      >
                        −{rec.estimated_risk_reduction.toFixed(1)} pts (measured)
                      </span>
                    ) : (
                      <span
                        className="text-[11px] font-semibold px-2.5 py-0.5 rounded-md bg-amber-50 text-amber-700 border border-amber-100"
                        title="Attribution-derived estimate — not yet a measured causal effect"
                      >
                        ~{rec.estimated_risk_reduction.toFixed(1)} pts (est.)
                      </span>
                    )
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
