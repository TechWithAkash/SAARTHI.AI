'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function Login() {
  const router = useRouter();

  function handleDemoLogin() {
    sessionStorage.setItem('saarthi_user_id', 'user_demo_001');
    sessionStorage.setItem('saarthi_user_name', 'Roshan');
    sessionStorage.setItem('darpan_user_id', 'user_demo_001');
    sessionStorage.setItem('darpan_user_name', 'Roshan');
    router.push('/dashboard');
  }

  return (
    <div className="min-h-screen bg-slate-50/80 flex flex-col items-center justify-center p-6 relative font-sans">
      
      {/* Return Home Link */}
      <Link
        href="/"
        className="absolute top-6 left-6 inline-flex items-center gap-2 text-xs font-bold text-slate-700 bg-white border border-slate-200 px-4 py-2 rounded-xl shadow-2xs hover:border-slate-300 transition-colors"
      >
        ← Return Home
      </Link>

      <div className="w-full max-w-md bg-white rounded-2xl border border-slate-200 p-8 shadow-xs relative overflow-hidden space-y-6">
        
        {/* Header Icon & Title */}
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 border border-blue-100 flex items-center justify-center mx-auto shadow-2xs">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 11c0 3.517-1.009 6.799-2.753 9.571m-3.44-2.04l.054-.09A13.916 13.916 0 008 11a4 4 0 118 0c0 1.017-.07 2.019-.203 3m-2.118 6.844A21.88 21.88 0 0015.171 17m3.839 1.132c.645-2.266.99-4.659.99-7.132A8 8 0 008 4.07M3 15.364c.64-1.319 1-2.8 1-4.364 0-1.457.39-2.823 1.07-4" />
            </svg>
          </div>
          <h2 className="text-2xl font-black text-slate-900 tracking-tight">Provider Access</h2>
          <p className="text-xs text-slate-500 font-medium">Sign in to review your clinical telemetry.</p>
        </div>

        {/* Quick Demo Login Button */}
        <button
          onClick={handleDemoLogin}
          className="w-full py-3.5 px-5 rounded-xl bg-gradient-to-r from-blue-950 via-blue-900 to-indigo-950 text-white font-bold text-xs flex items-center justify-center gap-2.5 shadow-xs hover:opacity-95 transition-opacity group"
        >
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" />
          </span>
          <span>Try Demo — Login as Roshan</span>
          <svg className="w-4 h-4 text-white group-hover:translate-x-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M17 8l4 4m0 0l-4 4m4-4H3" />
          </svg>
        </button>

        <div className="flex items-center gap-3">
          <div className="flex-1 h-px bg-slate-100" />
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">or sign in manually</span>
          <div className="flex-1 h-px bg-slate-100" />
        </div>

        {/* Manual Form */}
        <form className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 block">Provider Email</label>
            <input 
              type="email" 
              placeholder="dr.smith@hospital.org" 
              className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-xs font-semibold text-slate-900 placeholder:text-slate-400 focus:outline-none focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
            />
          </div>

          <div className="space-y-1.5">
            <div className="flex justify-between items-center">
              <label className="text-xs font-bold text-slate-700 block">Security Key</label>
              <span className="text-[11px] font-semibold text-blue-600 cursor-pointer hover:underline">Forgot?</span>
            </div>
            <input 
              type="password" 
              placeholder="••••••••••••" 
              className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-xs font-semibold text-slate-900 placeholder:text-slate-400 focus:outline-none focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all tracking-widest"
            />
          </div>

          <button
            type="button"
            className="w-full py-3.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs transition-colors shadow-xs"
          >
            Sign In Securely
          </button>
        </form>

        <div className="pt-4 border-t border-slate-100 text-center">
          <p className="text-xs text-slate-500 font-medium">
            New Provider? <Link href="/signup" className="text-blue-600 font-bold hover:underline">Register Identity</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
