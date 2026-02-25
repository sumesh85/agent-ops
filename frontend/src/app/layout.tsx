import type { Metadata } from "next";
import "./globals.css";
import SidebarNav from "@/components/SidebarNav";

export const metadata: Metadata = {
  title: "AgentOps Control Plane",
  description: "AI reliability infrastructure for agentic workflows",
};

function Sidebar() {
  return (
    <aside className="w-60 shrink-0 bg-slate-900 border-r border-slate-800 flex flex-col">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600
                          flex items-center justify-center shadow-lg">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="3" stroke="white" strokeWidth="1.5"/>
              <path d="M8 2v2M8 12v2M2 8h2M12 8h2" stroke="white" strokeWidth="1.5"
                    strokeLinecap="round"/>
            </svg>
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-100 leading-none">AgentOps</p>
            <p className="text-[10px] text-slate-500 mt-0.5">Control Plane</p>
          </div>
        </div>
      </div>

      {/* Nav — client component for active-link highlighting */}
      <SidebarNav />

      {/* Footer */}
      <div className="p-4 border-t border-slate-800 space-y-1">
        <p className="text-[10px] text-slate-600 font-medium uppercase tracking-wider">
          Wealthsimple AI Builders
        </p>
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <p className="text-[10px] text-slate-500">All systems operational</p>
        </div>
      </div>
    </aside>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-950 text-slate-100 min-h-screen">
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="flex-1 overflow-auto">{children}</main>
        </div>
      </body>
    </html>
  );
}
