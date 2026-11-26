"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Bell, CheckCircle2, LogOut } from "lucide-react";
import { getStoredUser, clearAuth, AuthUser } from "@/lib/auth";
import { fetchApi } from "@/lib/api";

const ROLE_LABELS: Record<string, string> = {
  admin: "Admin",
  operator: "Operator",
  viewer: "Viewer",
};

const BACKUP_OK_CLASS = "px-4 py-2.5 border-t border-gray-100 text-[11px] text-gray-600";
const BACKUP_WARN_CLASS = "px-4 py-2.5 border-t border-rose-200 text-[11px] text-rose-900 bg-rose-50";

interface AlertItem {
  id: number;
  error_type: string;
  message: string;
  order_id?: number | null;
  created_at: string;
}

interface AlertSummary {
  pending_total: number;
  orders_attention: number;
  backup: { last_backup_at?: string | null; status?: string | null; detail?: string | null };
}

function alertLink(a: AlertItem): { href: string; label: string } {
  if (a.order_id) return { href: `/orders?order=${a.order_id}`, label: "Open order" };
  if (a.error_type === "BACKUP_PROBLEM") return { href: "/", label: "View" };
  return { href: "/logs", label: "View" };
}

function backupLine(b?: AlertSummary["backup"]): { text: string; ok: boolean } {
  if (!b || !b.last_backup_at) return { text: "No database backup has run yet.", ok: false };
  const when = new Date(b.last_backup_at).toLocaleString();
  if (b.status !== "ok") return { text: `Last backup FAILED (${when}).`, ok: false };
  return { text: `Last database backup: ${when}.`, ok: true };
}

export default function Navbar() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [open, setOpen] = useState(false);
  const [summary, setSummary] = useState<AlertSummary | null>(null);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [busyId, setBusyId] = useState<number | null>(null);
  const boxRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setUser(getStoredUser());
  }, []);

  const loadAlerts = useCallback(async () => {
    try {
      const [s, list] = await Promise.all([
        fetchApi<AlertSummary>("/errors/summary"),
        fetchApi<{ items: AlertItem[] }>("/errors?unresolved=true&page_size=8"),
      ]);
      setSummary(s);
      setAlerts(list.items || []);
    } catch {
      // Not signed in yet, or the API is briefly unavailable: keep the last view.
    }
  }, []);

  useEffect(() => {
    loadAlerts();
    const timer = setInterval(loadAlerts, 45000);
    return () => clearInterval(timer);
  }, [loadAlerts]);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const markHandled = async (id: number) => {
    setBusyId(id);
    try {
      await fetchApi(`/errors/${id}/resolve`, { method: "POST" });
      await loadAlerts();
    } finally {
      setBusyId(null);
    }
  };

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

  const count = summary?.pending_total ?? 0;
  const backup = backupLine(summary?.backup);

  return (
    <header className="h-16 border-b border-gray-100 bg-white/80 backdrop-blur-sm px-6 md:px-8 flex items-center justify-end gap-3 sticky top-0 z-20">
      <div className="relative" ref={boxRef}>
        <button
          onClick={() => {
            setOpen((v) => !v);
            loadAlerts();
          }}
          title="Alerts"
          aria-label={count > 0 ? `${count} alerts need attention` : "No alerts"}
          className="relative p-2 rounded-full text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition-colors"
        >
          <Bell className="h-5 w-5" />
          {count > 0 && (
            <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-rose-600 text-white text-[10px] font-bold flex items-center justify-center">
              {count > 99 ? "99+" : count}
            </span>
          )}
        </button>

        {open && (
          <div className="absolute right-0 mt-2 w-[380px] max-w-[92vw] bg-white border border-gray-200 rounded-lg shadow-lg z-30">
            <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
              <span className="text-sm font-bold text-gray-900">Alerts</span>
              <span className="text-xs text-gray-600">{count === 0 ? "Nothing needs attention" : `${count} need attention`}</span>
            </div>

            <div className="max-h-[360px] overflow-y-auto">
              {alerts.length === 0 ? (
                <div className="px-4 py-8 text-center text-xs text-gray-600">
                  <CheckCircle2 className="h-6 w-6 text-emerald-600 mx-auto mb-1.5" />
                  All clear.
                </div>
              ) : (
                alerts.map((a) => {
                  const link = alertLink(a);
                  return (
                    <div key={a.id} className="px-4 py-3 border-b border-gray-100 last:border-b-0">
                      <p className="text-xs text-gray-900 leading-snug">{a.message}</p>
                      <div className="mt-1.5 flex items-center justify-between gap-3">
                        <span className="text-[11px] text-gray-500" suppressHydrationWarning>
                          {new Date(a.created_at).toLocaleString()}
                        </span>
                        <div className="flex items-center gap-2">
                          <Link
                            href={link.href}
                            onClick={() => setOpen(false)}
                            className="text-[11px] font-semibold text-[#A8560A] hover:underline"
                          >
                            {link.label}
                          </Link>
                          <button
                            onClick={() => markHandled(a.id)}
                            disabled={busyId === a.id}
                            className="text-[11px] font-semibold text-gray-700 hover:text-gray-900 disabled:opacity-50"
                          >
                            {busyId === a.id ? "Saving..." : "Mark handled"}
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            <div className={backup.ok ? BACKUP_OK_CLASS : BACKUP_WARN_CLASS}>{backup.text}</div>
          </div>
        )}
      </div>

      <div className="flex items-center gap-3 pl-3 pr-1.5 py-1.5 rounded-lg bg-gray-50 border border-gray-100">
        <Link href="/account" title="My account and password" className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-full bg-[#D9720F] text-white flex items-center justify-center font-bold text-xs shrink-0">
            {initials}
          </div>
          <div className="text-left hidden sm:block">
            <div className="text-xs font-semibold text-[#1C201B] leading-tight">
              {user?.full_name || (user?.is_superuser ? "Admin" : ROLE_LABELS[user?.role || ""] || "Staff")}
            </div>
            <div className="text-[11px] text-gray-500 leading-tight">{user?.email || ""}</div>
          </div>
        </Link>
        <button
          onClick={handleLogout}
          title="Sign out"
          className="p-1.5 rounded-full text-gray-600 hover:text-rose-700 hover:bg-gray-100 transition-colors"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}
