"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  LayoutDashboard, 
  Layers, 
  Truck, 
  Store, 
  History, 
  Settings, 
  SlidersHorizontal,
  Activity
} from "lucide-react";

const navigation = [
  { name: "Store Overview", href: "/", icon: LayoutDashboard, hint: "Key numbers & store health" },
  { name: "Products to Sell", href: "/catalog", icon: Layers, hint: "Browse & select items" },
  { name: "Your Online Stores", href: "/listings", icon: Store, hint: "Live items & selling prices" },
  { name: "Pricing & Stock Rules", href: "/rules", icon: SlidersHorizontal, hint: "Set your profit margins" },
  { name: "Wholesale Suppliers", href: "/suppliers", icon: Truck, hint: "Distributors & stock feeds" },
  { name: "Connect Stores", href: "/marketplaces", icon: Settings, hint: "Amazon, eBay, Shopify..." },
  { name: "Activity & Alerts", href: "/logs", icon: History, hint: "Recent updates & notifications" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-white/90 backdrop-blur-2xl border-r border-black/[0.06] flex flex-col justify-between h-screen sticky top-0 z-30 shadow-[4px_0_24px_rgba(0,0,0,0.02)]">
      <div>
        {/* Brand Header */}
        <div className="h-20 flex items-center px-5 border-b border-black/[0.05] gap-3">
          <div className="h-11 w-11 rounded-2xl bg-white border border-black/[0.08] flex items-center justify-center p-1 shadow-wandor-sm shrink-0 overflow-hidden">
            <img
              src="/logo.png"
              alt="OAKAO Logo"
              className="h-full w-full object-contain mix-blend-multiply"
            />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              <span className="font-brand text-xl text-[#0a0a0a] tracking-tight">سync</span>
              <span className="text-[10px] uppercase font-semibold tracking-wider px-1.5 py-0.5 rounded-full bg-[#905831]/10 text-[#905831] border border-[#905831]/20 font-sans">
                PRO
              </span>
            </div>
            <div className="text-[11px] text-[#767676] font-medium mt-0.5 truncate">OAKAO Orchestrator</div>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="p-3.5 space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`group flex items-center gap-3 px-3.5 py-2.5 rounded-2xl text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? "bg-[#0a0a0a] text-white shadow-wandor-md"
                    : "text-[#767676] hover:text-[#0a0a0a] hover:bg-black/[0.035]"
                }`}
              >
                <Icon className={`h-4 w-4 transition-transform duration-200 group-hover:scale-110 ${isActive ? "text-white" : "text-[#767676]"}`} />
                <div className="min-w-0 flex-1">
                  <div className={`font-semibold truncate text-[13px] ${isActive ? "text-white" : "text-[#1a1a1a]"}`}>
                    {item.name}
                  </div>
                  <div className={`text-[10px] truncate ${isActive ? "text-white/70" : "text-[#767676]"}`}>
                    {item.hint}
                  </div>
                </div>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer Status Pill */}
      <div className="p-4 border-t border-black/[0.05]">
        <div className="p-3.5 bg-gradient-to-br from-white/90 to-white/60 backdrop-blur-md rounded-2xl border border-black/[0.06] shadow-wandor-sm">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-semibold text-[#1a1a1a] flex items-center gap-1.5">
              <Activity className="h-3 w-3 text-[#905831]" />
              Sync Engine
            </span>
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
          </div>
          <p className="text-[10px] text-[#767676] leading-snug">
            Automatic background sync active across all suppliers & stores
          </p>
        </div>
      </div>
    </aside>
  );
}
