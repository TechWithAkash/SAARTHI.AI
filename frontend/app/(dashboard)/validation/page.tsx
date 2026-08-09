"use client";

// Independent validation study — trained and benchmarked separately from the
// live risk engine, on a different dataset (NHANES) against a published
// clinical score (IDRS), as a methodology sanity-check. This page is a
// static report of that result, not a live model: it renders fixed numbers
// from the actual training run, and does not call the backend or affect the
// live risk score shown elsewhere in the app.

const RESULTS = [
  {
    condition: "Hypertension",
    auc: 0.7885,
    n_train: 3328,
    n_test: 1110,
    prevalence: 0.3546,
    features: ["age", "gender", "bmi", "waist", "hba1c", "whr", "sleep_hours", "sugar_intake_g", "PAD680"],
    citation: "Development of a hypertension risk prediction model, NHANES + Stacking (Frontiers in Cardiovascular Medicine)",
    note: "Systolic/diastolic BP were deliberately excluded — the hypertension label is partly built from them, so including them would leak the outcome into the input.",
    clean: true,
  },
  {
    condition: "Cardiovascular Disease",
    auc: 0.7727,
    n_train: 3243,
    n_test: 1081,
    prevalence: 0.1088,
    features: ["age", "gender", "bmi", "waist", "hba1c", "systolic_bp", "diastolic_bp", "whr", "sleep_hours", "sugar_intake_g", "PAD680"],
    citation: "No pre-vetted NHANES+ML paper for this exact setup — grounded in the same Framingham/INTERHEART risk factors as the live ICMR rule-based scorer.",
    note: null,
    clean: true,
  },
  {
    condition: "Diabetes",
    auc: 0.9279,
    n_train: 3243,
    n_test: 1081,
    prevalence: 0.1511,
    features: ["age", "gender", "bmi", "waist", "hba1c", "systolic_bp", "diastolic_bp", "whr", "sleep_hours", "sugar_intake_g", "PAD680"],
    citation: "Machine Learning-Based Prediction Model for Type 2 Diabetes Mellitus (Archives of Medical Science, NHANES-based)",
    note: "Includes HbA1c as an input feature. HbA1c ≥ 6.5% is also the clinical threshold NHANES uses to define the diabetes label itself — this measures whether the model can recover a diagnostic threshold, not independent predictive power. Reported here in full rather than omitted; treat this AUC as an upper bound / leakage check, not a benchmark win.",
    clean: false,
  },
];

const IDRS_AUC = 0.749;

export default function ValidationPage() {
  return (
    <div className="p-6 md:p-8 max-w-5xl mx-auto space-y-8 bg-slate-50/60 min-h-screen pb-24">
      <div>
        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">Research &amp; Methodology</span>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">Independent Model Validation</h1>
        <p className="text-sm text-slate-500 font-medium mt-1.5 max-w-2xl leading-relaxed">
          Separately from the live risk engine (which uses a 12-feature ICMR-derived pipeline validated for
          SHAP explainability and causal inference), we trained and benchmarked simple XGBoost classifiers
          on 8,187 real NHANES survey records, then compared them against IDRS — a published, clinically
          validated diabetes risk score — as a sanity check on our overall modeling approach.
        </p>
      </div>

      {/* IDRS comparison */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-3">Clinical Benchmark Comparison</span>
        <div className="flex flex-col sm:flex-row items-stretch gap-4">
          <div className="flex-1 rounded-xl border border-slate-200 bg-slate-50/60 p-4">
            <p className="text-xs font-semibold text-slate-500">IDRS (published clinical score)</p>
            <p className="text-3xl font-black text-slate-700 mt-1">{IDRS_AUC.toFixed(3)} <span className="text-sm font-semibold text-slate-400">AUC</span></p>
          </div>
          <div className="flex-1 rounded-xl border border-blue-200 bg-blue-50/60 p-4">
            <p className="text-xs font-semibold text-blue-700">Our NHANES-trained diabetes model</p>
            <p className="text-3xl font-black text-blue-700 mt-1">{RESULTS[2].auc.toFixed(3)} <span className="text-sm font-semibold text-blue-400">AUC</span></p>
          </div>
        </div>
        <p className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3.5 py-2.5 mt-4 leading-relaxed">
          <strong>Read this gap carefully, not triumphantly:</strong> a +0.18 AUC jump over a validated clinical
          instrument is a leakage flag, not a clean win — see the HbA1c note below. The hypertension (0.789) and
          CVD (0.773) results don&apos;t have this issue and are the ones we&apos;d stand behind as genuine.
        </p>
      </div>

      {/* Per-condition results */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {RESULTS.map((r) => (
          <div key={r.condition} className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs flex flex-col h-full">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">{r.condition}</span>
              <span className={`text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full border ${
                r.clean ? "text-emerald-700 bg-emerald-50 border-emerald-200" : "text-amber-700 bg-amber-50 border-amber-200"
              }`}>
                {r.clean ? "Clean" : "Caveat"}
              </span>
            </div>
            <p className="text-3xl font-black text-slate-900">{r.auc.toFixed(3)} <span className="text-sm font-semibold text-slate-400">AUC</span></p>
            <p className="text-xs text-slate-500 mt-1">{r.n_train.toLocaleString()} train · {r.n_test.toLocaleString()} test · {(r.prevalence * 100).toFixed(1)}% prevalence</p>

            <div className="mt-4 pt-4 border-t border-slate-100">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">Features Used</span>
              <div className="flex flex-wrap gap-1.5">
                {r.features.map((f) => (
                  <span key={f} className="text-[10px] font-medium text-slate-600 bg-slate-50 border border-slate-200 rounded-md px-1.5 py-0.5">{f}</span>
                ))}
              </div>
            </div>

            {r.note && (
              <p className={`text-[11px] leading-relaxed mt-4 rounded-lg px-3 py-2.5 border ${
                r.clean ? "text-slate-600 bg-slate-50 border-slate-200" : "text-amber-800 bg-amber-50 border-amber-200"
              }`}>
                {r.note}
              </p>
            )}

            <p className="text-[10px] text-slate-400 mt-4 leading-relaxed italic">{r.citation}</p>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">What This Page Is — And Isn&apos;t</span>
        <p className="text-xs text-slate-600 leading-relaxed">
          This is a validation study, not the production model. The risk score, SHAP breakdown, causal chain,
          and simulations shown elsewhere in this app are all computed by a different pipeline — a Transformer
          + 3-XGBoost-specialist ensemble trained on 12 ICMR-derived features, wired to real Garmin data. This
          page exists to show that our general modeling approach holds up against an independent dataset and a
          published clinical instrument, reported honestly including where a result needs a caveat.
        </p>
      </div>
    </div>
  );
}
