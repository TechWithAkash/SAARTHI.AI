"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface Props {
  scenarios: { current: number[]; improved: number[]; optimal: number[] };
  timelineDays: number[];
  projectedReduction: { improved: number; optimal: number };
}

export default function SimulationChart({ scenarios, timelineDays, projectedReduction }: Props) {
  const data = timelineDays.map((day, i) => ({
    day: `Day ${day}`,
    Current: Math.round(scenarios.current[i] ?? 0),
    Improved: Math.round(scenarios.improved[i] ?? 0),
    Optimal: Math.round(scenarios.optimal[i] ?? 0),
  }));

  return (
    <div className="w-full">
      <div className="flex items-start justify-between mb-6">
        <div>
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Risk Simulation</p>
          <p className="text-sm text-gray-500 mt-0.5">Projected trajectories over 120 days</p>
        </div>
        <div className="flex gap-3">
          <div className="text-right">
            <p className="text-xs text-gray-400">Improved path</p>
            <p className="text-sm font-semibold text-[#22C55E]">−{projectedReduction.improved.toFixed(1)}%</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-gray-400">Optimal path</p>
            <p className="text-sm font-semibold text-[#16A34A]">−{projectedReduction.optimal.toFixed(1)}%</p>
          </div>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={350} minWidth={0} minHeight={0}>
        <LineChart data={data} margin={{ top: 20, right: 8, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
          <XAxis dataKey="day" tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} domain={[0, 100]} />
          <Tooltip
            contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 4px 20px rgba(0,0,0,0.08)", fontSize: 12 }}
          />
          <Legend
            wrapperStyle={{ fontSize: 12, paddingTop: 16 }}
            formatter={(v) => <span style={{ color: "#6B7280" }}>{v}</span>}
          />
          <Line type="monotone" dataKey="Current" stroke="#D1D5DB" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="Improved" stroke="#86EFAC" strokeWidth={2.5} dot={false} />
          <Line type="monotone" dataKey="Optimal" stroke="#22C55E" strokeWidth={2.5} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
