"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { useRouter, usePathname } from "next/navigation";
import type { User, Session } from "@supabase/supabase-js";
import { getSupabaseClient } from "./supabase";

interface AuthContextValue {
  user: User | null;
  session: Session | null;
  loading: boolean;
  /** Returns true when the project requires email confirmation (no session yet). */
  signUp: (email: string, password: string) => Promise<{ needsConfirmation: boolean }>;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  resendConfirmation: (email: string) => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/** Routes that don't require a session. Everything else redirects to /login. */
const PUBLIC_ROUTES = ["/login"];

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const client = getSupabaseClient();
    if (!client) {
      setLoading(false);
      return;
    }
    let mounted = true;
    client.auth.getSession().then(({ data }) => {
      if (!mounted) return;
      setSession(data.session);
      setUser(data.session?.user ?? null);
      setLoading(false);
    }).catch(() => {
      // A rejected session read must still clear the loading state —
      // otherwise the app hangs on a spinner forever.
      if (!mounted) return;
      setLoading(false);
    });
    const { data: listener } = client.auth.onAuthStateChange((_event, newSession) => {
      if (!mounted) return;
      setSession(newSession);
      setUser(newSession?.user ?? null);
    });
    return () => {
      mounted = false;
      listener.subscription.unsubscribe();
    };
  }, []);

  // Route guards: unauthenticated -> /login, authenticated on /login -> /onboarding
  useEffect(() => {
    if (loading) return;
    const isPublic = PUBLIC_ROUTES.some(
      (r) => pathname === r || pathname?.startsWith(r + "/")
    );
    if (!user && !isPublic) {
      router.replace("/login");
    } else if (user && pathname === "/login") {
      router.replace("/onboarding");
    }
  }, [user, loading, pathname, router]);

  const signUp = useCallback(async (email: string, password: string) => {
    const client = getSupabaseClient();
    if (!client) throw new Error("Authentication is not configured.");
    const { data, error } = await client.auth.signUp({ email, password });
    if (error) throw error;
    // needsConfirmation is true only when the project requires email
    // confirmation (no session returned). When autoconfirm is on, the
    // traveler is signed in immediately.
    return { needsConfirmation: !data.session };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const client = getSupabaseClient();
    if (!client) throw new Error("Authentication is not configured.");
    const { error } = await client.auth.signInWithPassword({ email, password });
    if (error) throw error;
  }, []);

  const signOut = useCallback(async () => {
    const client = getSupabaseClient();
    try {
      if (client) {
        await client.auth.signOut();
      }
    } finally {
      // Local cleanup + redirect must ALWAYS run, even if the server-side
      // revocation rejects (network error, etc.).
      if (typeof window !== "undefined") {
        // Clear local scholar identity so the next sign-in starts fresh.
        for (const k of [
          "pathmind_person_id",
          "pathmind_user_name",
          "pathmind_user_identity",
          "pathmind_user_goal",
          "pathmind_user_evidence",
        ]) {
          localStorage.removeItem(k);
        }
      }
      router.replace("/login");
    }
  }, [router]);

  const resendConfirmation = useCallback(async (email: string) => {
    const client = getSupabaseClient();
    if (!client) throw new Error("Authentication is not configured.");
    const { error } = await client.auth.resend({ type: "signup", email });
    if (error) throw error;
  }, []);

  const resetPassword = useCallback(async (email: string) => {
    const client = getSupabaseClient();
    if (!client) throw new Error("Authentication is not configured.");
    const { error } = await client.auth.resetPasswordForEmail(email);
    if (error) throw error;
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        loading,
        signUp,
        signIn,
        signOut,
        resendConfirmation,
        resetPassword,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
