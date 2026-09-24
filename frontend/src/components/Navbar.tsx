"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import { getStoredUser, clearAuth, AuthUser } from "@/lib/auth";

const ROLE_LABELS: Record<string, string> = {
  admin: "Admin",
  operator: "Operator",
  viewer: "Viewer",
};

export default function Navbar() {
  const router = useRouter();
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
    <header className="h-16 border-b border-gray-100 bg-white/80 backdrop-blur-sm px-6 md:px-8 flex items-center justify-end sticky top-0 z-20">
      <div className="flex items-center gap-3 pl-3 pr-1.5 py-1.5 rounded-lg bg-gray-50 border border-gray-100">
        <div className="h-8 w-8 rounded-full bg-[#D9720F] text-white flex items-center justify-center font-bold text-xs shrink-0">
          {initials}
        </div>
        <div className="text-left hidden sm:block">
          <div className="text-xs font-semibold text-[#1C201B] leading-tight">
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
