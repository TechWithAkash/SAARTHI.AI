"use client";

import { AreaChart, Area, ResponsiveContainer, Tooltip } from "recharts";

interface Props {
  score: number;
  category: string;
  topFactors: string[];
  history?: { timestamp: string; risk_score: number }[];
}

const CATEGORY_MAP: Record<string, { label: string; badge: string; bar: string; chart: string; text: string }> = {
  Low:      { label: "Low Risk (< 10%)",       badge: "bg-emerald-50 text-emerald-700 border-emerald-200", bar: "bg-emerald-500", chart: "#10B981", text: "text-emerald-700" },
  Moderate: { label: "Moderate Risk (10–30%)", badge: "bg-amber-50 text-amber-700 border-amber-200",     bar: "bg-amber-500",   chart: "#F59E0B", text: "text-amber-700" },
  High:     { label: "Elevated Risk (30–60%)", badge: "bg-orange-50 text-orange-700 border-orange-200", bar: "bg-orange-500", chart: "#F97316", text: "text-orange-700" },
  Critical: { label: "High Risk (> 60%)",      badge: "bg-rose-50 text-rose-700 border-rose-200",         bar: "bg-rose-500",   chart: "#EF4444", text: "text-rose-700" },
};

export default function RiskCard({ score, category, topFactors, history = [] }: Props) {
  const style = CATEGORY_MAP[category] ?? CATEGORY_MAP.Low;
  const pct = Math.min(100, Math.max(0, Math.round(score)));

  // Sort history by date (oldest to newest)
  const chartData = [...history]
    .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
    .map(h => ({
      score: h.risk_score,
      time: new Date(h.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }));

  return (
    <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs flex flex-col justify-between h-full">
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Overall Risk Assessment</span>
            <h3 className="text-lg font-bold text-slate-900 mt-0.5">Composite Disease Index</h3>
          </div>
          <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${style.badge}`}>
            {style.label}
          </span>
        </div>

        <div className="flex items-center gap-6 my-4">
          <div className="flex flex-col">
            <div className="flex items-baseline gap-1">
              <span className="text-3xl font-extrabold text-slate-900">{pct}</span>
              <span className="text-xs font-semibold text-slate-400">/ 100</span>
            </div>
            <span className="text-[11px] text-slate-500 font-medium">Risk Score Points</span>
          </div>

          <div className="flex-1">
            <div className="flex justify-between items-center text-xs mb-1.5 font-medium text-slate-600">
              <span>Risk Intensity</span>
              <span className={`font-semibold ${style.text}`}>{pct}% Intensity</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
              <div className={`h-2 rounded-full ${style.bar} transition-all duration-700`} style={{ width: `${pct}%` }} />
            </div>
          </div>
        </div>

        {topFactors && topFactors.length > 0 && (
          <div className="mt-4 pt-4 border-t border-slate-100">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">Key Biomarker Influencers</span>
            <div className="flex flex-wrap gap-1.5">
              {topFactors.map((f) => (
                <span key={f} className="text-xs font-medium px-2.5 py-1 bg-slate-50 text-slate-700 rounded-lg border border-slate-200/80">
                  {f.replace(/_/g, " ")}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {chartData.length > 1 && (
        <div className="mt-6 pt-4 border-t border-slate-100">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">30-Day Risk Trajectory</span>
          <div className="h-20 w-full">
            <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="colorRisk" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={style.chart} stopOpacity={0.25}/>
                    <stop offset="95%" stopColor={style.chart} stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <Tooltip 
                  contentStyle={{ borderRadius: '8px', border: '1px solid #E2E8F0', boxShadow: '0 4px 12px rgba(0,0,0,0.05)', fontSize: '11px' }}
                  labelStyle={{ display: 'none' }}
                />
                <Area 
                  type="monotone" 
                  dataKey="score" 
                  stroke={style.chart} 
                  strokeWidth={2}
                  fillOpacity={1} 
                  fill="url(#colorRisk)" 
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
