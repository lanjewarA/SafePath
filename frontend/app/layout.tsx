import "./globals.css";
import Link from "next/link";
import { Shield, MapPin, AlertTriangle, MessageSquare, Navigation } from "lucide-react";

export const metadata = {
  title: "SafePath AI — West India Safety Routing",
  description: "Urban Safety Routing & Safety Copilot powered by GNN risk modeling and Gemini LLM verification.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="flex flex-col min-h-screen text-slate-200">
        {/* Navigation Bar */}
        <header className="glass-panel-strong nav-accent sticky top-0 z-50 rounded-b-xl border-x-0 border-t-0">
          <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2 font-bold text-xl text-teal-300">
              <Shield className="w-6 h-6 text-teal-400" />
              <span>SafePath <span className="text-slate-100">AI</span></span>
              <span className="text-xs bg-teal-950/60 text-teal-300 border border-teal-500/30 px-2 py-0.5 rounded-full font-mono">
                West India
              </span>
            </Link>

            <nav className="flex items-center gap-4 text-sm font-medium text-slate-300">
              <Link href="/" className="flex items-center gap-1.5 hover:text-teal-300 transition-colors">
                <MapPin className="w-4 h-4" /> Routes
              </Link>
              <Link href="/report" className="flex items-center gap-1.5 hover:text-teal-300 transition-colors">
                <AlertTriangle className="w-4 h-4 text-amber-400" /> Report Hazard
              </Link>
              <Link href="/safewalk" className="flex items-center gap-1.5 hover:text-teal-300 transition-colors">
                <Navigation className="w-4 h-4 text-teal-400" /> SafeWalk
              </Link>
              <Link href="/chat" className="flex items-center gap-1.5 hover:text-teal-300 transition-colors">
                <MessageSquare className="w-4 h-4 text-pink-400" /> Copilot
              </Link>
            </nav>
          </div>
        </header>

        {/* Page Body */}
        <main className="flex-1 flex flex-col">
          {children}
        </main>
      </body>
    </html>
  );
}
