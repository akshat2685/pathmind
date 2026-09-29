"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth-context";

/**
 * PATHMIND sign-in / sign-up.
 *
 * Works with the project's Supabase Auth configuration either way:
 * - Email confirmation OFF (mailer_autoconfirm): sign-up returns a session
 *   immediately and the traveler goes straight in — no email is promised.
 * - Email confirmation ON: the traveler is told to check their inbox, with
 *   a "resend confirmation email" affordance.
 */
export default function LoginPage() {
  const { signUp, signIn, resendConfirmation, resetPassword } = useAuth();
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [showResend, setShowResend] = useState(false);

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setMessage(null);
    setShowResend(false);
    try {
      if (isSignUp) {
        const { needsConfirmation } = await signUp(email, password);
        if (needsConfirmation) {
          // A session is returned only when confirmation is required.
          setMessage("Welcome! Please check your email to confirm your account before logging in.");
          setShowResend(true);
        } else {
          setMessage("Welcome! You are signed in.");
        }
        // The AuthProvider's route guard moves the traveler to /onboarding
        // as soon as the session is active.
      } else {
        await signIn(email, password);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Something went wrong.";
      setError(msg);
      // An unconfirmed account trying to sign in gets a clear path forward.
      if (/confirm|verified|not confirmed/i.test(msg)) setShowResend(true);
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    if (!email) {
      setError("Enter your email address first, then resend the confirmation.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await resendConfirmation(email);
      setMessage("Confirmation email sent — check your inbox (and spam folder).");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not resend the email.");
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async () => {
    if (!email) {
      setError("Enter your email address first, then reset your password.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await resetPassword(email);
      setMessage("Password reset email sent — check your inbox.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not send the reset email.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1
            className="text-4xl font-bold tracking-tight text-[#1c1c11]"
            style={{ fontFamily: "var(--font-bricolage), sans-serif" }}
          >
            PATHMIND
          </h1>
          <p
            className="mt-2 text-xl text-[#4a654e]"
            style={{ fontFamily: "var(--font-caveat), cursive" }}
          >
            {isSignUp ? "begin your journey, traveler" : "welcome back, traveler"}
          </p>
        </div>

        <div className="rounded-2xl border-2 border-[#333333]/70 bg-[#fdfae7]/80 p-6 shadow-[4px_5px_0_rgba(61,52,48,0.15)]">
          <div className="flex rounded-full border-2 border-[#333333]/60 overflow-hidden mb-6">
            <button
              type="button"
              onClick={() => { setIsSignUp(false); setError(null); setMessage(null); setShowResend(false); }}
              className={`flex-1 py-2 text-sm font-semibold transition-colors ${!isSignUp ? "bg-[#4a654e] text-white" : "text-[#1c1c11]"}`}
            >
              Sign in
            </button>
            <button
              type="button"
              onClick={() => { setIsSignUp(true); setError(null); setMessage(null); setShowResend(false); }}
              className={`flex-1 py-2 text-sm font-semibold transition-colors ${isSignUp ? "bg-[#4a654e] text-white" : "text-[#1c1c11]"}`}
            >
              New traveler
            </button>
          </div>

          <form onSubmit={handleAuth} className="space-y-5">
            <div>
              <label htmlFor="email" className="block text-sm font-semibold text-[#1c1c11] mb-1">
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="hand-drawn-input w-full px-1 py-2"
                autoComplete="email"
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-sm font-semibold text-[#1c1c11] mb-1">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={isSignUp ? "at least 6 characters" : "your password"}
                className="hand-drawn-input w-full px-1 py-2"
                autoComplete={isSignUp ? "new-password" : "current-password"}
              />
            </div>

            {error && (
              <p className="text-sm font-medium text-[#8b4c50] bg-[#8b4c50]/10 border border-[#8b4c50]/40 rounded-lg px-3 py-2">
                {error}
              </p>
            )}
            {message && (
              <p className="text-sm font-medium text-[#4a654e] bg-[#4a654e]/10 border border-[#4a654e]/40 rounded-lg px-3 py-2">
                {message}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="ink-wash-btn-primary w-full py-3 disabled:opacity-60"
            >
              {loading ? "One moment…" : isSignUp ? "Begin the journey" : "Continue the journey"}
            </button>
          </form>

          <div className="mt-4 flex flex-col gap-2 text-center">
            {showResend && (
              <button
                type="button"
                onClick={handleResend}
                disabled={loading}
                className="ink-wash-btn w-full py-2 text-sm disabled:opacity-60"
              >
                Resend confirmation email
              </button>
            )}
            {!isSignUp && (
              <button
                type="button"
                onClick={handleResetPassword}
                disabled={loading}
                className="text-sm text-[#4a654e] underline underline-offset-2 hover:text-[#3b523e] disabled:opacity-60"
              >
                Forgot your password?
              </button>
            )}
          </div>
        </div>

        <p
          className="mt-6 text-center text-lg text-[#68635e]"
          style={{ fontFamily: "var(--font-caveat), cursive" }}
        >
          your journey, your pace — pick up right where you left off
        </p>
      </div>
    </main>
  );
}
