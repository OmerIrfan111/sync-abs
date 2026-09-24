"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle } from "lucide-react";
import { setToken, setStoredUser } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/login/json`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Incorrect email or password");
      }
      const data = await res.json();
      setToken(data.access_token);

      const meRes = await fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${data.access_token}` },
      });
      if (meRes.ok) {
        const me = await meRes.json();
        setStoredUser(me);
      }

      router.push("/");
      router.refresh();
    } catch (err: any) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen w-full flex items-center justify-center p-4 sm:p-8 bg-[#EBEDE7] overflow-hidden">
      <div
        className="absolute inset-0 scale-110"
        style={{ backgroundImage: "url('/bglogin.jpg')", backgroundSize: "cover", backgroundPosition: "center", backgroundRepeat: "no-repeat", filter: "blur(3px)" }}
      />
      <div className="relative w-full max-w-4xl bg-[#FAFAF8] border border-gray-200 rounded-lg overflow-hidden grid grid-cols-1 md:grid-cols-2">

        {/* Left panel — the desert route: distribution moves across distance */}
        <div className="relative hidden md:block min-h-[520px]">
          <img
            src="/login.jpg"
            alt=""
            className="absolute inset-0 w-full h-full object-cover object-center bg-[#1C201B]"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-[#1C201B]/80 via-[#1C201B]/10 to-transparent" />
          <div className="absolute bottom-6 left-6 right-6">
            <p className="text-white font-brand text-lg leading-snug">
              Every shipment starts somewhere.
            </p>
            <p className="text-white/70 text-xs mt-1">
              From the distributor&apos;s warehouse to a customer&apos;s door.
            </p>
          </div>
        </div>

        {/* Right panel — the form */}
        <div className="p-8 sm:p-10 flex flex-col justify-center">
          <h1 className="text-2xl font-brand font-normal text-[#1C201B]">Dispatch Console</h1>
          <p className="text-xs text-[#767676] mt-1.5 mb-7">Sign in to manage suppliers, listings, and orders.</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3 rounded bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wide text-[#767676] mb-1.5">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                className="w-full px-3 py-2.5 bg-white border border-gray-300 rounded-md text-sm text-[#1C201B] focus:outline-none focus:border-[#1C201B] focus:ring-2 focus:ring-[#1C201B]/[0.06]"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wide text-[#767676] mb-1.5">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-3 py-2.5 bg-white border border-gray-300 rounded-md text-sm text-[#1C201B] focus:outline-none focus:border-[#1C201B] focus:ring-2 focus:ring-[#1C201B]/[0.06]"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-[#D9720F] hover:bg-[#A8560A] text-white rounded-md text-sm font-semibold transition-colors disabled:opacity-50"
            >
              {loading ? "Signing in..." : "Sign In"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
