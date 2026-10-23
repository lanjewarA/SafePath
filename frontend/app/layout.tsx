import "./globals.css";
import Link from "next/link";
import { Shield } from "lucide-react";
import AppNavigation from "@/components/AppNavigation";

export const metadata = {
  title: "SafePath AI — Safety Routing",
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
            </Link>

            <AppNavigation />
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
