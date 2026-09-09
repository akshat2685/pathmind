"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { NotificationCenter } from "@/components/pathmind/proactive/NotificationCenter";

export function TopBar() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const pathname = usePathname();

  const navItems = [
    { href: "/", icon: "history_edu", label: "The Initiation", sub: "Home & Pathways" },
    { href: "/onboarding", icon: "ink_pen", label: "The First Step", sub: "Longitudinal Profile" },
    { href: "/assessment", icon: "psychology_alt", label: "Counseling Engine", sub: "Psychometric Assessment" },
    { href: "/explorer", icon: "alt_route", label: "Career Explorer", sub: "Trajectory Discovery" },
    { href: "/journey", icon: "map", label: "Learning Journey", sub: "Progressive Roadmap" },
    { href: "/memory", icon: "memory", label: "Memory Vault", sub: "Personal Intelligence" },
    { href: "/evidence", icon: "verified", label: "Evidence & Mastery", sub: "Proof & Progression" },
    { href: "/readiness", icon: "rocket_launch", label: "Career Launchpad", sub: "Readiness & Opportunities" },
    { href: "/evolution", icon: "timeline", label: "Personal Evolution", sub: "Longitudinal Model" },
    { href: "/portfolio", icon: "folder_special", label: "Artifacts & Portfolio", sub: "Real-World Evidence" },
    { href: "/execution", icon: "flag", label: "Mission Control", sub: "Daily Execution & Action" },
    { href: "/opportunities", icon: "explore", label: "Opportunity Navigator", sub: "Discovery & Matching" },
    { href: "/orchestrator", icon: "hub", label: "Control Tower", sub: "Unified Agent Orchestrator" },
  ];

  return (
    <>
      <header className="md:hidden flex justify-between items-center px-4 py-3 w-full fixed top-0 left-0 bg-surface-container-low/95 backdrop-blur-md border-b-2 border-outline-variant shadow-sm z-40">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            aria-label={isMenuOpen ? "Close navigation menu" : "Open navigation menu"}
            aria-expanded={isMenuOpen}
            className="p-2 -ml-1 text-on-surface hover:text-primary transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center cursor-pointer focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none"
          >
            <span className="material-symbols-outlined text-2xl">
              {isMenuOpen ? "close" : "menu"}
            </span>
          </button>
          <Link href="/" className="flex items-center gap-2" aria-label="PATHMIND Homepage">
            <span className="material-symbols-outlined text-secondary text-2xl" style={{ fontVariationSettings: "'FILL' 1" }}>
              auto_stories
            </span>
            <span className="font-headline-lg text-xl italic text-secondary tracking-tight">
              Pathmind
            </span>
          </Link>
        </div>
        <div className="flex items-center gap-2">
          <NotificationCenter />
          <Link
            href="/onboarding"
            aria-label="Onboarding: Longitudinal Profile"
            className="text-primary hover:text-tertiary transition-colors min-w-[40px] min-h-[40px] flex items-center justify-center"
            title="Onboarding"
          >
            <span className="material-symbols-outlined text-2xl">menu_book</span>
          </Link>
          <Link
            href="/assessment"
            aria-label="Counseling Engine Assessment"
            className="text-primary hover:text-tertiary transition-colors min-w-[40px] min-h-[40px] flex items-center justify-center"
            title="Assessment"
          >
            <span className="material-symbols-outlined text-2xl">ink_pen</span>
          </Link>
        </div>
      </header>

      {/* Mobile Slide-over Drawer */}
      {isMenuOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex bg-black/60 backdrop-blur-xs animate-in fade-in">
          <div className="bg-surface border-r border-outline w-4/5 max-w-xs h-full flex flex-col pt-4 pb-6 px-4 shadow-2xl animate-in slide-in-from-left duration-200 overflow-y-auto">
            <div className="flex items-center justify-between pb-4 border-b border-outline/30 mb-3">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-secondary text-2xl" style={{ fontVariationSettings: "'FILL' 1" }}>
                  auto_stories
                </span>
                <span className="font-headline-md text-secondary text-lg font-bold">PATHMIND</span>
              </div>
              <button
                onClick={() => setIsMenuOpen(false)}
                aria-label="Close navigation menu"
                className="p-2 text-on-surface-variant hover:text-on-surface min-w-[44px] min-h-[44px] flex items-center justify-center cursor-pointer"
              >
                <span className="material-symbols-outlined text-2xl">close</span>
              </button>
            </div>

            <div className="text-[11px] uppercase tracking-wider font-label-md text-on-surface-variant/70 px-2 mb-2">
              Journal Chapters
            </div>

            <div className="flex flex-col gap-1.5 flex-1">
              {navItems.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setIsMenuOpen(false)}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all ${
                      isActive
                        ? "bg-tertiary/15 text-tertiary font-bold"
                        : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container"
                    }`}
                  >
                    <span
                      className="material-symbols-outlined text-xl shrink-0"
                      style={isActive ? { fontVariationSettings: "'FILL' 1" } : {}}
                    >
                      {item.icon}
                    </span>
                    <div className="flex flex-col min-w-0">
                      <span className="text-sm font-medium leading-tight truncate">{item.label}</span>
                      <span className="font-note-handwritten text-xs opacity-80 truncate">{item.sub}</span>
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>
          <div className="flex-1" onClick={() => setIsMenuOpen(false)} />
        </div>
      )}
    </>
  );
}
