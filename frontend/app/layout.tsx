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
      <body className="flex flex-col min-h-screen bg-slate-900 text-slate-100">
        {/* Navigation Bar */}
        <header className="bg-slate-800/90 backdrop-blur border-b border-slate-700 sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2 font-bold text-xl text-emerald-400">
              <Shield className="w-6 h-6 text-emerald-400" />
              <span>SafePath <span className="text-slate-100">AI</span></span>
              <span className="text-xs bg-emerald-950 text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded-full font-mono">
                West India
              </span>
            </Link>

            <nav className="flex items-center gap-4 text-sm font-medium">
              <Link href="/" className="flex items-center gap-1.5 hover:text-emerald-400 transition-colors">
                <MapPin className="w-4 h-4" /> Routes
              </Link>
              <Link href="/report" className="flex items-center gap-1.5 hover:text-emerald-400 transition-colors">
                <AlertTriangle className="w-4 h-4 text-amber-400" /> Report Hazard
              </Link>
              <Link href="/safewalk" className="flex items-center gap-1.5 hover:text-emerald-400 transition-colors">
                <Navigation className="w-4 h-4 text-blue-400" /> SafeWalk
              </Link>
              <Link href="/chat" className="flex items-center gap-1.5 hover:text-emerald-400 transition-colors">
                <MessageSquare className="w-4 h-4 text-purple-400" /> Copilot
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

