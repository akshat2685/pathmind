"use client";

import { AuthProvider } from "@/lib/contexts/AuthContext";

/**
 * Client-side providers for the app. Kept separate from layout.tsx so the
 * root layout can stay a server component (and keep `metadata`).
 */
export function Providers({ children }: { children: React.ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}
