"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Radio, Compass, BellRing, Settings2, LogOut, MessageSquare, Swords, FlaskConical } from "lucide-react";

const NAV_ITEMS = [
  { href: "/dashboard",  label: "Health Dashboard",     icon: Activity },
  { href: "/simulation", label: "Risk Trajectories",    icon: Radio },
  { href: "/insights",   label: "Clinical Insights",    icon: Compass },
  { href: "/alerts",     label: "Alerts & Notifications", icon: BellRing },
  { href: "/arena",      label: "AI Model Benchmarks",  icon: Swords, highlight: true },
  { href: "/chat",       label: "AI Health Assistant",  icon: MessageSquare, highlight: true },
  { href: "/validation", label: "Model Validation",     icon: FlaskConical, highlight: true },
  { href: "/settings",   label: "Preferences & Profile", icon: Settings2 },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 xl:w-72 border-r border-slate-200 bg-white flex flex-col shrink-0 z-10">
      <div className="h-20 border-b border-slate-100 flex items-center px-6 bg-white">
        <Link href="/" className="flex items-center gap-3 group">
          <div className="w-9 h-9 rounded-xl overflow-hidden ring-1 ring-slate-200 flex-shrink-0 group-hover:border-blue-300 transition-colors">
            <img src="/image.png" alt="SAARTHI.AI" className="w-full h-full object-cover" />
          </div>
          <div className="flex flex-col leading-none">
            <span className="text-[18px] font-extrabold tracking-tight text-slate-900">
              SAARTHI<span className="text-blue-600">.AI</span>
            </span>
            <span className="text-[11px] font-semibold text-slate-400 mt-0.5">
              Preventive Health Platform
            </span>
          </div>
        </Link>
      </div>

      <nav className="flex-1 py-6 px-3 flex flex-col gap-1 relative overflow-y-auto">
        <div className="text-[11px] text-slate-400 font-semibold uppercase tracking-wider mb-2 px-3">Patient Navigation</div>
        {NAV_ITEMS.map(({ href, label, icon: Icon, highlight }) => {
          const isActive = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3.5 py-3 text-[13px] font-medium rounded-xl transition-all ${
                isActive
                  ? "bg-blue-50 text-blue-700 font-semibold border border-blue-100/80"
                  : highlight
                  ? "text-blue-600 hover:text-blue-800 hover:bg-blue-50/60 border border-transparent"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50 border border-transparent"
              }`}
            >
              <Icon className="w-4 h-4" strokeWidth={isActive ? 2.2 : 1.8} />
              {label}
              {highlight && !isActive && (
                <span className="ml-auto text-[9px] font-bold uppercase tracking-wider text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded border border-blue-100">
                  AI
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-100 bg-slate-50/50">
        <div className="bg-white border border-slate-200 rounded-xl p-3.5 flex items-center justify-between shadow-xs hover:border-slate-300 transition-all cursor-pointer group">
          <div className="flex flex-col">
            <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider mb-0.5">Patient / User</span>
            <span className="text-xs font-semibold text-slate-800">Roshan</span>
          </div>
          <div className="w-7 h-7 rounded-full bg-slate-100 flex items-center justify-center group-hover:bg-slate-200 transition-colors">
            <LogOut className="w-3.5 h-3.5 text-slate-500" />
          </div>
        </div>
      </div>
    </aside>
  );
}
