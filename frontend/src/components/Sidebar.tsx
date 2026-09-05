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
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col justify-between h-screen sticky top-0 z-30">
      <div>
        {/* Brand Header */}
        <div className="h-16 flex items-center px-6 border-b border-gray-100">
          <Link href="/" className="flex items-center">
            <img
              src="/logo.png"
              alt="سync"
              className="h-8 w-auto object-contain"
            />
          </Link>
        </div>

        {/* Navigation Links */}
        <nav className="p-3 space-y-0.5">
          {navigation.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-gray-900 text-white"
                    : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                }`}
              >
                <Icon className={`h-4 w-4 shrink-0 ${isActive ? "text-white" : "text-gray-400"}`} />
                <div className="min-w-0 flex-1">
                  <div className="font-semibold text-xs leading-none">
                    {item.name}
                  </div>
                  <div className={`text-[10px] mt-1 leading-none ${isActive ? "text-gray-300" : "text-gray-400"}`}>
                    {item.hint}
                  </div>
                </div>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer Status */}
      <div className="p-4 border-t border-gray-100">
        <div className="p-2.5 bg-gray-50 rounded-lg border border-gray-200/70">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-semibold text-gray-800 flex items-center gap-1.5">
              <Activity className="h-3 w-3 text-[#905831]" />
              Sync Engine
            </span>
            <span className="flex h-1.5 w-1.5 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
            </span>
          </div>
          <p className="text-[10px] text-gray-500 leading-snug">
            Automatic background sync active
          </p>
        </div>
      </div>
    </aside>
  );
}
