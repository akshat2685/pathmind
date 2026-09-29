"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { getSupabaseClient } from "@/lib/supabase";

/**
 * AuthGate — wraps protected routes and enforces authentication.
 *
 * On mount, checks for an active Supabase session. If none exists,
 * redirects to /signin. While checking, shows a loading state.
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
      // Auth not configured — cannot verify, redirect to signin
      // which will show the configuration error.
      router.replace("/signin");
      return;
    }

    client.auth.getSession().then(({ data }) => {
      if (data.session) {
        setAuthenticated(true);
      } else {
        router.replace("/signin");
      }
    }).catch(() => {
      // A rejected session check must not leave the "Verifying your session..."
      // spinner hanging forever: treat it as unauthenticated.
      router.replace("/signin");
    });

    // Listen for auth changes (sign out in another tab, token expiry)
    const {
      data: { subscription },
    } = client.auth.onAuthStateChange((_event, session) => {
      if (!session) {
        router.replace("/signin");
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [router]);

  if (authenticated === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0a0e14]">
        <div className="text-center">
          <p className="text-slate-400 mb-2">Verifying your session...</p>
          <div className="w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full animate-spin mx-auto" />
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
