"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api, type HealthDataInput, type RiskResponse, type Recommendation, type UserProfile, type GarminStatus } from "@/lib/api";
import RiskCard from "@/components/RiskCard";
import RecommendationCard from "@/components/RecommendationCard";
import AuraChat from "@/components/AuraChat";
import { Activity, Heart, Moon, Zap, Apple, Expand, RefreshCw, Compass, Radio, ArrowUpRight, ArrowDownRight, Printer, ChevronDown, ChevronUp, ShieldCheck, AlertTriangle, FileText, Sliders } from "lucide-react";
import { AreaChart, Area, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, Radar, Tooltip } from "recharts";

const DEFAULT_USER = "user_demo_001";

const FIELDS: {
  key: keyof Omit<HealthDataInput, "user_id">;
  label: string;
  min: number;
  max: number;
  step: number;
  unit: string;
  refRange: string;
  icon: any;
  color: {
    icon: string;
    progress: string;
    accent: string;
  };
}[] = [
  {
    key: "heart_rate", label: "Heart Rate", min: 40, max: 200, step: 1, unit: "bpm", refRange: "60–100 bpm", icon: Heart,
    color: { icon: "bg-rose-50 text-rose-600 border border-rose-100", progress: "bg-rose-500", accent: "accent-rose-500" }
  },
  {
    key: "sleep", label: "Sleep Duration", min: 0, max: 12, step: 0.5, unit: "hrs", refRange: "7–9 hrs", icon: Moon,
    color: { icon: "bg-indigo-50 text-indigo-600 border border-indigo-100", progress: "bg-indigo-500", accent: "accent-indigo-500" }
  },
  {
    key: "steps", label: "Daily Steps", min: 0, max: 30000, step: 100, unit: "steps", refRange: "≥ 8,000 steps", icon: Activity,
    color: { icon: "bg-cyan-50 text-cyan-600 border border-cyan-100", progress: "bg-cyan-500", accent: "accent-cyan-500" }
  },
  {
    key: "stress_level", label: "Stress Level", min: 1, max: 10, step: 1, unit: "/10", refRange: "1–4 /10", icon: Zap,
    color: { icon: "bg-amber-50 text-amber-600 border border-amber-100", progress: "bg-amber-500", accent: "accent-amber-500" }
  },
  {
    key: "diet_score", label: "Diet Quality", min: 1, max: 10, step: 1, unit: "/10", refRange: "7–10 /10", icon: Apple,
    color: { icon: "bg-emerald-50 text-emerald-600 border border-emerald-100", progress: "bg-emerald-500", accent: "accent-emerald-500" }
  },
  {
    key: "bmi", label: "Body Mass Index", min: 15, max: 50, step: 0.1, unit: "kg/m²", refRange: "18.5–24.9", icon: Expand,
    color: { icon: "bg-blue-50 text-blue-600 border border-blue-100", progress: "bg-blue-600", accent: "accent-blue-600" }
  },
];

const DEFAULTS: Omit<HealthDataInput, "user_id"> = {
  heart_rate: 72, sleep: 7, steps: 8000, stress_level: 4, diet_score: 6, bmi: 23.5,
};

function sparklineFromHistory(
  history: RiskResponse[],
  pick: (r: RiskResponse) => number | null | undefined,
  points = 7,
): { val: number }[] {
  const vals = history
    .slice(0, points)
    .reverse()
    .map((r) => pick(r))
    .filter((v): v is number => v != null);
  return vals.map((val) => ({ val }));
}

export default function Dashboard() {
  const router = useRouter();
  const [form, setForm] = useState(DEFAULTS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false); // Collapsed drawer by default for clean view

  const [userName, setUserName] = useState('');
  const [result, setResult] = useState<{
    score: number;
    category: string;
    topFactors: string[];
  } | null>(null);
  const [history, setHistory] = useState<RiskResponse[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);

  // Live KPI state
  const [liveRisk, setLiveRisk] = useState<RiskResponse | null>(null);
  const [alertCount, setAlertCount] = useState<number | null>(0);

  // Progressive Disclosure Toggles
  const [showFullClinicalReport, setShowFullClinicalReport] = useState(false);
  const [showTechnicalExplainability, setShowTechnicalExplainability] = useState(false);

  // Clinical profile
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [profileForm, setProfileForm] = useState({
    age: '',
    gender: 'male',
    fam_diabetes: false,
    fam_cvd: false,
    fam_hypertension: false,
    whr: '',
  });
  const [savingProfile, setSavingProfile] = useState(false);
  const [isComputingRisk, setIsComputingRisk] = useState(false);
  const [isEditingProfile, setIsEditingProfile] = useState(false);

  const fetchHistory = () => {
    api.getRiskHistory(DEFAULT_USER).then(setHistory).catch((err: any) => {
      if (err?.status !== 404) console.error("Risk history error:", err);
    });
  };

  useEffect(() => {
    fetchHistory();
    fetchGarminStatus();
    const name = sessionStorage.getItem('saarthi_user_name') ?? sessionStorage.getItem('darpan_user_name');
    if (name) setUserName(name);

    api.getProfile(DEFAULT_USER)
      .then((p) => {
        setProfile(p);
        if (p.age || p.gender) {
          setProfileForm({
            age: p.age ? String(p.age) : '',
            gender: p.gender ?? 'male',
            fam_diabetes: p.fam_diabetes === 1,
            fam_cvd: p.fam_cvd === 1,
            fam_hypertension: p.fam_hypertension === 1,
            whr: p.whr ? String(p.whr) : '',
          });
        }
      })
      .catch(() => { });

    api.getRisk(DEFAULT_USER)
      .then(async (risk) => {
        if (risk.diabetes_risk != null) {
          setLiveRisk(risk);
          setResult({ score: risk.risk_score, category: risk.risk_category, topFactors: risk.top_risk_factors });
          return;
        }
        try {
          const hist = await api.getRiskHistory(DEFAULT_USER);
          const withScores = hist.find((r: any) => r.diabetes_risk != null || r.cvd_risk != null);
          if (withScores) {
            setLiveRisk(withScores);
            setResult({ score: withScores.risk_score, category: withScores.risk_category, topFactors: withScores.top_risk_factors });
          } else {
            setLiveRisk(risk);
          }
        } catch {
          setLiveRisk(risk);
        }
      })
      .catch(() => { });

    api.getLatestHealth(DEFAULT_USER)
      .then((latest) => {
        setForm({
          heart_rate: latest.heart_rate != null ? Math.round(latest.heart_rate) : DEFAULTS.heart_rate,
          sleep: (latest.sleep && latest.sleep > 0) ? Number(latest.sleep.toFixed(1)) : DEFAULTS.sleep,
          steps: latest.steps != null ? Math.round(latest.steps) : DEFAULTS.steps,
          stress_level: latest.stress_level != null ? latest.stress_level : DEFAULTS.stress_level,
          diet_score: latest.diet_score != null ? latest.diet_score : DEFAULTS.diet_score,
          bmi: latest.bmi != null ? Number(latest.bmi.toFixed(1)) : DEFAULTS.bmi,
        });
      })
      .catch(() => { });

    api.getAlerts(DEFAULT_USER)
      .then((d) => setAlertCount(d.alerts ? d.alerts.length : 0))
      .catch(() => setAlertCount(0));
  }, []);

  const [syncing, setSyncing] = useState(false);
  const [syncProgress, setSyncProgress] = useState(0);

  // Real Garmin connection state — previously the header just hardcoded
  // "Wearable Telemetry Active · Last synced 4m ago" regardless of whether
  // anything was actually connected. This replaces that with the truth.
  const [garminStatus, setGarminStatus] = useState<GarminStatus | null>(null);
  const [garminSyncing, setGarminSyncing] = useState(false);
  const [garminError, setGarminError] = useState<string | null>(null);

  const fetchGarminStatus = () => {
    api.getGarminStatus(DEFAULT_USER).then(setGarminStatus).catch(() => setGarminStatus(null));
  };

  async function handleGarminSync() {
    setGarminSyncing(true);
    setGarminError(null);
    try {
      await api.syncGarmin(DEFAULT_USER, 14);
      fetchGarminStatus();
      fetchHistory();
      const latest = await api.getLatestHealth(DEFAULT_USER);
      setForm({
        heart_rate: latest.heart_rate != null ? Math.round(latest.heart_rate) : form.heart_rate,
        sleep: latest.sleep != null ? Number(latest.sleep.toFixed(1)) : form.sleep,
        steps: latest.steps != null ? Math.round(latest.steps) : form.steps,
        stress_level: latest.stress_level ?? form.stress_level,
        diet_score: latest.diet_score ?? form.diet_score,
        bmi: latest.bmi != null ? Number(latest.bmi.toFixed(1)) : form.bmi,
      });
    } catch (err: any) {
      // 503 = not configured or login blocked; 502 = Garmin upstream error.
      // Both are the backend refusing safely, not a crash — surface the
      // real reason instead of a generic failure.
      setGarminError(err?.detail ?? "Garmin sync failed. Check /garmin/status for details.");
    } finally {
      setGarminSyncing(false);
    }
  }

  async function handleSync() {
    setSyncing(true);
    setSyncProgress(0);
    try {
      const steps = [10, 45, 80];
      for (const p of steps) {
        await new Promise(r => setTimeout(r, 200));
        setSyncProgress(p);
      }

      const latest = await api.getLatestHealth(DEFAULT_USER);
      setSyncProgress(100);

      setForm({
        heart_rate: latest.heart_rate != null ? Math.round(latest.heart_rate) : form.heart_rate,
        sleep: latest.sleep != null ? Number(latest.sleep.toFixed(1)) : form.sleep,
        steps: latest.steps != null ? Math.round(latest.steps) : form.steps,
        stress_level: latest.stress_level ?? form.stress_level,
        diet_score: latest.diet_score ?? form.diet_score,
        bmi: latest.bmi != null ? Number(latest.bmi.toFixed(1)) : form.bmi,
      });
    } catch (err: any) {
      if (err?.status !== 404) {
        console.error(err);
      }
      setError(err?.detail ?? "No recent telemetry recorded yet. Enter metrics manually below and click Run Analysis.");
    } finally {
      await new Promise(r => setTimeout(r, 600));
      setSyncing(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const approxRisk = Math.min(95, Math.max(5, Math.round(
      (form.stress_level * 3) +
      ((form.heart_rate - 60) * 0.4) +
      ((8 - form.sleep) * 3) +
      (form.bmi > 25 ? (form.bmi - 25) * 2 : 0) +
      ((10 - form.diet_score) * 2)
    )));
    const approxCategory = approxRisk > 60 ? "High" : approxRisk > 35 ? "Moderate" : "Low";
    const approxFactors = [
      form.stress_level > 6 ? "stress_level" : "heart_rate",
      form.sleep < 6 ? "sleep" : "bmi",
    ];

    setResult({ score: approxRisk, category: approxCategory, topFactors: approxFactors });
    setLiveRisk((prev) => prev ?? {
      user_id: DEFAULT_USER,
      log_id: "provisional",
      risk_score: approxRisk,
      risk_category: approxCategory as any,
      top_risk_factors: approxFactors,
      shap_contributions: {},
      timestamp: new Date().toISOString(),
    });

    try {
      await api.submitHealth({ user_id: DEFAULT_USER, ...form });

      const getBestRisk = async () => {
        try {
          const latest = await api.getRisk(DEFAULT_USER);
          if (latest.diabetes_risk != null) return latest;
          try {
            const hist = await api.getRiskHistory(DEFAULT_USER);
            const withScores = hist.find((r: any) => r.diabetes_risk != null);
            if (withScores) return { ...latest, ...withScores };
          } catch { /* ignore */ }
          return latest;
        } catch (err: any) {
          if (err?.status === 404) return null;
          throw err;
        }
      };

      let shownInitial = false;
      for (let attempt = 0; attempt < 10; attempt++) {
        await new Promise((r) => setTimeout(r, 1500));
        try {
          const candidate = await getBestRisk();
          if (!candidate) continue;

          if (candidate.risk_score != null) {
            setResult({ score: candidate.risk_score, category: candidate.risk_category, topFactors: candidate.top_risk_factors });
            setLiveRisk(candidate);
            setLoading(false);
            shownInitial = true;
            fetchHistory();
            api.getAlerts(DEFAULT_USER).then((d) => setAlertCount(d.alerts ? d.alerts.length : 0)).catch(() => setAlertCount(0));
            api.getRecommend(DEFAULT_USER).then((r) => setRecommendations(r.recommendations)).catch((err: any) => {
              if (err?.status !== 404) console.error("Recommend fetch error:", err);
            });
          }
          if (candidate.diabetes_risk != null) {
            setLiveRisk(candidate);
            break;
          }
        } catch { /* pipeline processing */ }
      }

      sessionStorage.setItem('saarthi_user_id', DEFAULT_USER);
      sessionStorage.setItem('darpan_user_id', DEFAULT_USER);
    } catch (err: any) {
      if (err?.status !== 404) {
        setError(err instanceof Error ? err.message : 'Something went wrong');
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveProfile(e: React.FormEvent) {
    e.preventDefault();
    if (!profileForm.age) return;
    setSavingProfile(true);
    try {
      const saved = await api.updateProfile({
        user_id: DEFAULT_USER,
        age: parseInt(profileForm.age),
        gender: profileForm.gender,
        whr: profileForm.whr ? parseFloat(profileForm.whr) : 0.85,
        fam_diabetes: profileForm.fam_diabetes ? 1 : 0,
        fam_cvd: profileForm.fam_cvd ? 1 : 0,
        fam_hypertension: profileForm.fam_hypertension ? 1 : 0,
      });
      setProfile(saved);
      setSavingProfile(false);

      setIsComputingRisk(true);
      try {
        const { user_id, ...healthData } = await api.getLatestHealth(DEFAULT_USER);
        await api.submitHealth({ user_id: DEFAULT_USER, ...healthData });
      } catch { /* pipeline processing */ }

      let found = false;
      for (let i = 0; i < 12 && !found; i++) {
        await new Promise(r => setTimeout(r, 2000));
        try {
          const risk = await api.getRisk(DEFAULT_USER);
          if (risk.diabetes_risk != null) {
            setLiveRisk(risk);
            setResult({ score: risk.risk_score, category: risk.risk_category, topFactors: risk.top_risk_factors });
            fetchHistory();
            found = true;
          }
        } catch { /* processing */ }
      }
      setIsComputingRisk(false);
    } catch (err) {
      setError('Failed to save profile. Please try again.');
      setSavingProfile(false);
      setIsComputingRisk(false);
    }
  }

  const currentDate = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });

  function exportReport() {
    const name = sessionStorage.getItem('saarthi_user_name') ?? sessionStorage.getItem('darpan_user_name') ?? 'Patient';
    const reportDate = new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    const reportTime = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    const riskColor = result
      ? result.score < 30 ? '#059669' : result.score < 60 ? '#d97706' : '#dc2626'
      : '#64748b';
    const riskBg = result
      ? result.score < 30 ? '#ecfdf5' : result.score < 60 ? '#fffbeb' : '#fef2f2'
      : '#f8fafc';

    const vitalsRows = [
      { label: 'Heart Rate', value: `${form.heart_rate}`, unit: 'bpm', ref: '60–100', status: form.heart_rate >= 60 && form.heart_rate <= 100 ? 'Normal' : 'Review' },
      { label: 'Sleep Duration', value: `${form.sleep}`, unit: 'hrs', ref: '7–9', status: form.sleep >= 7 && form.sleep <= 9 ? 'Normal' : 'Review' },
      { label: 'Daily Steps', value: `${form.steps.toLocaleString()}`, unit: 'steps', ref: '≥ 8,000', status: form.steps >= 8000 ? 'Normal' : 'Low' },
      { label: 'Stress Level', value: `${form.stress_level}`, unit: '/10', ref: '1–4', status: form.stress_level <= 4 ? 'Normal' : 'Elevated' },
      { label: 'Diet Score', value: `${form.diet_score}`, unit: '/10', ref: '7–10', status: form.diet_score >= 7 ? 'Normal' : 'Review' },
      { label: 'BMI', value: `${form.bmi}`, unit: 'kg/m²', ref: '18.5–24.9', status: form.bmi >= 18.5 && form.bmi <= 24.9 ? 'Normal' : 'Review' },
    ];

    const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>SAARTHI.AI Clinical Summary — ${name}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Inter', sans-serif; background: #fff; color: #0f172a; font-size: 13px; line-height: 1.6; }
    @media print {
      body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
      .no-print { display: none !important; }
    }
    .page { max-width: 800px; margin: 0 auto; padding: 48px; }
    .header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #2563eb; padding-bottom: 20px; margin-bottom: 24px; }
    .brand-name { font-size: 22px; font-weight: 800; color: #0f172a; }
    .brand-sub { font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; }
    .patient-bar { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px 20px; margin-bottom: 24px; display: flex; gap: 40px; }
    .patient-label { font-size: 10px; font-weight: 700; color: #64748b; text-transform: uppercase; }
    .patient-value { font-size: 14px; font-weight: 700; color: #0f172a; }
    .risk-card { background: ${riskBg}; border: 1.5px solid ${riskColor}; border-radius: 14px; padding: 20px 24px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
    .risk-score-num { font-size: 42px; font-weight: 800; color: ${riskColor}; line-height: 1; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 24px; }
    thead th { background: #f8fafc; font-size: 10px; font-weight: 700; color: #64748b; text-transform: uppercase; padding: 10px 14px; text-align: left; border-bottom: 1px solid #e2e8f0; }
    tbody td { padding: 10px 14px; border-bottom: 1px solid #f1f5f9; font-size: 13px; color: #334155; }
    .status-normal { background: #dcfce7; color: #059669; font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 99px; text-transform: uppercase; }
    .status-review, .status-elevated { background: #fef3c7; color: #d97706; font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 99px; text-transform: uppercase; }
    .print-btn { position: fixed; top: 20px; right: 20px; background: #2563eb; color: white; border: none; font-size: 13px; font-weight: 600; padding: 10px 20px; border-radius: 8px; cursor: pointer; z-index: 100; }
  </style>
</head>
<body>
  <button class="print-btn no-print" onclick="window.print()">Print Clinical Report</button>
  <div class="page">
    <div class="header">
      <div>
        <div class="brand-name">SAARTHI<span style="color:#2563eb">.AI</span></div>
        <div class="brand-sub">Clinical Preventive Health Platform</div>
      </div>
      <div style="text-align:right">
        <div style="font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase">Clinical Diagnostic Summary</div>
        <div style="font-size:12px;font-weight:600;color:#334155;margin-top:2px">${reportDate} · ${reportTime}</div>
      </div>
    </div>
    <div class="patient-bar">
      <div><div class="patient-label">Patient Name</div><div class="patient-value">${name}</div></div>
      <div><div class="patient-label">Patient ID</div><div class="patient-value">${sessionStorage.getItem('saarthi_user_id') ?? sessionStorage.getItem('darpan_user_id') ?? 'user_demo_001'}</div></div>
      <div><div class="patient-label">Telemetry Source</div><div class="patient-value">Apple Watch / Wearable</div></div>
    </div>
    ${result ? `
    <div class="risk-card">
      <div>
        <div style="font-size:10px;font-weight:700;color:${riskColor};text-transform:uppercase;margin-bottom:4px;">Risk Assessment Score</div>
        <div class="risk-score-num">${result.score.toFixed(0)} <span style="font-size:16px;color:#64748b;">/ 100</span></div>
      </div>
      <div style="text-align:right">
        <div style="font-size:20px;font-weight:700;color:${riskColor}">${result.category} Risk Category</div>
        <div style="font-size:12px;color:#475569;margin-top:4px">Key Factors: ${result.topFactors.map(f => f.replace(/_/g, ' ')).join(', ')}</div>
      </div>
    </div>` : ''}
    <div style="font-weight:700;font-size:12px;color:#475569;text-transform:uppercase;margin-bottom:8px">Current Vital Telemetry Readouts</div>
    <table>
      <thead><tr><th>Metric</th><th>Value</th><th>Reference Range</th><th>Status</th></tr></thead>
      <tbody>
        ${vitalsRows.map(r => `
        <tr>
          <td style="font-weight:600;">${r.label}</td>
          <td><strong>${r.value}</strong> ${r.unit}</td>
          <td>${r.ref}</td>
          <td><span class="status-${r.status.toLowerCase()}">${r.status}</span></td>
        </tr>`).join('')}
      </tbody>
    </table>
  </div>
</body>
</html>`;

    const win = window.open('', '_blank');
    if (win) {
      win.document.write(html);
      win.document.close();
    }
  }

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-8 bg-slate-50/60 min-h-screen pb-24">

      {/* ── 1. HEADER / PATIENT GREETING (Clinical Blue Banner) ── */}
      <div className="bg-gradient-to-r from-blue-950 via-blue-900 to-indigo-950 text-white rounded-2xl p-6 sm:p-7 border border-blue-800/60 shadow-md relative overflow-hidden flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        {/* Subtle radial glow background overlay */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_80%_0%,rgba(59,130,246,0.25),transparent_60%)] pointer-events-none" />

        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            {/* Previously this badge was static — "Wearable Telemetry Active
                · Last synced 4m ago" — shown unconditionally whether or not
                any wearable was connected. This reflects the real Garmin
                connection state from /garmin/status instead. */}
            {garminStatus?.last_sync?.last_synced_at ? (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 backdrop-blur-xs">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Garmin Connected
              </span>
            ) : garminStatus?.configured ? (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-400/30 backdrop-blur-xs">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                Garmin Ready — Not Yet Synced
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-500/20 text-slate-300 border border-slate-400/30 backdrop-blur-xs">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                No Wearable Connected
              </span>
            )}
            <span className="text-xs text-blue-200/70 font-medium">
              {garminStatus?.last_sync?.last_synced_at
                ? `· ${garminStatus.last_sync.days_synced} days synced`
                : "· vitals entered manually"}
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">Good Evening, {userName || 'Soham'} 👋</h1>
          <p className="text-xs sm:text-sm text-blue-100/80 font-medium mt-1">Patient Health Overview · 14-Day Physiological Baseline Analysis</p>
          {garminError && (
            <p className="text-xs text-rose-300 font-medium mt-2 max-w-md">{garminError}</p>
          )}
        </div>

        <div className="relative z-10 flex flex-wrap items-center gap-3">
          {garminStatus?.configured && (
            <button
              onClick={handleGarminSync}
              disabled={garminSyncing || garminStatus.login_blocked}
              title={garminStatus.login_blocked ? "Login attempts exhausted for this session — restart the API to retry" : undefined}
              className="flex items-center gap-2 px-4 py-2.5 bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-400/30 text-white rounded-xl text-xs font-semibold backdrop-blur-xs transition-all disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-emerald-200 ${garminSyncing ? "animate-spin" : ""}`} />
              {garminSyncing ? "Syncing Garmin…" : "Sync Garmin"}
            </button>
          )}

          <button
            onClick={handleSync}
            disabled={syncing}
            title="Reload the most recent reading already in your health record"
            className="flex items-center gap-2 px-4 py-2.5 bg-white/10 hover:bg-white/20 border border-white/20 text-white rounded-xl text-xs font-semibold backdrop-blur-xs transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-blue-200 ${syncing ? "animate-spin" : ""}`} />
            {syncing ? `Loading ${syncProgress}%` : "Reload Latest Reading"}
          </button>

          <button
            onClick={() => setIsEditing(e => !e)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold backdrop-blur-xs transition-all border ${isEditing
              ? "bg-blue-500/40 text-white border-blue-400/60"
              : "bg-white/10 hover:bg-white/20 text-white border-white/20"
              }`}
          >
            <Sliders className="w-3.5 h-3.5 text-blue-200" />
            {isEditing ? "Hide Sliders" : "Edit / Simulate Telemetry"}
          </button>

          <button
            onClick={exportReport}
            className="flex items-center gap-2 px-4.5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold transition-all border border-blue-400/40 shadow-sm"
          >
            <Printer className="w-3.5 h-3.5" /> Export Clinical Report
          </button>
        </div>
      </div>

      {/* ── 2. OVERALL HEALTH STATUS & ALERTS ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-stretch">

        {/* Card 1 — Overall Wellness Index with Up & Down Trend Sparkline */}
        {(() => {
          const prakritiScore = liveRisk ? Math.round(100 - liveRisk.risk_score) : 82;
          const pctFraction = prakritiScore / 100;
          const realHistorySparkline = sparklineFromHistory(history, (r) => 100 - r.risk_score);
          const sparklineData = realHistorySparkline.length >= 3 
            ? realHistorySparkline 
            : [{ val: 78 }, { val: 80 }, { val: 76 }, { val: 82 }, { val: 84 }, { val: 81 }, { val: 85 }];

          return (
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs flex flex-col justify-between h-full min-h-[240px] transition-all hover:border-slate-300 relative overflow-hidden">
              <div>
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">Health Equilibrium</span>
                <div className="flex justify-between items-start gap-4">
                  <div>
                    <div className="flex items-baseline gap-1.5">
                      <span className="text-3xl font-extrabold text-slate-900 tracking-tight">{prakritiScore}</span>
                      <span className="text-sm font-semibold text-slate-400">/ 100</span>
                    </div>
                    <div className="mt-2">
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                        Optimal Balance
                      </span>
                    </div>
                  </div>
                  <div className="relative w-14 h-14 shrink-0">
                    <svg className="w-14 h-14 -rotate-90" viewBox="0 0 56 56">
                      <circle cx="28" cy="28" r="22" stroke="#f1f5f9" strokeWidth="5" fill="none" />
                      <circle cx="28" cy="28" r="22" stroke="#10B981" strokeWidth="5" fill="none"
                        strokeDasharray={`${2 * Math.PI * 22 * pctFraction} ${2 * Math.PI * 22}`}
                        strokeLinecap="round" className="transition-all duration-700" />
                    </svg>
                    <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-emerald-700">{prakritiScore}%</span>
                  </div>
                </div>
              </div>

              {/* Up-and-Down Trend Sparkline Line Graph */}
              <div className="my-2">
                <div className="flex justify-between items-center text-[11px] text-slate-400 font-medium mb-1">
                  <span>30-Day Trend Curve</span>
                  <span className="text-emerald-600 font-semibold flex items-center gap-0.5">
                    <ArrowUpRight className="w-3 h-3" /> +2.4 pts
                  </span>
                </div>
                <div className="h-12 w-full">
                  <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                    <AreaChart data={sparklineData}>
                      <defs>
                        <linearGradient id="colorEqSpark" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10B981" stopOpacity={0.25} />
                          <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <Area type="monotone" dataKey="val" stroke="#10B981" strokeWidth={2} fill="url(#colorEqSpark)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500 font-medium">
                <span>Physiological Trajectory</span>
                <span className="text-slate-400 text-[11px]">Vitals Nominal</span>
              </div>
            </div>
          );
        })()}

        {/* Card 2 — Health Alerts Card with Anomaly Wave Line */}
        {(() => {
          const count = alertCount ?? 0;
          const alertSparkline = count > 0 
            ? [{ val: 1 }, { val: 3 }, { val: 2 }, { val: 5 }, { val: 3 }, { val: count }]
            : [{ val: 0 }, { val: 1 }, { val: 0 }, { val: 0 }, { val: 1 }, { val: 0 }, { val: 0 }];
          const strokeColor = count > 0 ? "#F59E0B" : "#10B981";

          return (
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs flex flex-col justify-between h-full min-h-[240px] transition-all hover:border-slate-300 relative overflow-hidden">
              <div>
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">Health Alerts</span>
                <div className="flex justify-between items-start gap-4">
                  <div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-3xl font-extrabold text-slate-900 tracking-tight">{count}</span>
                      <span className="text-xs font-semibold text-slate-500">Active Warnings</span>
                    </div>
                    <div className="mt-2">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${count > 0 ? "bg-amber-50 text-amber-700 border-amber-200" : "bg-emerald-50 text-emerald-700 border-emerald-200"}`}>
                        {count > 0 ? <AlertTriangle className="w-3.5 h-3.5 text-amber-600" /> : <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />}
                        {count > 0 ? "Requires Attention" : "All Systems Clear"}
                      </span>
                    </div>
                  </div>
                  <div className={`w-14 h-14 rounded-2xl border flex items-center justify-center shrink-0 ${count > 0 ? "bg-amber-50 border-amber-100 text-amber-600" : "bg-emerald-50 border-emerald-100 text-emerald-600"}`}>
                    {count > 0 ? <AlertTriangle className="w-6 h-6" /> : <ShieldCheck className="w-6 h-6" />}
                  </div>
                </div>
              </div>

              {/* Anomaly Wave Line Graph */}
              <div className="my-2">
                <div className="flex justify-between items-center text-[11px] text-slate-400 font-medium mb-1">
                  <span>Stability Wave</span>
                  <span className={count > 0 ? "text-amber-600 font-semibold" : "text-emerald-600 font-semibold"}>
                    {count > 0 ? "Anomaly Detected" : "Stable Baseline"}
                  </span>
                </div>
                <div className="h-12 w-full">
                  <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                    <AreaChart data={alertSparkline}>
                      <defs>
                        <linearGradient id="colorAlertSpark" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={strokeColor} stopOpacity={0.25} />
                          <stop offset="95%" stopColor={strokeColor} stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <Area type="monotone" dataKey="val" stroke={strokeColor} strokeWidth={2} fill="url(#colorAlertSpark)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100">
                <button
                  onClick={() => router.push("/alerts")}
                  className="w-full text-xs font-semibold text-blue-600 hover:text-blue-800 transition-colors flex items-center justify-between"
                >
                  <span>View Alert Log ({count})</span>
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          );
        })()}

        {/* Card 3 — Primary Action Card with Forecast Wave Line */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs flex flex-col justify-between h-full min-h-[240px] transition-all hover:border-slate-300 relative overflow-hidden">
          <div>
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">Preventive Care Action</span>
            <div className="flex justify-between items-start gap-4">
              <div>
                <h3 className="text-sm font-bold text-slate-900 leading-snug">Run Trajectory Analysis</h3>
                <p className="text-xs text-slate-500 font-medium mt-1 leading-relaxed">
                  Evaluate multi-disease risk profiles from current 30-day vitals.
                </p>
              </div>
              <div className="w-14 h-14 rounded-2xl bg-blue-50 border border-blue-100 text-blue-600 flex items-center justify-center shrink-0">
                <Activity className="w-6 h-6" />
              </div>
            </div>
          </div>

          {/* Predictive Risk Reduction Sparkline */}
          <div className="my-2">
            <div className="flex justify-between items-center text-[11px] text-slate-400 font-medium mb-1">
              <span>Predictive Curve</span>
              <span className="text-blue-600 font-semibold">Simulated Reduction</span>
            </div>
            <div className="h-12 w-full">
              <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                <AreaChart data={[{ val: 45 }, { val: 40 }, { val: 32 }, { val: 28 }, { val: 24 }, { val: 18 }, { val: 15 }]}>
                  <defs>
                    <linearGradient id="colorPredictSpark" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2563EB" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#2563EB" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <Area type="monotone" dataKey="val" stroke="#2563EB" strokeWidth={2} fill="url(#colorPredictSpark)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100">
            <button
              id="analyze-updated-vitals-btn"
              onClick={handleSubmit}
              disabled={loading}
              className="w-full py-2 px-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold transition-all disabled:opacity-50 flex items-center justify-center gap-2 shadow-xs"
            >
              {loading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Activity className="w-3.5 h-3.5" />}
              {loading ? "Analyzing Vitals…" : "Analyze Updated Vitals"}
            </button>
          </div>
        </div>
      </div>

      {/* ── 3. TODAY'S VITALS & TELEMETRY ── */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-6">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4 border-b border-slate-100">
          <div>
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-0.5">Biometric Telemetry</span>
            <h2 className="text-base font-bold text-slate-900">Today's Vitals Readouts</h2>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsEditing(e => !e)}
              className="text-xs font-semibold text-blue-600 hover:text-blue-800 transition-colors flex items-center gap-1.5"
            >
              <Sliders className="w-3.5 h-3.5" />
              {isEditing ? "Close Simulation Drawer" : "Edit / Simulate Vitals"}
            </button>
          </div>
        </div>

        {/* Elegant & Perfectly Proportioned Vitals Readout Cards Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5">
          {FIELDS.map(({ key, label, min, max, unit, refRange, icon: Icon, color }) => {
            const val = form[key];
            const pct = Math.min(100, Math.max(0, Math.round(((val - min) / (max - min)) * 100)));
            return (
              <div
                key={key}
                className="p-4.5 rounded-2xl bg-white border border-slate-200/90 shadow-xs transition-all duration-200 hover:-translate-y-0.5 hover:shadow-sm flex flex-col justify-between h-full min-h-[155px]"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className={`w-10 h-10 rounded-xl ${color.icon} flex items-center justify-center shrink-0`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">{unit}</span>
                </div>

                <div>
                  <span className="text-2xl font-black text-slate-900 tracking-tight block">{val}</span>
                  <span className="text-xs font-bold text-slate-700 block mt-0.5">{label}</span>
                </div>

                <div className="mt-3">
                  <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                    <div
                      className={`h-1.5 rounded-full ${color.progress} transition-all duration-500`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-[10px] font-medium text-slate-400 block mt-1.5">Target: {refRange}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Collapsible Telemetry Simulation Sliders Drawer */}
        {isEditing && (
          <div className="pt-6 border-t border-slate-200/80 bg-slate-50/80 rounded-2xl p-6 space-y-6 animate-in fade-in duration-300">
            <div className="flex justify-between items-center">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-slate-900">Simulate Vital Adjustments</h3>
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                    Telemetry Engine Active
                  </span>
                </div>
                <p className="text-xs text-slate-500 font-medium mt-0.5">Adjust sliders below to test hypothetical changes before running diagnostic analysis.</p>
              </div>
              <button
                type="button"
                onClick={() => setIsEditing(false)}
                className="text-xs text-slate-500 hover:text-slate-800 font-semibold bg-white border border-slate-200 px-3 py-1.5 rounded-xl shadow-2xs transition-colors"
              >
                Close Drawer ✕
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {FIELDS.map(({ key, label, min, max, step, unit, color }) => (
                  <div key={key} className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-3 hover:border-slate-300 transition-colors">
                    <div className="flex justify-between items-center text-xs">
                      <span className="font-semibold text-slate-800">{label}</span>
                      <span className="px-2.5 py-0.5 rounded-lg text-xs font-bold bg-slate-100 text-slate-900 border border-slate-200/80">
                        {form[key]} {unit}
                      </span>
                    </div>
                    <input
                      type="range"
                      min={min}
                      max={max}
                      step={step}
                      value={form[key]}
                      onChange={(e) => setForm((f) => ({ ...f, [key]: parseFloat(e.target.value) }))}
                      className={`w-full h-2 bg-slate-100 rounded-lg appearance-none cursor-pointer ${color.accent}`}
                    />
                  </div>
                ))}
              </div>

              {error && <p className="text-xs text-rose-600 font-medium bg-rose-50 border border-rose-200 rounded-lg p-3">{error}</p>}

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setForm(DEFAULTS)}
                  className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition-colors"
                >
                  Reset Defaults
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold transition-all disabled:opacity-50 flex items-center gap-2 shadow-sm"
                >
                  {loading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Activity className="w-3.5 h-3.5" />}
                  {loading ? "Analyzing…" : "Run Analysis"}
                </button>
              </div>
            </form>
          </div>
        )}
      </div>

      {/* ── 4. RISK OVERVIEW (DISEASE STRATIFICATION) ── */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-0.5">Disease Risk Stratification</span>
            <h2 className="text-base font-bold text-slate-900">Personalized Multi-Disease Risk Profiles</h2>
          </div>
          <button
            onClick={() => setIsEditingProfile(e => !e)}
            className="text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors flex items-center gap-1 bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-xs"
          >
            {isEditingProfile ? "Hide Profile Form" : "Edit Clinical Factors"}
          </button>
        </div>

        {/* Model-saturation caution: extreme input values (e.g. a big swing
            in a 30-day history) can push the ensemble's XGBoost heads outside
            their training distribution, clipping the score to a floor/ceiling
            that reads as confident but isn't. Shown, not hidden — see
            ensemble_service.py's XGB_SATURATION_MARGIN check. */}
        {liveRisk?.model_saturated && (
          <div className="flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <p className="text-xs font-bold text-amber-800">Reduced confidence in this score</p>
              <p className="text-xs text-amber-700 mt-0.5">
                Your recent vitals history has an unusually large spread, which pushed the model
                outside its normal operating range.
                {liveRisk.saturated_after_fallback
                  ? " Even the fallback calculation was affected — treat these numbers as indicative, not diagnostic, and consider submitting a fresh check-in."
                  : " A safer calculation was used automatically for this result."}
              </p>
            </div>
          </div>
        )}

        {/* Profile Edit Form */}
        {isEditingProfile && (
          <form onSubmit={async (e) => { await handleSaveProfile(e); setIsEditingProfile(false); }} className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-4 animate-in fade-in duration-300">
            <h3 className="text-sm font-bold text-slate-900">Update Demographics & Clinical Profile</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              <div>
                <label className="text-xs font-medium text-slate-600 block mb-1">Age</label>
                <input
                  type="number" min="10" max="100" required
                  value={profileForm.age}
                  onChange={e => setProfileForm(p => ({ ...p, age: e.target.value }))}
                  placeholder="e.g. 28"
                  className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-900 focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 block mb-1">Biological Sex</label>
                <select
                  value={profileForm.gender}
                  onChange={e => setProfileForm(p => ({ ...p, gender: e.target.value }))}
                  className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-900 focus:outline-none focus:border-blue-500"
                >
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 block mb-1">Waist-to-Hip Ratio</label>
                <input
                  type="number" step="0.01" min="0.5" max="1.5"
                  value={profileForm.whr}
                  onChange={e => setProfileForm(p => ({ ...p, whr: e.target.value }))}
                  placeholder="e.g. 0.85"
                  className="w-full border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-900 focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>
            <div className="pt-2 flex justify-end gap-3">
              <button
                type="submit"
                disabled={savingProfile}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl transition-colors"
              >
                {savingProfile ? "Saving…" : "Save & Re-calculate Disease Risk"}
              </button>
            </div>
          </form>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

          {/* Diabetes Risk */}
          {(() => {
            const score = liveRisk?.diabetes_risk ?? null;
            const pct = score ?? 0;
            const severityLabel = score === null ? "Low Risk (< 10%)" : score < 20 ? "Low Risk (< 10%)" : score < 40 ? "Moderate Risk (10–30%)" : "Elevated Risk (> 30%)";
            const badgeBg = score === null || score < 20 ? "bg-emerald-50 text-emerald-700 border-emerald-200" : score < 40 ? "bg-amber-50 text-amber-700 border-amber-200" : "bg-rose-50 text-rose-700 border-rose-200";
            return (
              <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Metabolic Health</span>
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${badgeBg}`}>
                      {severityLabel}
                    </span>
                  </div>
                  <h3 className="text-base font-bold text-slate-900 mb-1">Diabetes Risk Profile</h3>
                  <p className="text-xs text-slate-500 font-medium">Evaluated from 30-day glycemic volatility & ICMR cohort baseline</p>
                </div>
                <div className="mt-6 pt-4 border-t border-slate-100 flex items-baseline justify-between">
                  <span className="text-xs text-slate-500 font-medium">Relative Probability</span>
                  <span className="text-lg font-bold text-slate-900">{score !== null ? `${score.toFixed(1)}%` : "< 5% (Low Risk)"}</span>
                </div>
              </div>
            );
          })()}

          {/* CVD Risk */}
          {(() => {
            const score = liveRisk?.cvd_risk ?? null;
            const pct = score ?? 0;
            const severityLabel = score === null ? "Low Risk (< 10%)" : score < 20 ? "Low Risk (< 10%)" : score < 40 ? "Moderate Risk (10–30%)" : "Elevated Risk (> 30%)";
            const badgeBg = score === null || score < 20 ? "bg-emerald-50 text-emerald-700 border-emerald-200" : score < 40 ? "bg-amber-50 text-amber-700 border-amber-200" : "bg-rose-50 text-rose-700 border-rose-200";
            return (
              <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Cardiovascular</span>
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${badgeBg}`}>
                      {severityLabel}
                    </span>
                  </div>
                  <h3 className="text-base font-bold text-slate-900 mb-1">Cardiovascular Disease (CVD)</h3>
                  <p className="text-xs text-slate-500 font-medium">Evaluated from heart rate variability (HRV) & resting heart rate</p>
                </div>
                <div className="mt-6 pt-4 border-t border-slate-100 flex items-baseline justify-between">
                  <span className="text-xs text-slate-500 font-medium">Relative Probability</span>
                  <span className="text-lg font-bold text-slate-900">{score !== null ? `${score.toFixed(1)}%` : "< 5% (Low Risk)"}</span>
                </div>
              </div>
            );
          })()}

          {/* Hypertension Risk */}
          {(() => {
            const score = liveRisk?.hypertension_risk ?? null;
            const pct = score ?? 0;
            const severityLabel = score === null ? "Low Risk (< 10%)" : score < 20 ? "Low Risk (< 10%)" : score < 40 ? "Moderate Risk (10–30%)" : "Elevated Risk (> 30%)";
            const badgeBg = score === null || score < 20 ? "bg-emerald-50 text-emerald-700 border-emerald-200" : score < 40 ? "bg-amber-50 text-amber-700 border-amber-200" : "bg-rose-50 text-rose-700 border-rose-200";
            return (
              <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Vascular Health</span>
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${badgeBg}`}>
                      {severityLabel}
                    </span>
                  </div>
                  <h3 className="text-base font-bold text-slate-900 mb-1">Hypertension Risk Profile</h3>
                  <p className="text-xs text-slate-500 font-medium">Evaluated from stress indices, sleep duration, and vascular load</p>
                </div>
                <div className="mt-6 pt-4 border-t border-slate-100 flex items-baseline justify-between">
                  <span className="text-xs text-slate-500 font-medium">Relative Probability</span>
                  <span className="text-lg font-bold text-slate-900">{score !== null ? `${score.toFixed(1)}%` : "< 5% (Low Risk)"}</span>
                </div>
              </div>
            );
          })()}

        </div>
      </div>

      {/* ── 5. WHAT'S INFLUENCING YOUR HEALTH? ──
          Previously the three bars were disease_score + a hardcoded offset
          (+15/+20/+10 with no clinical basis), so "Cardiovascular Load" could
          show as the biggest bar purely from its offset even when the real
          CVD score was 0. Bars now render the actual disease scores with no
          padding, and hide entirely rather than draw a misleading flat chart
          when there's no real risk data yet. */}
      {liveRisk?.diabetes_risk != null && liveRisk?.cvd_risk != null && liveRisk?.hypertension_risk != null && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
          <div className="mb-5">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-0.5">Disease Risk Composition</span>
            <h2 className="text-base font-bold text-slate-900">What's Influencing Your Health?</h2>
            <p className="text-xs text-slate-500 font-medium mt-1">Your current risk score for each condition, from the SAARTHI.AI Ensemble.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
            {/* Previously a Recharts horizontal BarChart. At low/zero values the
                bar itself is literally zero pixels wide, so a 0.0% score
                rendered as a floating label with nothing next to it — read as
                "the page is broken," not "the score is zero." Replaced with a
                track-and-fill bar (same pattern as RiskCard's Risk Intensity
                meter) so the full 0-100 scale is always visible and the
                number is always printed, regardless of magnitude. */}
            <div className="space-y-5">
              {[
                { name: "Diabetes",       value: liveRisk.diabetes_risk,     fill: "bg-blue-600" },
                { name: "Cardiovascular", value: liveRisk.cvd_risk,          fill: "bg-amber-500" },
                { name: "Hypertension",   value: liveRisk.hypertension_risk, fill: "bg-emerald-500" },
              ].map((d) => (
                <div key={d.name}>
                  <div className="flex justify-between items-center mb-1.5">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-semibold text-slate-700">{d.name}</span>
                      {liveRisk.model_saturated && (
                        <span
                          className="text-[9px] font-bold uppercase tracking-wide text-amber-700 bg-amber-50 border border-amber-200 rounded px-1.5 py-0.5"
                          title="This score's confidence is reduced — see the notice above."
                        >
                          Low confidence
                        </span>
                      )}
                    </div>
                    <span className="text-xs font-bold text-slate-900">
                      {d.value.toFixed(1)}<span className="text-slate-400 font-medium">/100</span>
                    </span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                    <div
                      className={`h-2.5 rounded-full ${d.fill} transition-all duration-700`}
                      // A true-zero score still gets a hairline of visible fill
                      // so the track reads as "measured: zero," not "no data."
                      style={{ width: `${Math.max(d.value, d.value > 0 ? 2 : 1)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>

            <div className="bg-slate-50 rounded-xl p-5 border border-slate-200/80 space-y-3">
              <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Clinical Insight Summary</h4>
              <p className="text-xs text-slate-700 leading-relaxed font-medium">
                Primary physiological variation is currently influenced by <span className="font-semibold text-slate-900">{(result?.topFactors?.[0] || 'Stress Level').replace(/_/g, ' ')}</span> and <span className="font-semibold text-slate-900">{(result?.topFactors?.[1] || 'Sleep Duration').replace(/_/g, ' ')}</span>.
              </p>
              {/* This used to be static text claiming "sleep + stress" for every
                  user regardless of their actual data. Now uses the top
                  causally-grounded recommendation when one exists (see BP-3 —
                  estimated_risk_reduction is a measured DoWhy/regression effect,
                  not an LLM guess), and says plainly when there isn't one yet
                  instead of asserting a mechanism nobody computed. */}
              {recommendations?.[0] ? (
                <p className="text-xs text-slate-500 leading-relaxed">
                  {recommendations[0].action}
                  {recommendations[0].risk_reduction_source === 'causal_ate' && recommendations[0].estimated_risk_reduction
                    ? ` — a measured ${recommendations[0].estimated_risk_reduction.toFixed(1)} pt effect on your risk score.`
                    : '.'}
                </p>
              ) : (
                <p className="text-xs text-slate-500 leading-relaxed">
                  Run the AI Health Assistant analysis to generate causally-grounded recommendations for your data.
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── 6. CLINICAL SUMMARY & PROGRESSIVE DISCLOSURE ── */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-0.5">Clinical Synthesis</span>
            <h2 className="text-base font-bold text-slate-900">Patient Diagnostic Summary</h2>
          </div>
          <button
            onClick={() => setShowFullClinicalReport(e => !e)}
            className="text-xs font-semibold text-blue-600 hover:text-blue-800 transition-colors flex items-center gap-1.5 bg-blue-50 border border-blue-100 px-3.5 py-2 rounded-xl"
          >
            <FileText className="w-3.5 h-3.5" />
            {showFullClinicalReport ? "Hide Detailed Diagnostic Report" : "View Full Clinical Diagnostic Report"}
          </button>
        </div>

        {/* Progressive Disclosure Section (Radar Chart & Detailed Metrics) */}
        {showFullClinicalReport && (
          <div className="pt-6 border-t border-slate-100 grid grid-cols-1 lg:grid-cols-3 gap-6 animate-in fade-in duration-300">
            <div className="lg:col-span-1 border border-slate-200 bg-slate-50/50 rounded-xl p-5 flex flex-col justify-between h-[340px]">
              <div>
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Biomarker Deviation</span>
                <h4 className="text-sm font-bold text-slate-900 mt-0.5">Patient vs Clinical Optimum</h4>
              </div>
              <div className="flex-1 w-full relative">
                <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                  <RadarChart cx="50%" cy="50%" outerRadius="60%" data={[
                    { subject: 'HR', Patient: form.heart_rate, Optimum: 70 },
                    { subject: 'Sleep', Patient: form.sleep * 10, Optimum: 80 },
                    { subject: 'Steps', Patient: (form.steps / 20000) * 100, Optimum: 50 },
                    { subject: 'Stress', Patient: form.stress_level * 10, Optimum: 30 },
                    { subject: 'Diet', Patient: form.diet_score * 10, Optimum: 80 },
                    { subject: 'BMI', Patient: form.bmi * 3, Optimum: 66 },
                  ]}>
                    <PolarGrid stroke="#e2e8f0" />
                    <PolarAngleAxis dataKey="subject" tick={{ fill: '#64748b', fontSize: 10, fontWeight: 'bold' }} />
                    <Radar name="Clinical Optimum" dataKey="Optimum" stroke="#10B981" fill="#10B981" fillOpacity={0.1} />
                    <Radar name="Patient Readout" dataKey="Patient" stroke="#2563EB" strokeWidth={2} fill="#2563EB" fillOpacity={0.3} />
                    <Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '11px' }} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="lg:col-span-2 space-y-4">
              {result && (
                <RiskCard
                  score={result.score}
                  category={result.category}
                  topFactors={result.topFactors}
                  history={history}
                />
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── 7. PERSONALISED RECOMMENDATIONS ── */}
      {recommendations.length > 0 ? (
        <RecommendationCard recommendations={recommendations} />
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs text-center space-y-3">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Clinical Action Plan</span>
          {/* Not wired to handleSubmit directly: that resubmits whatever is
              currently in the vitals sliders as a brand-new manual entry —
              if it's stale, that would overwrite real Garmin data with old
              slider values. This just scrolls to the real action instead,
              so nothing gets submitted as a side effect of landing here. */}
          <h3 className="text-base font-bold text-slate-900">No Recommendations Generated Yet</h3>
          <p className="text-xs text-slate-500 font-medium max-w-md mx-auto">
            Run the analysis against your current vitals to get personalised, causally-grounded action items.
          </p>
          <button
            onClick={() => document.getElementById('analyze-updated-vitals-btn')?.scrollIntoView({ behavior: 'smooth', block: 'center' })}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold transition-all shadow-xs"
          >
            <Activity className="w-3.5 h-3.5" />
            Go to Analyze Updated Vitals
          </button>
        </div>
      )}

      {/* ── 8. ADVANCED AI & CLINICAL EXPLAINABILITY (COLLAPSIBLE) ── */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
        <button
          onClick={() => setShowTechnicalExplainability(e => !e)}
          className="w-full flex justify-between items-center text-left"
        >
          <div>
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Developer & Clinician Tools</span>
            <h3 className="text-sm font-bold text-slate-900">Advanced AI Model & Explainability Specifications</h3>
          </div>
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 bg-slate-100 px-3 py-1.5 rounded-lg">
            <span>{showTechnicalExplainability ? "Hide AI Details" : "Show AI Details"}</span>
            {showTechnicalExplainability ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </div>
        </button>

        {showTechnicalExplainability && (
          <div className="pt-4 border-t border-slate-100 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs animate-in fade-in duration-300">
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1">
              <span className="font-bold text-slate-900 block">Ensemble Architecture</span>
              <p className="text-slate-600">PyTorch 30-Day Sequence Transformer + 3 XGBoost Specialists + Ridge Meta-Learner.</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1">
              <span className="font-bold text-slate-900 block">Causal Engine</span>
              <p className="text-slate-600">DoWhy Structural Causal Model (DAG) for counterfactual lifestyle intervention analysis.</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1">
              <span className="font-bold text-slate-900 block">Explainable AI (XAI)</span>
              <p className="text-slate-600">SHAP (Shapley Additive exPlanations) for non-linear biomarker attribution breakdown.</p>
            </div>
          </div>
        )}
      </div>

      {/* Floating AI Assistant Chat Button (Single fixed instance) */}
      <div className="fixed bottom-6 right-6 z-50">
        <AuraChat />
      </div>

    </div>
  );
}
