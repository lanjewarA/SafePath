"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AlertTriangle, MapPin, MessageSquare, Navigation } from "lucide-react";

const navigationItems = [
  { href: "/", label: "Routes", icon: MapPin, activeClass: "ring-teal-500/50 bg-teal-950/40 text-teal-300" },
  { href: "/report", label: "Report Hazard", icon: AlertTriangle, activeClass: "ring-amber-500/50 bg-amber-950/40 text-amber-300" },
  { href: "/safewalk", label: "SafeWalk", icon: Navigation, activeClass: "ring-teal-500/50 bg-teal-950/40 text-teal-300" },
  { href: "/chat", label: "Copilot", icon: MessageSquare, activeClass: "ring-pink-500/50 bg-pink-950/40 text-pink-300" },
];

export default function AppNavigation() {
  const pathname = usePathname();

  return (
    <nav aria-label="Main navigation" className="flex items-center gap-2 sm:gap-4 text-sm font-medium text-slate-300 relative">
      {navigationItems.map(({ href, label, icon: Icon, activeClass }) => {
        const isActive = pathname === href;
        return (
          <Link
            key={href}
            href={href}
            aria-label={label}
            aria-current={isActive ? "page" : undefined}
            className={`flex items-center gap-1.5 rounded-md px-2 py-1.5 transition-colors hover:text-teal-300 ${
              isActive ? `ring-2 ${activeClass}` : ""
            }`}
          >
            <Icon className="w-4 h-4" />
            <span className="hidden sm:inline">{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
