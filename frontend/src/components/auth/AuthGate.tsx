"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { getSupabaseClient } from "@/lib/supabase";

/**
 * AuthGate — wraps protected routes and enforces authentication.
 *
 * On mount, checks for an active Supabase session. If none exists,
 * redirects to /login. While checking, shows a loading state.
 *
 * Usage: wrap any page that requires authentication:
 *   <AuthGate><YourPageContent /></AuthGate>
 */
export function AuthGate({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    const client = getSupabaseClient();
    if (!client) {
      // Auth not configured — cannot verify, redirect to login
      // which will show the configuration error.
      router.replace("/login");
      return;
    }

    client.auth.getSession().then(({ data }) => {
      if (data.session) {
        setAuthenticated(true);
      } else {
        router.replace("/login");
      }
    }).catch(() => {
      // A rejected session check must not leave the "Verifying your session..."
      // spinner hanging forever: treat it as unauthenticated.
      router.replace("/login");
    });

    // Listen for auth changes (sign out in another tab, token expiry)
    const {
      data: { subscription },
    } = client.auth.onAuthStateChange((_event, session) => {
      if (!session) {
        router.replace("/login");
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [router]);

  if (authenticated === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface">
        <div className="text-center">
          <p className="font-note-handwritten text-lg text-on-surface-variant mb-2">Verifying your session...</p>
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
