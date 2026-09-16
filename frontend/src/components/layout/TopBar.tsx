"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { NotificationCenter } from "@/components/pathmind/proactive/NotificationCenter";

interface TopBarProps {
  scholarName?: string | null;
  personId?: string | null;
}

export function TopBar({ scholarName: propName, personId: propId }: TopBarProps = {}) {
  const [scholarName, setScholarName] = useState<string | null>(propName || null);
  const [personId, setPersonId] = useState<string | null>(propId || null);

  useEffect(() => {
    if (propName !== undefined) setScholarName(propName);
    if (propId !== undefined) setPersonId(propId);
  }, [propName, propId]);

  useEffect(() => {
    const updateScholarInfo = () => {
      if (typeof window !== "undefined") {
        const storedName = localStorage.getItem("pathmind_user_name");
        const storedId = localStorage.getItem("pathmind_person_id");
        if (!propName) setScholarName(storedName);
        if (!propId) setPersonId(storedId);
      }
    };

    updateScholarInfo();
    window.addEventListener("storage", updateScholarInfo);
    window.addEventListener("pathmind_identity_changed", updateScholarInfo);
    return () => {
      window.removeEventListener("storage", updateScholarInfo);
      window.removeEventListener("pathmind_identity_changed", updateScholarInfo);
    };
  }, [propName, propId]);

  const handleReset = () => {
    if (typeof window !== "undefined") {
      if (confirm("Reset current journey and start fresh with a new scholar identity?")) {
        localStorage.removeItem("pathmind_person_id");
        localStorage.removeItem("pathmind_user_name");
        localStorage.removeItem("pathmind_user_identity");
        localStorage.removeItem("pathmind_user_goal");
        localStorage.removeItem("pathmind_user_evidence");
        window.location.reload();
      }
    }
  };

  return (
    <header className="w-full flex justify-between items-center px-4 sm:px-8 py-3.5 bg-surface-container-low/90 backdrop-blur-md border-b border-outline/30 sticky top-0 z-40">
      <div className="flex items-center gap-3">
        <Link href="/" className="flex items-center gap-2.5 group" aria-label="PATHMIND Homepage">
          <div className="w-9 h-9 rounded-full bg-secondary/15 text-secondary border border-secondary/30 flex items-center justify-center group-hover:scale-105 transition-transform">
            <span className="material-symbols-outlined text-xl" style={{ fontVariationSettings: "'FILL' 1" }}>
              auto_stories
            </span>
          </div>
          <div className="flex flex-col">
            <span className="font-headline-md text-xl tracking-tight text-secondary font-bold">
              PATHMIND
            </span>
            <span className="font-note-handwritten text-xs text-on-surface-variant hidden sm:inline">
              Longitudinal Learning Companion
            </span>
          </div>
        </Link>
      </div>

      <div className="flex items-center gap-3 sm:gap-4">
        {scholarName && (
          <div className="inline-flex items-center gap-2 px-3 py-1 sketchy-chip bg-primary-fixed/30 border border-primary/40 text-on-surface text-sm">
            <span className="material-symbols-outlined text-primary text-base" style={{ fontVariationSettings: "'FILL' 1" }}>
              history_edu
            </span>
            <span className="font-note-handwritten text-base font-semibold truncate max-w-[140px] sm:max-w-[200px]">
              {scholarName}
            </span>
          </div>
        )}

        <div className="hidden md:inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-700 dark:text-emerald-300 text-xs font-medium">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <span>Ready</span>
        </div>

        {personId && (
          <button
            onClick={handleReset}
            title="Start fresh with a new scholar identity"
            className="text-xs text-on-surface-variant hover:text-error transition-colors px-2.5 py-1 rounded border border-outline-variant/40 hover:border-error/40 flex items-center gap-1 cursor-pointer font-note-handwritten text-sm"
          >
            <span className="material-symbols-outlined text-sm">restart_alt</span>
            <span className="hidden sm:inline">Reset</span>
          </button>
        )}

        <NotificationCenter />
      </div>
    </header>
  );
}
