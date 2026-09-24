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
  ShoppingCart,
  BarChart3
} from "lucide-react";

const navGroups = [
  {
    label: "Overview",
    items: [
      { name: "Store Overview", href: "/", icon: LayoutDashboard },
      { name: "Analytics", href: "/analytics", icon: BarChart3 },
    ],
  },
  {
    label: "Sell",
    items: [
      { name: "Products to Sell", href: "/catalog", icon: Layers },
      { name: "Your Online Stores", href: "/listings", icon: Store },
      { name: "Pricing & Stock Rules", href: "/rules", icon: SlidersHorizontal },
    ],
  },
  {
    label: "Connections",
    items: [
      { name: "Wholesale Suppliers", href: "/suppliers", icon: Truck },
      { name: "Connect Stores", href: "/marketplaces", icon: Settings },
    ],
  },
  {
    label: "Operations",
    items: [
      { name: "Orders", href: "/orders", icon: ShoppingCart },
      { name: "Activity & Alerts", href: "/logs", icon: History },
    ],
  },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-white border-r border-gray-100 flex flex-col justify-between h-screen sticky top-0 z-30">
      <div className="overflow-y-auto">
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
        <nav className="p-3 space-y-4">
          {navGroups.map((group) => (
            <div key={group.label}>
              <div className="px-3 pb-1.5 text-[10px] font-bold uppercase tracking-wider text-gray-400">
                {group.label}
              </div>
              <div className="space-y-0.5">
                {group.items.map((item) => {
                  const isActive = pathname === item.href;
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.name}
                      href={item.href}
                      className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                        isActive
                          ? "bg-[#D9720F]/10 text-[#A8560A]"
                          : "text-gray-600 hover:text-[#1C201B] hover:bg-gray-50"
                      }`}
                    >
                      <Icon className={`h-4 w-4 shrink-0 ${isActive ? "text-[#A8560A]" : "text-gray-400"}`} />
                      <span className="font-semibold text-xs">{item.name}</span>
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </div>
    </aside>
  );
}
