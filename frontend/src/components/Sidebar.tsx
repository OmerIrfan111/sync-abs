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
  AlertCircle,
  Settings,
  RefreshCw,
  SlidersHorizontal
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
    <aside className="w-64 bg-[#0e1526] border-r border-gray-800 flex flex-col justify-between h-screen sticky top-0">
      <div>
        {/* Brand Header */}
        <div className="h-16 flex items-center px-6 border-b border-gray-800/80 gap-3">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center font-black text-xl text-white shadow-lg shadow-indigo-500/25">
            س
          </div>
          <div>
            <div className="font-bold text-lg text-white tracking-tight flex items-center gap-1.5">
              <span>سync</span>
              <span className="text-[10px] uppercase font-bold tracking-widest px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                Business
              </span>
            </div>
            <div className="text-[11px] text-gray-400 font-medium">Store Automation Manager</div>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="p-4 space-y-1.5">
          {navigation.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                    : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
                }`}
              >
                <Icon className={`h-4 w-4 ${isActive ? "text-white" : "text-gray-400"}`} />
                <div>
                  <div>{item.name}</div>
                  <div className={`text-[10px] ${isActive ? "text-indigo-200" : "text-gray-500"}`}>{item.hint}</div>
                </div>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer Info */}
      <div className="p-4 border-t border-gray-800/80">
        <div className="p-3 bg-gray-900/60 rounded-xl border border-gray-800">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-semibold text-gray-300">Automatic Updates</span>
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
          </div>
          <p className="text-[11px] text-gray-400">Checking prices & stock continuously</p>
        </div>
      </div>
    </aside>
  );
}
