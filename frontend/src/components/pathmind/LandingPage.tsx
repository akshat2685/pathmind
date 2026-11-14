"use client";

import Link from "next/link";

/**
 * PathMind landing page — the public front door at `/`.
 *
 * Shown only when Supabase auth is configured and there is no session
 * (see page.tsx). Signed-in travelers go straight to the journey; when
 * auth is not configured at all the journey renders as before.
 *
 * Same design language as the rest of the app: warm paper, sage, ochre,
 * dusty rose; Bricolage headlines, Source Serif body, Caveat notes.
 * Copy states what the product actually does — no invented claims.
 */
const CHAPTERS = [
  { n: "01", title: "Initiation", text: "You tell us your name. A person record is created — the journey is yours from here." },
  { n: "02", title: "Aspiration", text: "Your stage, your goal, your constraints. A readiness check runs before anything is promised." },
  { n: "03", title: "Verification", text: "Identity is proven before it is taken on trust. Nothing here runs on a claim alone." },
  { n: "04", title: "Aptitude test", text: "A diagnostic on your aspiration — not a generic quiz, a baseline for this goal." },
  { n: "05", title: "Evidence", text: "Real proof: projects, links, files. What you can show matters more than what you say." },
  { n: "06", title: "Assessment", text: "A diagnostic blueprint turns evidence into a baseline — strengths, gaps, nothing invented." },
  { n: "07", title: "Trajectory", text: "Two or three grounded candidate paths. You pick one; the system doesn't pick for you." },
  { n: "08", title: "Roadmap", text: "Progressive locked stages. Each one opens only when the previous phase is verified." },
];

export function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col bg-surface">
      {/* Header */}
      <header className="w-full max-w-6xl mx-auto px-6 py-5 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3">
          <img src="/pathmind-mark.svg" alt="PathMind" className="w-10 h-10" />
          <span className="font-headline-md text-2xl tracking-tight text-secondary font-bold">
            PATHMIND
          </span>
        </Link>
        <nav className="flex items-center gap-5 text-sm">
          <Link
            href="/college/onboarding"
            className="hidden sm:inline text-on-surface-variant hover:text-primary transition-colors"
          >
            College Hub
          </Link>
          <Link
            href="/login"
            className="px-4 py-2 rounded-full border border-primary/50 text-primary font-semibold hover:bg-primary/10 transition-colors"
          >
            Sign in
          </Link>
        </nav>
      </header>

      <main className="flex-1 w-full max-w-6xl mx-auto px-6">
        {/* Hero */}
        <section className="pt-10 pb-14 sm:pt-16 text-center">
          <p className="font-note-handwritten text-2xl text-tertiary mb-3">
            Mindful Learning Path Companion
          </p>
          <h1 className="font-headline-lg text-5xl sm:text-6xl leading-[1.05] text-on-surface max-w-3xl mx-auto">
            Your learning path, drawn for you.
          </h1>
          <p className="font-body-md text-lg text-on-surface-variant leading-relaxed max-w-2xl mx-auto mt-5">
            PathMind turns where you are — your skills, your evidence, your
            constraints — into a grounded path toward where you want to be.
            No generic advice. Every step is verified before the next one
            unlocks.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mt-8">
            <Link
              href="/login"
              className="ink-wash-btn-primary px-7 py-3 text-lg cursor-pointer"
            >
              Begin your journey
            </Link>
            <Link
              href="/college/onboarding"
              className="px-7 py-3 text-lg rounded-full border border-outline-variant/60 text-on-surface hover:border-primary/60 hover:text-primary transition-colors cursor-pointer"
            >
              College Engineering Hub
            </Link>
          </div>
          <p className="font-note-handwritten text-lg text-on-surface-variant mt-6">
            one notebook, every journey — from school to scholar, switcher to founder
          </p>
        </section>

        {/* The eight chapters */}
        <section className="pb-14">
          <h2 className="font-headline-md text-3xl text-on-surface text-center">
            Eight chapters. One journey.
          </h2>
          <p className="text-center text-on-surface-variant mt-2 mb-8">
            The spine of the product — the same path every traveler walks, shaped by their goal.
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {CHAPTERS.map((c) => (
              <div
                key={c.n}
                className="p-5 rounded bg-surface-container-low border border-outline-variant/50"
              >
                <p className="font-note-handwritten text-xl text-tertiary">{c.n}</p>
                <h3 className="font-headline-md text-xl text-on-surface mt-1">{c.title}</h3>
                <p className="text-sm text-on-surface-variant leading-relaxed mt-2">{c.text}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Proof, not promises */}
        <section className="pb-14">
          <h2 className="font-headline-md text-3xl text-on-surface text-center">
            Proof, not promises.
          </h2>
          <div className="grid sm:grid-cols-3 gap-4 mt-8">
            <div className="p-5 rounded bg-surface-container-low border border-outline-variant/50">
              <h3 className="font-headline-md text-xl text-on-surface">Claimed vs proven</h3>
              <p className="text-sm text-on-surface-variant leading-relaxed mt-2">
                A skill counts only when evidence backs it. Claimed skills and
                proven skills are kept apart, in plain sight.
              </p>
            </div>
            <div className="p-5 rounded bg-surface-container-low border border-outline-variant/50">
              <h3 className="font-headline-md text-xl text-on-surface">Verified before trusted</h3>
              <p className="text-sm text-on-surface-variant leading-relaxed mt-2">
                Identity and evidence are checked before guidance is taken on
                trust. The system says what it does not know.
              </p>
            </div>
            <div className="p-5 rounded bg-surface-container-low border border-outline-variant/50">
              <h3 className="font-headline-md text-xl text-on-surface">Unlock on evidence</h3>
              <p className="text-sm text-on-surface-variant leading-relaxed mt-2">
                Roadmap stages stay locked until the previous phase is
                verified. Progress is earned, not asserted.
              </p>
            </div>
          </div>
        </section>

        {/* College slice */}
        <section className="pb-16">
          <div className="p-8 rounded bg-primary/10 border border-primary/30 text-center">
            <p className="font-note-handwritten text-xl text-tertiary">For engineering students</p>
            <h2 className="font-headline-md text-3xl text-on-surface mt-1">
              College Engineering Hub
            </h2>
            <p className="text-on-surface-variant leading-relaxed max-w-xl mx-auto mt-3">
              Syllabus-aware daily plans, previous-year questions, a mentor
              that knows your subjects, and a diagnosis that puts weaknesses
              first. The college slice of PathMind, inside the same app.
            </p>
            <Link
              href="/college/onboarding"
              className="inline-block mt-5 px-7 py-3 text-lg rounded-full bg-primary text-on-primary font-semibold hover:opacity-90 transition-opacity cursor-pointer"
            >
              Start the college path
            </Link>
          </div>
        </section>
      </main>

      <footer className="w-full border-t border-outline-variant/50 py-6 text-center">
        <img src="/pathmind-mark.svg" alt="" aria-hidden="true" className="w-8 h-8 mx-auto mb-2" />
        <p className="text-sm text-on-surface-variant">
          PathMind • Edition 2026 — Mindful Learning Path Companion
        </p>
      </footer>
    </div>
  );
}
