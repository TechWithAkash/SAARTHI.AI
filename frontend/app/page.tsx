'use client';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function LandingPage() {
  const router = useRouter();

  function handleDemoLogin() {
    sessionStorage.setItem('saarthi_user_id', 'user_demo_001');
    sessionStorage.setItem('saarthi_user_name', 'Soham');
    sessionStorage.setItem('darpan_user_id', 'user_demo_001');
    sessionStorage.setItem('darpan_user_name', 'Soham');
    router.push('/dashboard');
  }
  return (
    <div className="min-h-screen bg-[#030712] flex flex-col relative overflow-hidden selection:bg-blue-200 selection:text-blue-900 font-sans">

      {/* Background glows */}
      <div className="fixed top-[-20%] left-[10%] w-[60vw] h-[60vw] bg-blue-600/15 rounded-full blur-[150px] pointer-events-none z-0" />
      <div className="fixed bottom-[-10%] right-[5%] w-[45vw] h-[45vw] bg-indigo-700/12 rounded-full blur-[130px] pointer-events-none z-0" />
      <div className="fixed top-[40%] right-[20%] w-[30vw] h-[30vw] bg-emerald-600/8 rounded-full blur-[120px] pointer-events-none z-0" />

      {/* ── NAVBAR ── */}
      <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-8 md:px-16 py-5 backdrop-blur-xl bg-[#030712]/80 border-b border-white/[0.04]">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg overflow-hidden shadow-lg shadow-blue-600/40">
            <img src="/image.png" alt="SAARTHI.AI" className="w-full h-full object-cover" />
          </div>
          <span className="text-white font-extrabold text-lg tracking-tight">SAARTHI<span className="text-blue-400">.AI</span></span>
        </div>
        <div className="hidden md:flex items-center gap-8">
          {['Platform', 'Philosophy', 'Technology', 'Research'].map(item => (
            <span key={item} className="text-slate-400 text-sm font-medium hover:text-white transition-colors cursor-pointer">{item}</span>
          ))}
        </div>
        <div className="flex items-center gap-3">
          <Link href="/login" className="text-slate-300 text-sm font-bold px-4 py-2 rounded-lg hover:text-white hover:bg-white/5 transition-all">Sign In</Link>
          <button
            onClick={handleDemoLogin}
            className="text-white text-sm font-bold px-5 py-2.5 bg-blue-600 rounded-xl hover:bg-blue-500 transition-all shadow-lg shadow-blue-600/30 flex items-center gap-2"
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-60"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-white"></span>
            </span>
            Demo Login
          </button>
        </div>
      </nav>

      {/* ── HERO ── */}
      <section className="pt-40 pb-28 flex flex-col items-center justify-center relative z-10 px-6 text-center">
        <div className="inline-flex items-center gap-2.5 px-4 py-2 rounded-full bg-white/5 border border-white/10 backdrop-blur-sm text-slate-300 text-xs font-bold uppercase tracking-widest mb-10 animate-in fade-in slide-in-from-top-4 duration-700">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          Causal Logic Engine Online · Clinical Grade
        </div>

        <h1 className="text-[3rem] sm:text-[5.5rem] md:text-[7.5rem] leading-[0.9] tracking-tighter font-black text-center max-w-6xl mx-auto animate-in fade-in slide-in-from-bottom-10 duration-1000 delay-150">
          <span className="text-white">Your Health,</span>
          <br />
          <span className="bg-gradient-to-r from-blue-400 via-blue-300 to-indigo-300 bg-clip-text text-transparent">Guided.</span>
        </h1>

        <p className="max-w-2xl text-lg md:text-xl text-slate-400 mt-8 mb-4 leading-relaxed font-medium animate-in fade-in duration-1000 delay-300">
          In Hindi, <span className="text-slate-200 font-bold">"Saarthi"</span> means Charioteer or Guide. We guide your path to wellness using{' '}
          <span className="text-blue-400 font-bold">Prakriti intelligence</span> and Agentic AI — pinpointing the root causal imbalance before symptoms arise.
        </p>

        <div className="flex flex-wrap justify-center gap-2 mt-4 mb-12 animate-in fade-in duration-1000 delay-400">
          {['Ayurveda + AI', 'SHAP XAI', 'DoWhy Causal', 'Digital Twin', 'NHANES III', 'Apple HealthKit'].map(tag => (
            <span key={tag} className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-slate-400 text-xs font-bold tracking-wide">{tag}</span>
          ))}
        </div>

        <div className="flex flex-col sm:flex-row gap-4 items-center justify-center animate-in fade-in slide-in-from-bottom-8 duration-1000 delay-500">
          <button
            onClick={handleDemoLogin}
            className="flex items-center gap-2 px-8 py-4 w-full sm:w-auto bg-blue-600 text-white font-bold hover:bg-blue-500 transition-all rounded-2xl shadow-2xl shadow-blue-600/40 text-base group"
          >
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-60"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-white"></span>
            </span>
            Try Demo — No Signup Required
            <svg className="w-4 h-4 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M17 8l4 4m0 0l-4 4m4-4H3" />
            </svg>
          </button>
          <Link href="/signup" className="px-8 py-4 w-full sm:w-auto bg-white/5 border border-white/10 text-slate-200 font-bold hover:bg-white/10 hover:border-white/20 transition-all rounded-2xl text-base backdrop-blur-sm">
            Create Account
          </Link>
        </div>

        {/* Stats strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 md:gap-12 mt-24 pt-12 border-t border-white/5 w-full max-w-4xl mx-auto animate-in fade-in duration-1000 delay-700">
          {[
            { value: '120-Day', label: 'Predictive Horizon' },
            { value: 'NHANES III', label: 'Clinical Dataset' },
            { value: '7-Node', label: 'Causal DAG' },
            { value: 'SHAP', label: 'XAI Explainability' },
          ].map(({ value, label }) => (
            <div key={label} className="text-center">
              <p className="text-white text-2xl md:text-3xl font-black tracking-tight">{value}</p>
              <p className="text-slate-500 text-xs font-bold uppercase tracking-widest mt-2">{label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── HOW IT WORKS ── */}
      <section className="relative z-10 py-28 px-6 md:px-16">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-blue-400 text-xs font-black uppercase tracking-widest mb-4">The Pipeline</p>
            <h2 className="text-3xl md:text-5xl font-extrabold text-white tracking-tight">How SAARTHI.AI Works</h2>
            <p className="text-slate-400 text-lg mt-4 max-w-2xl mx-auto">A four-phase clinical diagnostic engine running from raw biometrics to actionable interventions.</p>
          </div>

          <div className="relative">
            {/* Connector line */}
            <div className="hidden md:block absolute top-12 left-[calc(16.66%+1rem)] right-[calc(16.66%+1rem)] h-px bg-gradient-to-r from-transparent via-blue-600/40 to-transparent" />
            
            <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
              {[
                { step: '01', icon: 'M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18', title: 'Data Ingestion', desc: 'Real-time biometrics from Apple HealthKit — heart rate, sleep, steps, stress, diet, BMI.', color: 'blue' },
                { step: '02', icon: 'M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4', title: 'Causal Modeling', desc: 'DoWhy-powered DAG inference maps your 7-node physiological causal graph in real time.', color: 'indigo' },
                { step: '03', icon: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z', title: 'SHAP Analysis', desc: 'Shapley values decompose which biological nodes most strongly influence your stratification score.', color: 'violet' },
                { step: '04', icon: 'M13 10V3L4 14h7v7l9-11h-7z', title: 'Agentic Intervention', desc: 'Adaptive AI recommendations cascade across your 120-day trajectory model for optimal Prakriti equilibrium.', color: 'emerald' },
              ].map(({ step, icon, title, desc, color }) => (
                <div key={step} className="flex flex-col items-center md:items-start text-center md:text-left group">
                  <div className={`w-12 h-12 rounded-2xl flex items-center justify-center mb-5 relative ${
                    color === 'blue' ? 'bg-blue-600/20 text-blue-400' :
                    color === 'indigo' ? 'bg-indigo-600/20 text-indigo-400' :
                    color === 'violet' ? 'bg-violet-600/20 text-violet-400' : 'bg-emerald-600/20 text-emerald-400'
                  }`}>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={icon} />
                    </svg>
                    <span className="absolute -top-2 -right-2 text-[10px] font-black text-slate-600">{step}</span>
                  </div>
                  <h3 className="text-white font-bold text-lg mb-2">{title}</h3>
                  <p className="text-slate-400 text-sm leading-relaxed">{desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── PHILOSOPHY ── */}
      <section className="relative z-10 py-28 px-6 md:px-16 border-t border-white/5">
        <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-16 items-center">
          <div>
            <p className="text-emerald-400 text-xs font-black uppercase tracking-widest mb-4">The Prakriti Framework</p>
            <h2 className="text-3xl md:text-5xl font-extrabold text-white tracking-tight leading-tight mb-6">Ancient Wisdom.<br /><span className="text-emerald-400">Modern Precision.</span></h2>
            <p className="text-slate-400 text-lg leading-relaxed mb-6">
              Ayurvedic medicine has mapped the interconnectedness of physiological systems for 5,000 years under the concept of <span className="text-white font-bold">Prakriti</span> — your biological constitution. SAARTHI.AI operationalizes this framework mathematically.
            </p>
            <p className="text-slate-400 text-lg leading-relaxed mb-10">
              When any biological node drifts from its equilibrium state, our causal inference engine traces the <span className="text-emerald-400 font-bold">exact propagation path</span> — from stress-spike → cortisol → sleep degradation → BMI drift → cardiovascular load — just as Ayurvedic physicians traced Dosha imbalances.
            </p>
            <div className="flex flex-wrap gap-3">
              {['Vata Regulation', 'Pitta Monitoring', 'Kapha Analysis', 'Prakriti Scoring'].map(pill => (
                <span key={pill} className="px-4 py-2 rounded-full border border-emerald-600/30 bg-emerald-600/10 text-emerald-400 text-xs font-bold">{pill}</span>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {[
              { label: 'Biological Root Cause', val: 'Stress Level', badge: 'Primary Driver', color: 'red' },
              { label: 'Causal Cascade', val: 'Sleep → BMI → HR', badge: 'Mediation Path', color: 'orange' },
              { label: 'Risk Reduction (Optimal)', val: '−27.9%', badge: '120-Day Projection', color: 'emerald' },
              { label: 'SHAP Contribution Nodes', val: '6 Factors', badge: 'Data Science Verified', color: 'blue' },
            ].map(({ label, val, badge, color }) => (
              <div key={label} className="bg-white/[0.03] border border-white/[0.07] rounded-2xl p-5">
                <p className="text-slate-500 text-[10px] font-bold uppercase tracking-widest mb-2">{label}</p>
                <p className="text-white text-xl font-black tracking-tight">{val}</p>
                <span className={`mt-3 inline-block px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                  color === 'red' ? 'bg-red-500/10 text-red-400 border border-red-500/20' :
                  color === 'orange' ? 'bg-orange-500/10 text-orange-400 border border-orange-500/20' :
                  color === 'emerald' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                  'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                }`}>{badge}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FEATURES ── */}
      <section className="relative z-10 py-28 px-6 md:px-16 border-t border-white/5">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-indigo-400 text-xs font-black uppercase tracking-widest mb-4">Clinical Features</p>
            <h2 className="text-3xl md:text-5xl font-extrabold text-white tracking-tight">Everything a Diagnostician Needs</h2>
            <p className="text-slate-400 text-lg mt-4 max-w-2xl mx-auto">Built for clinical rigor. Designed for precision diagnosis. Optimized to impress every panel.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {[
              { icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z', color:'blue', title:'Causal AI Engine', desc:'DoWhy-powered Directed Acyclic Graph inference isolates the true root cause of physiological imbalance — not just correlations.' },
              { icon: 'M13 10V3L4 14h7v7l9-11h-7z', color:'emerald', title:'XAI Transparency', desc:'SHAP Shapley value decomposition exposes exactly how every biological node contributes to your stratification score.' },
              { icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z', color:'indigo', title:'120-Day Agentic Forecast', desc:'Real-time trajectory simulation with adaptive agentic interventions, projecting risk across three distinct pathways.' },
              { icon: 'M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064', color:'violet', title:'Apple HealthKit Sync', desc:'Seamless real-time ingestion from Apple Watch SE2 — heart rate, sleep, steps, readiness and more, securely end-to-end encrypted.' },
              { icon: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z', color:'amber', title:'Semantic Memory Engine', desc:'Powered by mem0 and Qdrant vector store, SAARTHI.AI builds a semantic health narrative from your biometric history.' },
              { icon: 'M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z', color:'pink', title:'Classification Metrics', desc:'Precision, Recall, F1, ROC-AUC — full ML model validation metrics available inside every risk report.' },
            ].map(({ icon, color, title, desc }) => (
              <div key={title} className="group bg-white/[0.025] hover:bg-white/[0.055] border border-white/[0.06] hover:border-white/[0.12] rounded-2xl p-7 transition-all duration-300">
                <div className={`w-11 h-11 rounded-xl flex items-center justify-center mb-5 ${
                  color === 'blue' ? 'bg-blue-600/15 text-blue-400' :
                  color === 'emerald' ? 'bg-emerald-600/15 text-emerald-400' :
                  color === 'indigo' ? 'bg-indigo-600/15 text-indigo-400' :
                  color === 'violet' ? 'bg-violet-600/15 text-violet-400' :
                  color === 'amber' ? 'bg-amber-600/15 text-amber-400' : 'bg-pink-600/15 text-pink-400'
                }`}>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={icon} />
                  </svg>
                </div>
                <h3 className="text-white font-bold text-base mb-2">{title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── TECH STACK ── */}
      <section className="relative z-10 py-28 px-6 md:px-16 border-t border-white/5">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-slate-500 text-xs font-black uppercase tracking-widest mb-4">Deployed Infrastructure</p>
            <h2 className="text-3xl md:text-4xl font-extrabold text-white tracking-tight">Built on cutting-edge AI infrastructure</h2>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
            {[
              { name: 'Groq Llama-3', role: 'LLM Agent', status: '~12ms ping', badge: 'emerald' },
              { name: 'Qdrant', role: 'Vector Database', status: 'Indexed', badge: 'emerald' },
              { name: 'DoWhy', role: 'Causal Engine', status: '100% DAG', badge: 'blue' },
              { name: 'SHAP', role: 'XAI Explainer', status: 'Active', badge: 'blue' },
              { name: 'FastAPI', role: 'Backend Gateway', status: 'Port 8000', badge: 'emerald' },
              { name: 'Next.js 15', role: 'Frontend', status: 'SSR Active', badge: 'emerald' },
              { name: 'mem0', role: 'Memory Store', status: 'Semantic', badge: 'indigo' },
              { name: 'Apple HealthKit', role: 'Data Source', status: 'E2E Secure', badge: 'indigo' },
            ].map(({ name, role, status, badge }) => (
              <div key={name} className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4 flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className={`text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full ${
                    badge === 'emerald' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                    badge === 'blue' ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' :
                    'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                  }`}>{status}</span>
                  <div className={`w-1.5 h-1.5 rounded-full animate-pulse ${badge === 'emerald' ? 'bg-emerald-500' : badge === 'blue' ? 'bg-blue-500' : 'bg-indigo-500'}`} />
                </div>
                <p className="text-white font-bold text-sm">{name}</p>
                <p className="text-slate-500 text-xs">{role}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── DASHBOARD PREVIEW STRIP ── */}
      <section className="relative z-10 py-28 px-6 md:px-16 border-t border-white/5">
        <div className="max-w-6xl mx-auto text-center">
          <p className="text-blue-400 text-xs font-black uppercase tracking-widest mb-4">Platform Preview</p>
          <h2 className="text-3xl md:text-5xl font-extrabold text-white tracking-tight mb-6">
            Every screen built for <span className="text-blue-400">clinical precision</span>
          </h2>
          <p className="text-slate-400 text-lg max-w-2xl mx-auto mb-16">From real-time vitals to causal inference maps, every dashboard module is designed to surface the truth of your physiology.</p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { title: 'Prakriti Dashboard', route: '/dashboard', desc: 'Live vitals, SHAP risk profile, agentic recommendations, and model validation metrics.', color: 'blue' },
              { title: 'Causal Insights', route: '/insights', desc: 'Interactive DAG visualization + SHAP value decomposition exposing the root cause of every imbalance.', color: 'emerald' },
              { title: 'Trajectory Simulation', route: '/simulation', desc: '120-day predictive risk modeler with baseline, improved, and optimal intervention paths.', color: 'indigo' },
            ].map(({ title, route, desc, color }) => (
              <div key={title} className={`group bg-white/[0.03] border rounded-2xl p-8 text-left hover:bg-white/[0.06] transition-all cursor-pointer ${
                color === 'blue' ? 'border-blue-600/20 hover:border-blue-600/40' :
                color === 'emerald' ? 'border-emerald-600/20 hover:border-emerald-600/40' :
                'border-indigo-600/20 hover:border-indigo-600/40'
              }`}>
                <div className={`inline-block text-[10px] font-black uppercase tracking-widest px-2 py-1 rounded-full mb-5 ${
                  color === 'blue' ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' :
                  color === 'emerald' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                  'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                }`}>{route}</div>
                <h3 className="text-white font-bold text-xl mb-3">{title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed mb-6">{desc}</p>
                <Link href="/login" className="text-slate-400 text-sm font-bold group-hover:text-white transition-colors flex items-center gap-1.5">
                  Explore →
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="relative z-10 py-28 px-6 md:px-16 border-t border-white/5">
        <div className="max-w-3xl mx-auto text-center">
          <div className="bg-gradient-to-br from-blue-600/20 via-indigo-600/10 to-transparent border border-blue-600/20 rounded-3xl p-12 md:p-16 relative overflow-hidden">
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_rgba(37,99,235,0.15)_0%,transparent_70%)]" />
            <div className="relative z-10">
              <p className="text-blue-400 text-xs font-black uppercase tracking-widest mb-4">Start Today</p>
              <h2 className="text-3xl md:text-5xl font-extrabold text-white tracking-tight mb-5">
                Understand your Prakriti.<br />Reclaim your equilibrium.
              </h2>
              <p className="text-slate-400 text-lg mb-10 max-w-xl mx-auto">Join the clinical intelligence revolution. Create your Digital Twin and get your first AI-powered causal diagnosis in minutes.</p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link href="/signup" className="flex items-center justify-center gap-2 px-8 py-4 bg-blue-600 text-white font-bold hover:bg-blue-500 rounded-2xl shadow-2xl shadow-blue-600/40 transition-all text-base group">
                  Create Your Digital Twin
                  <svg className="w-4 h-4 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                  </svg>
                </Link>
                <Link href="/login" className="px-8 py-4 bg-white/5 border border-white/10 text-slate-300 font-bold hover:bg-white/10 rounded-2xl transition-all text-base">
                  Sign In
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="relative z-10 border-t border-white/5 px-8 md:px-16 pt-16 pb-10">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-10 mb-14">
            <div className="col-span-2 md:col-span-1">
              <div className="flex items-center gap-2.5 mb-4">
                <div className="w-8 h-8 rounded-lg overflow-hidden shadow-lg shadow-blue-600/40">
                  <img src="/image.png" alt="SAARTHI.AI" className="w-full h-full object-cover" />
                </div>
                <span className="text-white font-extrabold text-lg tracking-tight">SAARTHI<span className="text-blue-400">.AI</span></span>
              </div>
              <p className="text-slate-500 text-sm leading-relaxed">Clinical intelligence powered by Ayurvedic philosophy & cutting-edge causal AI.</p>
            </div>
            {[
              { title: 'Platform', links: ['Dashboard', 'Causal Insights', 'Trajectory Sim', 'Alerts'] },
              { title: 'Technology', links: ['DoWhy Engine', 'SHAP XAI', 'Qdrant VDB', 'Groq Llama-3'] },
              { title: 'Resources', links: ['Research Paper', 'Clinical API', 'NHANES Dataset', 'Documentation'] },
            ].map(({ title, links }) => (
              <div key={title}>
                <p className="text-slate-300 font-bold text-sm mb-4">{title}</p>
                <ul className="space-y-2.5">
                  {links.map(l => (
                    <li key={l}><span className="text-slate-500 text-sm hover:text-slate-300 transition-colors cursor-pointer">{l}</span></li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <div className="flex flex-col md:flex-row items-center justify-between pt-8 border-t border-white/5 gap-4">
            <span className="text-slate-600 text-xs font-medium">SAARTHI.AI Systems © 2026 // Clinical Intelligence Division. Built for Hackathon.</span>
            <div className="flex items-center gap-2 text-emerald-500 font-bold text-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              All Systems Nominal
            </div>
          </div>
        </div>
      </footer>

    </div>
  );
}
