import Link from 'next/link';

export default function Signup() {
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
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
            </svg>
          </div>
          <h2 className="text-2xl font-black text-slate-900 tracking-tight">Register Patient Node</h2>
          <p className="text-xs text-slate-500 font-medium">Create a secure profile for twin integration.</p>
        </div>

        {/* Signup Form */}
        <form className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 block">Patient Full Name</label>
            <input 
              type="text" 
              placeholder="E.g. Jane Doe" 
              className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-xs font-semibold text-slate-900 placeholder:text-slate-400 focus:outline-none focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 block">Primary Email</label>
            <input 
              type="email" 
              placeholder="patient@contact.org" 
              className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-xs font-semibold text-slate-900 placeholder:text-slate-400 focus:outline-none focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 block">Secure Password</label>
            <input 
              type="password" 
              placeholder="••••••••••••" 
              className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-xs font-semibold text-slate-900 placeholder:text-slate-400 focus:outline-none focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all tracking-widest"
            />
          </div>

          <button
            type="button"
            className="w-full py-3.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs transition-colors shadow-xs"
          >
            Initialize Twin Profile
          </button>
        </form>

        <div className="pt-4 border-t border-slate-100 text-center">
          <p className="text-xs text-slate-500 font-medium">
            Existing Patient? <Link href="/login" className="text-blue-600 font-bold hover:underline">Access Portal</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
