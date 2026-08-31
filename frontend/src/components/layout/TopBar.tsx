"use client";

import Link from "next/link";

export function TopBar() {
  return (
    <header className="md:hidden flex justify-between items-center px-6 py-4 w-full fixed top-0 left-0 bg-surface-container-low/95 backdrop-blur-md border-b-2 border-outline-variant shadow-sm z-40">
      <Link href="/" className="flex items-center gap-2">
        <span className="material-symbols-outlined text-secondary text-2xl" style={{ fontVariationSettings: "'FILL' 1" }}>
          auto_stories
        </span>
        <h1 className="font-headline-lg text-2xl italic text-secondary tracking-tight">
          Pathmind
        </h1>
      </Link>
      <div className="flex gap-3">
        <Link
          href="/onboarding"
          className="text-primary hover:text-tertiary transition-colors duration-200"
          title="Onboarding"
        >
          <span className="material-symbols-outlined text-2xl">menu_book</span>
        </Link>
        <Link
          href="/assessment"
          className="text-primary hover:text-tertiary transition-colors duration-200"
          title="Assessment"
        >
          <span className="material-symbols-outlined text-2xl">ink_pen</span>
        </Link>
      </div>
    </header>
  );
}
