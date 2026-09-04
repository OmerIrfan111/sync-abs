"use client";

import React from "react";
import { Bell, ShieldCheck, User } from "lucide-react";

export default function Navbar() {
  return (
    <header className="h-16 border-b border-gray-800/80 bg-[#0e1526]/80 backdrop-blur-md px-8 flex items-center justify-between sticky top-0 z-20">
      <div className="flex items-center gap-3">
        <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
          All Systems Operational
        </span>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2.5 pl-4 border-l border-gray-800">
          <div className="h-8 w-8 rounded-full bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <User className="h-4 w-4" />
          </div>
          <div className="text-left">
            <div className="text-xs font-semibold text-gray-200">Admin User</div>
            <div className="text-[10px] text-gray-400">admin@syncplatform.io</div>
          </div>
        </div>
      </div>
    </header>
  );
}
