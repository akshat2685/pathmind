"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NotificationCenter } from "@/components/pathmind/proactive/NotificationCenter";

export function Sidebar() {
  const pathname = usePathname();

  const navItems = [
    {
      href: "/",
      icon: "history_edu",
      label: "The Initiation",
      sub: "Home & Pathways",
    },
    {
      href: "/onboarding",
      icon: "ink_pen",
      label: "The First Step",
      sub: "Longitudinal Profile",
    },
    {
      href: "/assessment",
      icon: "psychology_alt",
      label: "Counseling Engine",
      sub: "Psychometric Assessment",
    },
    {
      href: "/explorer",
      icon: "alt_route",
      label: "Career Explorer",
      sub: "Trajectory Discovery",
    },
    {
      href: "/journey",
      icon: "map",
      label: "Learning Journey",
      sub: "Progressive Roadmap",
    },
    {
      href: "/memory",
      icon: "memory",
      label: "Memory Vault",
      sub: "Personal Intelligence",
    },
    {
      href: "/evidence",
      icon: "verified",
      label: "Evidence & Mastery",
      sub: "Proof & Progression",
    },
    {
      href: "/readiness",
      icon: "rocket_launch",
      label: "Career Launchpad",
      sub: "Readiness & Opportunities",
    },
    {
      href: "/evolution",
      icon: "timeline",
      label: "Personal Evolution",
      sub: "Longitudinal Model",
    },
    {
      href: "/portfolio",
      icon: "folder_special",
      label: "Artifacts & Portfolio",
      sub: "Real-World Evidence",
    },
    {
      href: "/execution",
      icon: "flag",
      label: "Mission Control",
      sub: "Daily Execution & Action",
    },
    {
      href: "/opportunities",
      icon: "explore",
      label: "Opportunity Navigator",
      sub: "Discovery & Matching",
    },
    {
      href: "/orchestrator",
      icon: "hub",
      label: "Control Tower",
      sub: "Unified Agent Orchestrator",
    },
  ];

  return (
    <nav className="hidden md:flex fixed left-0 top-0 h-full flex-col pt-10 pb-6 w-72 journal-spine z-40 bg-surface border-r-2 border-outline-variant/60">
      {/* Brand Header */}
      <div className="px-6 mb-8 flex items-center justify-between">
        <Link href="/" className="group block">
          <div className="flex items-center gap-2.5">
            <span className="material-symbols-outlined text-secondary text-3xl" style={{ fontVariationSettings: "'FILL' 1" }}>
              auto_stories
            </span>
            <h1 className="font-headline-md text-secondary text-2xl tracking-tight group-hover:text-primary transition-colors">
              PATHMIND
            </h1>
          </div>
          <p className="font-note-handwritten text-on-surface-variant text-xl mt-1">
            Mindful Learning Companion
          </p>
        </Link>
        <NotificationCenter />
      </div>

      {/* Navigation Links */}
      <div className="flex flex-col gap-3 px-4">
        <div className="px-3 text-xs uppercase tracking-wider font-label-md text-on-surface-variant/70 mb-1">
          Journal Chapters
        </div>
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3.5 px-4 py-3 sketch-nav-item transition-all group ${
                isActive ? "active bg-tertiary/10 border-[#333] text-tertiary shadow-sm" : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              <span
                className={`material-symbols-outlined text-2xl transition-transform group-hover:scale-110 ${
                  isActive ? "text-tertiary" : "text-on-surface-variant"
                }`}
                style={isActive ? { fontVariationSettings: "'FILL' 1" } : {}}
              >
                {item.icon}
              </span>
              <div className="flex flex-col">
                <span className="font-headline-sm text-base leading-tight font-medium">
                  {item.label}
                </span>
                <span className="font-note-handwritten text-sm text-on-surface-variant/80">
                  {item.sub}
                </span>
              </div>
            </Link>
          );
        })}
      </div>

      {/* Bottom Scholar Info Card */}
      <div className="mt-auto mx-4 p-4 sketch-border-subtle bg-surface-container-low/90">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full border-2 border-primary bg-primary/10 flex items-center justify-center text-primary font-headline-sm text-lg shrink-0">
            <span className="material-symbols-outlined text-xl">person</span>
          </div>
          <div className="flex flex-col min-w-0">
            <span className="font-headline-sm text-sm font-medium text-on-surface truncate">Student Scholar</span>
            <span className="font-note-handwritten text-sm text-primary font-medium">
              Active Evaluation Mode
            </span>
          </div>
        </div>
      </div>
    </nav>
  );
}
