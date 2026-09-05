import React from "react";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import Navbar from "@/components/Navbar";

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
          href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Special+Elite&display=swap"
          rel="stylesheet"
        />
        <link rel="icon" href="/logo.png" />
      </head>
      <body className="bg-[#fbfbfa] text-[#1a1a1a] flex min-h-screen font-sans selection:bg-[#905831]/15 selection:text-[#905831]">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden">
          <Navbar />
          <main className="flex-1 p-6 md:p-8 lg:p-10 overflow-y-auto bg-[#fbfbfa]">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
