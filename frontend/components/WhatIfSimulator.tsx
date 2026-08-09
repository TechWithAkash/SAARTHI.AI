"use client";

import { useEffect, useRef, useState } from "react";
import { api, type WhatIfResponse, type WhatIfOverrides } from "@/lib/api";

interface SliderDef {
  key: keyof WhatIfOverrides;
  label: string;
  min: number;
  max: number;
  step: number;
  unit: string;
  format?: (v: number) => string;
}

const SLIDERS: SliderDef[] = [
  { key: "steps", label: "Daily Steps", min: 0, max: 30000, step: 500, unit: "steps", format: (v) => v.toLocaleString() },
  { key: "sleep", label: "Sleep Duration", min: 0, max: 12, step: 0.5, unit: "hrs" },
  { key: "stress_level", label: "Stress Level", min: 1, max: 10, step: 1, unit: "/10" },
  { key: "diet_score", label: "Diet Quality", min: 1, max: 10, step: 1, unit: "/10" },
  { key: "heart_rate", label: "Heart Rate", min: 40, max: 140, step: 1, unit: "bpm" },
  { key: "bmi", label: "Body Mass Index", min: 15, max: 40, step: 0.1, unit: "" },
];

const DEBOUNCE_MS = 400;

interface WhatIfSimulatorProps {
  userId: string;
  // Lets the parent page draw the projected value on the trajectory chart
  // above, so moving a slider visibly connects to the graph instead of only
  // updating the result cards in this card. Fires the real result, or null
  // when there's nothing valid to plot (reset, not dirty, or a failed query).
  onResult?: (result: WhatIfResponse | null) => void;
}

export default function WhatIfSimulator({ userId, onResult }: WhatIfSimulatorProps) {
  const [values, setValues] = useState<Record<string, number> | null>(null);
  const [baseline, setBaseline] = useState<Record<string, number> | null>(null);
  const [result, setResult] = useState<WhatIfResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [initError, setInitError] = useState<string | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Seed sliders from the user's real latest reading — not arbitrary
  // defaults, so "current" position on every slider actually IS current.
  useEffect(() => {
    if (!userId) return;
    api.getLatestHealth(userId)
      .then((h) => {
        const seed = {
          steps: h.steps ?? 8000,
          sleep: h.sleep ?? 7,
          stress_level: h.stress_level ?? 4,
          diet_score: h.diet_score ?? 6,
          heart_rate: h.heart_rate ?? 72,
          bmi: h.bmi ?? 23.5,
        };
        setValues(seed);
        setBaseline(seed);
      })
      .catch(() => setInitError("Submit a check-in from the Dashboard first to use the simulator."));
  }, [userId]);

  function updateValue(key: string, v: number) {
    setValues((prev) => (prev ? { ...prev, [key]: v } : prev));
  }

  // Debounced live query — fires ~5ms of real ensemble time server-side, but
  // debounced anyway so a slider drag doesn't fire a request per pixel.
  useEffect(() => {
    if (!values || !userId) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(() => {
      setLoading(true);
      setQueryError(null);
      api.postWhatIf(userId, values as WhatIfOverrides)
        .then((r) => { setResult(r); onResult?.(r); })
        // This used to swallow every failure silently — moving a slider
        // during a backend hiccup produced no spinner, no result, no
        // message, just blank space. Now it says so.
        .catch(() => { setQueryError("Couldn't calculate the projection — the backend may be busy. Try again in a moment."); onResult?.(null); })
        .finally(() => setLoading(false));
    }, DEBOUNCE_MS);

    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [values, userId]);

  function handleReset() {
    if (baseline) setValues({ ...baseline });
    setResult(null);
    onResult?.(null);
  }

  const isDirty = values && baseline && SLIDERS.some((s) => values[s.key] !== baseline[s.key]);

  if (initError) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs text-center">
        <p className="text-sm text-slate-500">{initError}</p>
      </div>
    );
  }

  if (!values) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
        <div className="h-40 flex items-center justify-center">
          <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-0.5">
            Interactive Predictor
          </span>
          <h2 className="text-base font-bold text-slate-900">What If I Changed This?</h2>
          <p className="text-xs text-slate-500 mt-1 max-w-lg">
            Move a slider to see the projected effect of sustaining that change for 30 days —
            scored by the same model as your live risk score.
          </p>
        </div>
        {isDirty && (
          <button
            onClick={handleReset}
            className="shrink-0 text-xs font-semibold text-slate-500 hover:text-slate-900 px-3 py-1.5 rounded-lg hover:bg-slate-100 transition-colors"
          >
            Reset
          </button>
        )}
      </div>

      {/* Sliders */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-5">
        {SLIDERS.map((s) => {
          const v = values[s.key];
          const changed = baseline && v !== baseline[s.key];
          return (
            <div key={s.key}>
              <div className="flex items-baseline justify-between mb-1.5">
                <span className="text-xs font-semibold text-slate-700">{s.label}</span>
                <span className={`text-xs font-bold ${changed ? "text-blue-600" : "text-slate-400"}`}>
                  {s.format ? s.format(v) : v}{s.unit && ` ${s.unit}`}
                </span>
              </div>
              <input
                type="range"
                min={s.min}
                max={s.max}
                step={s.step}
                value={v}
                onChange={(e) => updateValue(s.key, Number(e.target.value))}
                className="w-full h-1.5 rounded-full bg-slate-100 accent-blue-600 cursor-pointer"
              />
            </div>
          );
        })}
      </div>

      {/* Result */}
      <div className="pt-5 border-t border-slate-100">
        {!isDirty ? (
          <p className="text-xs text-slate-400 text-center py-4">
            Move a slider above to see the projected change.
          </p>
        ) : loading && !result ? (
          <div className="flex items-center justify-center py-6 gap-2 text-slate-400">
            <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
            <span className="text-xs font-medium">Calculating…</span>
          </div>
        ) : queryError ? (
          <div className="flex items-start gap-2 bg-rose-50 border border-rose-200 rounded-xl px-3.5 py-2.5">
            <svg className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
            </svg>
            <p className="text-xs text-rose-800 leading-relaxed">{queryError}</p>
          </div>
        ) : result ? (
          <div className="space-y-4">
            {result.model_saturated && (
              <div className="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-xl px-3.5 py-2.5">
                <svg className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
                </svg>
                <p className="text-xs text-amber-800 leading-relaxed">
                  This combination pushed the model outside its normal range — treat these
                  numbers as indicative, not precise.
                </p>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <ResultStat label="Composite Risk" baseline={result.baseline.composite_risk} projected={result.counterfactual.composite_risk} big />
              <ResultStat label="Diabetes" baseline={result.baseline.diabetes_risk} projected={result.counterfactual.diabetes_risk} />
              <ResultStat label="Cardiovascular" baseline={result.baseline.cvd_risk} projected={result.counterfactual.cvd_risk} />
              <ResultStat label="Hypertension" baseline={result.baseline.hypertension_risk} projected={result.counterfactual.hypertension_risk} />
            </div>

            <p className="text-[10px] text-slate-400 text-center leading-relaxed pt-1">{result.note}</p>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function ResultStat({ label, baseline, projected, big = false }: { label: string; baseline: number; projected: number; big?: boolean }) {
  const delta = Math.round((projected - baseline) * 10) / 10;
  const improved = delta < -0.1;
  const worsened = delta > 0.1;
  const color = improved ? "text-emerald-600" : worsened ? "text-rose-600" : "text-slate-400";
  const bg = improved ? "bg-emerald-50 border-emerald-200" : worsened ? "bg-rose-50 border-rose-200" : "bg-slate-50 border-slate-200";

  return (
    <div className={`rounded-xl border p-4 ${big ? "sm:col-span-2" : ""} ${bg}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-600">{label}</span>
        <span className={`text-xs font-bold ${color}`}>
          {delta === 0 ? "no change" : `${delta > 0 ? "+" : ""}${delta.toFixed(1)} pts`}
        </span>
      </div>
      <div className="flex items-baseline gap-2 mt-1.5">
        <span className={`font-black ${big ? "text-2xl" : "text-lg"} text-slate-900`}>
          {projected.toFixed(1)}
        </span>
        <span className="text-xs text-slate-400 line-through">{baseline.toFixed(1)}</span>
      </div>
    </div>
  );
}
