"use client";

import React from "react";
import { User, ShieldCheck } from "lucide-react";

export default function Navbar() {
  return (
    <header className="h-20 border-b border-black/[0.05] bg-white/70 backdrop-blur-xl px-8 flex items-center justify-between sticky top-0 z-20">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 py-1 px-3 bg-white rounded-full border border-black/[0.06] shadow-wandor-sm">
          <img
            src="/logo.png"
            alt="سync"
            className="h-4 w-auto object-contain mix-blend-multiply"
          />
          <span className="text-[10px] font-bold text-[#767676] tracking-wider uppercase">Enterprise</span>
        </div>
        <span className="text-xs font-medium px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200/60 flex items-center gap-2 shadow-wandor-sm">
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
          All Systems Operational
        </span>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3 pl-4 border-l border-black/[0.06]">
          <div className="h-9 w-9 rounded-full bg-[#0a0a0a] text-white flex items-center justify-center font-bold text-xs shadow-wandor-sm">
            AD
          </div>
          <div className="text-left hidden sm:block">
            <div className="text-xs font-semibold text-[#1a1a1a]">Admin Manager</div>
            <div className="text-[11px] text-[#767676]">admin@syncplatform.io</div>
          </div>
        </div>
      </div>
    </header>
  );
}
