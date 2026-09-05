"use client";

import React from "react";
import { User, ShieldCheck } from "lucide-react";

export default function Navbar() {
  return (
    <header className="h-16 border-b border-gray-200 bg-white px-6 md:px-8 flex items-center justify-between sticky top-0 z-20">
      <div className="flex items-center gap-3">
        <span className="text-xs font-medium px-2.5 py-1 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200/80 flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
          All Systems Operational
        </span>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3 pl-4 border-l border-gray-200">
          <div className="h-8 w-8 rounded-full bg-gray-900 text-white flex items-center justify-center font-bold text-xs">
            AD
          </div>
          <div className="text-left hidden sm:block">
            <div className="text-xs font-semibold text-gray-900 leading-tight">Admin Manager</div>
            <div className="text-[11px] text-gray-500 leading-tight">admin@syncplatform.io</div>
          </div>
        </div>
      </div>
    </header>
  );
}
