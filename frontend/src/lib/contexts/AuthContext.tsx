"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { User, Session } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase/client";
import { useRouter, usePathname } from "next/navigation";

interface AuthContextType {
  user: User | null;
  session: Session | null;
  isLoading: boolean;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  session: null,
  isLoading: true,
  signOut: async () => {},
});

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const {
          data: { session },
        } = await supabase.auth.getSession();
        setSession(session);
        setUser(session?.user ?? null);
      } catch (err) {
        // Never leave the app wedged on the loading screen: treat auth as
        // unauthenticated and let the route guards redirect to /login.
        console.error("[auth] getSession failed:", err);
        setSession(null);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setUser(session?.user ?? null);
      setIsLoading(false);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  // Protected route logic
  useEffect(() => {
    if (!isLoading) {
      const isAuthRoute = pathname === "/login";
      if (!user && !isAuthRoute) {
        router.push("/login");
      // NOTE: the /login → / redirect below is deliberately NOT gated on
      // user.email_confirmed_at. Supabase runs with mailer_autoconfirm=true,
      // so no confirmation email is ever sent and email_confirmed_at can stay
      // null even for valid sessions — gating on it strands users in a
      // redirect race. Session presence alone is the source of truth.
      } else if (user && isAuthRoute) {
        router.push("/");
      }
    }
  }, [user, isLoading, pathname, router]);

  const signOut = async () => {
    await supabase.auth.signOut();
    router.push("/login");
  };

  return (
    <AuthContext.Provider value={{ user, session, isLoading, signOut }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
