"use client";

import React, { useEffect, useState } from "react";
import { CheckCircle2, AlertCircle } from "lucide-react";
import { fetchApi } from "@/lib/api";
import { getStoredUser, AuthUser } from "@/lib/auth";

const ROLE_LABELS: Record<string, string> = { admin: "Admin", operator: "Operator", viewer: "Viewer" };

export default function AccountPage() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState<{ type: "success" | "error"; message: string } | null>(null);

  useEffect(() => {
    setUser(getStoredUser());
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setResult(null);
    if (next.length < 8) {
      setResult({ type: "error", message: "The new password needs at least 8 characters." });
      return;
    }
    if (next !== confirm) {
      setResult({ type: "error", message: "The two new passwords don't match." });
      return;
    }
    setSaving(true);
    try {
      await fetchApi("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({ current_password: current, new_password: next }),
      });
      setResult({ type: "success", message: "Password changed. Use the new one next time you sign in." });
      setCurrent("");
      setNext("");
      setConfirm("");
    } catch (err: any) {
      setResult({ type: "error", message: err?.message || "Could not change the password." });
    } finally {
      setSaving(false);
    }
  };

  const field =
    "w-full px-3 py-2 bg-white border border-gray-300 rounded-md text-sm text-gray-900 focus:outline-none focus:border-gray-900";

  return (
    <div className="max-w-lg mx-auto space-y-6 pb-12">
      <div className="pb-2 border-b border-gray-200">
        <h1 className="text-2xl font-brand font-normal text-gray-900">My account</h1>
        <p className="text-sm text-gray-600 mt-1">
          {user?.email} &middot; {ROLE_LABELS[user?.role || ""] || "Staff"}
        </p>
      </div>

      <form onSubmit={submit} className="bg-white rounded-lg border border-gray-200 p-5 space-y-4">
        <h2 className="text-base font-bold text-gray-900">Change password</h2>

        {result && (
          <div
            className={`p-3 rounded-lg border flex items-center gap-2 text-xs font-semibold ${
              result.type === "success"
                ? "bg-emerald-50 border-emerald-300 text-emerald-900"
                : "bg-rose-50 border-rose-300 text-rose-900"
            }`}
          >
            {result.type === "success" ? (
              <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
            ) : (
              <AlertCircle className="h-4 w-4 text-rose-600 shrink-0" />
            )}
            <span>{result.message}</span>
          </div>
        )}

        <label className="block text-xs font-medium text-gray-700">
          Current password
          <input type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} className={`${field} mt-1`} required />
        </label>
        <label className="block text-xs font-medium text-gray-700">
          New password (at least 8 characters)
          <input type="password" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} className={`${field} mt-1`} required />
        </label>
        <label className="block text-xs font-medium text-gray-700">
          Repeat the new password
          <input type="password" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} className={`${field} mt-1`} required />
        </label>

        <button
          type="submit"
          disabled={saving}
          className="px-4 py-2 bg-gray-900 hover:bg-gray-800 text-white rounded-lg text-xs font-semibold transition-colors disabled:opacity-50"
        >
          {saving ? "Saving..." : "Change password"}
        </button>
      </form>
    </div>
  );
}
