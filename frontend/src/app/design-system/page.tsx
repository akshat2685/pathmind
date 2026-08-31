import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";

export const metadata = {
  title: "Living Sketchbook Design System — PATHMIND",
  description: "Tactile analog design specifications and tokens.",
};

export default function DesignSystemPage() {
  const colors = [
    { name: "Primary (Sage Green)", hex: "#4a654e", role: "Growth, progress, primary actions" },
    { name: "Secondary (Warm Ochre)", hex: "#7d562d", role: "Academic heritage, highlights" },
    { name: "Tertiary (Dusty Rose)", hex: "#8b4c50", role: "Interactive accents, gentle nudges" },
    { name: "Parchment Surface", hex: "#fdfae7", role: "Tactile cream base surface" },
    { name: "Text (Espresso)", hex: "#1c1c11", role: "Analog ink typography" },
  ];

  return (
    <div className="flex min-h-screen bg-surface">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 md:ml-72">
        <TopBar />
        <main className="flex-1 p-6 md:p-12 relative z-10 max-w-5xl">
          
          <div className="mb-10">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 sketchy-chip text-tertiary mb-3">
              <span className="material-symbols-outlined text-lg" style={{ fontVariationSettings: "'FILL' 1" }}>
                palette
              </span>
              <span className="font-note-handwritten text-xl font-medium">Design System</span>
            </div>
            <h1 className="font-headline-lg text-4xl text-on-surface mb-2">
              Living Sketchbook System
            </h1>
            <p className="font-body-md text-lg text-on-surface-variant max-w-2xl">
              An analog, tactile journal aesthetic created to evoke mindfulness, reduce cognitive strain, and celebrate human curiosity.
            </p>
          </div>

          {/* Color Palette */}
          <div className="sketch-border p-8 mb-10 bg-surface-container-low/90">
            <h2 className="font-headline-sm text-2xl text-on-surface mb-6">Physiological Palette</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              {colors.map((c) => (
                <div key={c.name} className="p-4 rounded-xl border border-outline-variant/50 bg-surface-container/40 flex flex-col gap-2">
                  <div 
                    className="h-14 w-full rounded-lg border border-black/10 shadow-inner"
                    style={{ backgroundColor: c.hex }}
                  />
                  <div>
                    <span className="font-headline-sm text-base text-on-surface block font-medium">{c.name}</span>
                    <span className="font-mono text-xs text-on-surface-variant">{c.hex}</span>
                    <p className="font-body-md text-xs text-on-surface-variant/80 mt-1">{c.role}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Typography Pairings */}
          <div className="sketch-border p-8 mb-10 bg-surface-container-low/90 space-y-6">
            <h2 className="font-headline-sm text-2xl text-on-surface mb-4">Typography Quartet</h2>
            
            <div className="p-4 bg-surface-container/40 rounded-xl border border-outline-variant/40">
              <span className="font-label-md text-xs uppercase tracking-wider text-outline block mb-1">Headline Display</span>
              <p className="font-headline-lg text-3xl text-secondary">Bricolage Grotesque — Expressive &amp; Hand-cut</p>
            </div>

            <div className="p-4 bg-surface-container/40 rounded-xl border border-outline-variant/40">
              <span className="font-label-md text-xs uppercase tracking-wider text-outline block mb-1">Academic Body Text</span>
              <p className="font-body-md text-lg text-on-surface">Source Serif 4 — Deep focus literary serif for longitudinal educational content.</p>
            </div>

            <div className="p-4 bg-surface-container/40 rounded-xl border border-outline-variant/40">
              <span className="font-label-md text-xs uppercase tracking-wider text-outline block mb-1">Handwritten Marginalia</span>
              <p className="font-note-handwritten text-3xl text-tertiary">Caveat — Personal tutor notes in the journal margins...</p>
            </div>

            <div className="p-4 bg-surface-container/40 rounded-xl border border-outline-variant/40">
              <span className="font-label-md text-xs uppercase tracking-wider text-outline block mb-1">UI Metadata</span>
              <p className="font-label-md text-sm text-on-surface-variant">Be Vietnam Pro — Clean, contemporary contrast for operational metadata.</p>
            </div>
          </div>

          {/* Interactive UI Elements */}
          <div className="sketch-border p-8 mb-10 bg-surface-container-low/90">
            <h2 className="font-headline-sm text-2xl text-on-surface mb-6">Tactile Components</h2>
            <div className="flex flex-wrap items-center gap-6">
              <button type="button" className="ink-wash-btn px-6 py-2 text-xl">
                Ink Wash Button
              </button>
              <button type="button" className="ink-wash-btn-primary px-8 py-2 text-xl">
                Primary Hand-Stamp
              </button>
              <span className="font-note-handwritten text-xl text-primary sketchy-chip px-4 py-1">
                Washi Tape Chip
              </span>
              <span className="font-note-handwritten text-xl text-tertiary sketchy-chip px-4 py-1 rotate-2">
                Marginalia Tag
              </span>
            </div>
          </div>

        </main>
      </div>
    </div>
  );
}
