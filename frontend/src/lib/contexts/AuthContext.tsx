"use client";

import { createContext, useContext, type ReactNode } from "react";
import { useAuth as useMainAuth } from "@/lib/auth-context";
import type { User, Session } from "@supabase/supabase-js";

/**
 * College-slice auth context — adapter, not a second auth system.
 *
 * The unified app has ONE auth provider (main's @/lib/auth-context, mounted
 * in the root layout). College components import useAuth from here, so this
 * module re-exposes the main session in the college shape
 * ({ user, session, isLoading, signOut }). It runs no session listener and
 * no route guard of its own: AuthGate + the main AuthProvider own guarding.
 */
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

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const { user, session, loading, signOut } = useMainAuth();
  return (
    <AuthContext.Provider value={{ user, session, isLoading: loading, signOut }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
