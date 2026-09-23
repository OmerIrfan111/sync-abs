"use client";

import React, { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import { getStoredUser, clearAuth, AuthUser } from "@/lib/auth";

const ROLE_LABELS: Record<string, string> = {
  admin: "Admin",
  operator: "Operator",
  viewer: "Viewer",
};

const PAGE_TITLES: Record<string, string> = {
  "/": "Store Overview",
  "/catalog": "Products to Sell",
  "/listings": "Your Online Stores",
  "/orders": "Orders",
  "/analytics": "Analytics",
  "/rules": "Pricing & Stock Rules",
  "/suppliers": "Wholesale Suppliers",
  "/marketplaces": "Connect Stores",
  "/logs": "Activity & Alerts",
};

export default function Navbar() {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    setUser(getStoredUser());
  }, []);

  const handleLogout = () => {
    clearAuth();
    router.replace("/login");
  };

  const initials = (user?.full_name || user?.email || "?")
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase())
    .join("") || "?";

  return (
    <header className="h-16 border-b border-gray-100 bg-white/80 backdrop-blur-sm px-6 md:px-8 flex items-center justify-between sticky top-0 z-20">
      <div className="text-sm font-semibold text-[#1B1B2F]">
        {PAGE_TITLES[pathname] || ""}
      </div>

      <div className="flex items-center gap-3 pl-3 pr-1.5 py-1.5 rounded-full bg-gray-50 border border-gray-100">
        <div className="h-8 w-8 rounded-full bg-[#6C5DD3] text-white flex items-center justify-center font-bold text-xs shrink-0">
          {initials}
        </div>
        <div className="text-left hidden sm:block">
          <div className="text-xs font-semibold text-[#1B1B2F] leading-tight">
            {user?.full_name || (user?.is_superuser ? "Admin" : ROLE_LABELS[user?.role || ""] || "Staff")}
          </div>
          <div className="text-[11px] text-gray-500 leading-tight">{user?.email || ""}</div>
        </div>
        <button
          onClick={handleLogout}
          title="Sign out"
          className="p-1.5 rounded-full text-gray-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}
