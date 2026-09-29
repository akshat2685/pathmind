"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getSupabaseClient } from "@/lib/supabase";

/**
 * Sign-in / Sign-up page for PATHMIND.
 *
 * Uses Supabase email/password auth. After successful auth, redirects to
 * the main learning-path flow (/). If already authenticated, redirects
 * immediately.
 */
export default function SignInPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const client = getSupabaseClient();
    if (!client) {
      setChecking(false);
      return;
    }
    client.auth.getSession().then(({ data }) => {
      if (data.session) {
        router.replace("/");
      } else {
        setChecking(false);
      }
    }).catch(() => {
      // A rejected session check must still clear the checking state —
      // otherwise this page renders "Loading..." forever.
      setChecking(false);
    });
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    setLoading(true);

    const client = getSupabaseClient();
    if (!client) {
      setError("Authentication is not configured. Please try again later.");
      setLoading(false);
      return;
    }

    try {
      if (mode === "signin") {
        const { error } = await client.auth.signInWithPassword({
          email: email.trim(),
          password,
        });
        if (error) throw error;
        router.replace("/");
      } else {
        const { error } = await client.auth.signUp({
          email: email.trim(),
          password,
        });
        if (error) throw error;
        setMessage(
          "Account created. Please check your email to confirm, then sign in."
        );
        setMode("signin");
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Authentication failed. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0a0e14]">
        <p className="text-slate-400">Loading...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0a0e14] px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">PATHMIND</h1>
          <p className="text-slate-400">Longitudinal Learning Companion</p>
        </div>

        <div className="bg-[#0e1319] border border-[#1c2530] rounded-lg p-8">
          <h2 className="text-xl font-semibold text-white mb-6">
            {mode === "signin" ? "Sign in to continue" : "Create your account"}
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-slate-300 mb-2"
              >
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full px-4 py-3 bg-[#0a0e14] border border-[#1c2530] rounded-md text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
                disabled={loading}
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-slate-300 mb-2"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                minLength={6}
                className="w-full px-4 py-3 bg-[#0a0e14] border border-[#1c2530] rounded-md text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
                disabled={loading}
              />
            </div>

            {error && (
              <div className="px-4 py-3 bg-red-500/10 border border-red-500/30 rounded-md">
                <p className="text-sm text-red-400">{error}</p>
              </div>
            )}

            {message && (
              <div className="px-4 py-3 bg-sky-500/10 border border-sky-500/30 rounded-md">
                <p className="text-sm text-sky-400">{message}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 bg-sky-500 hover:bg-sky-600 disabled:bg-sky-500/50 text-white font-medium rounded-md transition-colors"
            >
              {loading
                ? "Please wait..."
                : mode === "signin"
                  ? "Sign In"
                  : "Create Account"}
            </button>
          </form>

          <div className="mt-6 text-center">
            <button
              onClick={() => {
                setMode(mode === "signin" ? "signup" : "signin");
                setError(null);
                setMessage(null);
              }}
              className="text-sm text-sky-400 hover:text-sky-300"
            >
              {mode === "signin"
                ? "Don't have an account? Sign up"
                : "Already have an account? Sign in"}
            </button>
          </div>
        </div>

        <p className="mt-6 text-center text-xs text-slate-500">
          Your learning journey is private and secured.
        </p>
      </div>
    </div>
  );
}
