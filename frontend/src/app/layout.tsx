import React from "react";
import "./globals.css";
import AuthGuard from "@/components/AuthGuard";

export const metadata = {
  title: "سync — Multi-Supplier Dropshipping & Inventory Synchronization",
  description: "Automated dropshipping and real-time inventory synchronization engine",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Bebas+Neue&family=Scheherazade+New:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
        <link rel="icon" href="/logo.png" />
      </head>
      <body className="bg-[#EBEDE7] text-[#1a1a1a] font-sans selection:bg-[#D9720F]/15 selection:text-[#A8560A]">
        <AuthGuard>{children}</AuthGuard>
      </body>
    </html>
  );
}
