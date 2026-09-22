"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { supabase } from "@/lib/supabase/client";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSignUp, setIsSignUp] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setMessage(null);

    try {
      if (isSignUp) {
        const { error } = await supabase.auth.signUp({
          email,
          password,
        });
        if (error) throw error;
        setMessage("Welcome! Please check your email to confirm your account before logging in.");
      } else {
        const { error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (error) throw error;
        router.push("/");
      }
    } catch (err: any) {
      setError(err.message || "An error occurred during authentication.");
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async () => {
    if (!email) {
      setError("Please enter your email to reset your password.");
      return;
    }
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email);
      if (error) throw error;
      setMessage("Password reset link sent to your email.");
    } catch (err: any) {
      setError(err.message || "Failed to send reset link.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-between relative overflow-x-hidden selection:bg-[#8ba88e]/40 selection:text-[#252321] font-sans antialiased text-[#252321] bg-[#f7f4e7]">
      {/* Background Notebook Grid Pattern */}
      <div 
        className="fixed inset-0 pointer-events-none opacity-80 -z-20"
        style={{
          backgroundImage: "linear-gradient(to right, rgba(90, 80, 70, 0.05) 1px, transparent 1px), linear-gradient(to bottom, rgba(90, 80, 70, 0.05) 1px, transparent 1px)",
          backgroundSize: "28px 28px"
        }}
      />

      {/* Ambient Watercolor Washes */}
      <div 
        className="fixed top-0 left-0 w-[550px] h-[550px] pointer-events-none -z-10 blur-2xl"
        style={{
          background: "radial-gradient(circle at 30% 40%, rgba(139, 168, 142, 0.35) 0%, rgba(139, 168, 142, 0.08) 55%, transparent 75%)"
        }}
      />
      <div 
        className="fixed -bottom-20 -right-20 w-[650px] h-[650px] pointer-events-none -z-10 blur-3xl"
        style={{
          background: "radial-gradient(circle at 70% 30%, rgba(206, 166, 107, 0.25) 0%, rgba(206, 166, 107, 0.05) 50%, transparent 70%)"
        }}
      />

      {/* TopBar */}
      <header className="w-full max-w-7xl mx-auto px-6 py-6 flex items-center justify-between z-10">
        <Link href="/" className="flex items-center gap-3.5 group">
          <div className="w-10 h-10 rounded-full border-[1.75px] border-[#252321]/80 overflow-hidden bg-[#fdfae7] shadow-sm flex items-center justify-center transition-transform group-hover:-rotate-3">
            <span className="material-symbols-outlined text-[#4a654e] text-2xl">
              auto_stories
            </span>
          </div>
          <div className="flex flex-col">
            <span className="font-bold text-2xl tracking-tight leading-none text-[#252321]">
              Path
            </span>
            <span className="font-note-handwritten text-sm text-[#68635e] tracking-wide -mt-0.5">
              living sketchbook
            </span>
          </div>
        </Link>

        <div className="hidden sm:flex items-center gap-4 text-xs font-serif text-[#68635e] italic">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#8ba88e] border border-[#252321]/40"></span>
            Volume IV • Traveler Registry
          </span>
          <span className="text-[#252321]/30">|</span>
          <span className="text-[#252321] underline decoration-[#252321]/30 decoration-wavy underline-offset-4 cursor-default">
            College Engineering MVP
          </span>
        </div>
      </header>

      {/* Main Content Section */}
      <main className="flex-grow flex items-center justify-center px-4 sm:px-6 lg:px-8 py-6 z-10">
        <div className="w-full max-w-5xl grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center">
          
          {/* LEFT COLUMN: Registered Scholars Directory & Field Note */}
          <section className="lg:col-span-5 flex flex-col justify-center order-2 lg:order-1 space-y-5">
            
            {/* Scholars in Residence Box */}
            <div 
              className="relative bg-[#fdfae7] p-5 sm:p-6 rotate-[-0.8deg] transition-transform hover:rotate-0 duration-300"
              style={{
                border: "1.5px solid #252321",
                borderRadius: "12px 18px 10px 22px / 20px 10px 24px 12px",
                boxShadow: "4px 6px 0px rgba(37, 35, 33, 0.9), 12px 16px 28px rgba(70, 60, 50, 0.08)"
              }}
            >
              {/* Tape Effect */}
              <div className="absolute -top-3.5 left-8 w-32 h-6 bg-amber-100/90 backdrop-blur-sm border border-[#252321]/20 rotate-[-2deg] shadow-xs flex items-center justify-center">
                <span className="text-[10px] tracking-widest uppercase font-serif text-[#252321]/80 font-bold">
                  Scholars in Residence
                </span>
              </div>

              <div className="pt-2">
                <div className="flex items-center justify-between mb-3 border-b border-[#252321]/20 pb-2">
                  <h3 className="font-serif italic font-bold text-base text-[#252321] flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-sm text-[#4a654e]">info</span>
                    Authentication Notice
                  </h3>
                </div>

                <div className="py-4">
                  <p className="text-xs text-[#68635e] font-serif italic mb-4">
                    The traveler registry is now securely managed. To enter your academic journey, please authenticate using your email and password.
                  </p>
                  <p className="text-[11px] text-[#252321]/70">
                    If you are a new scholar, use the &quot;New Traveler&quot; option to register your credentials. A confirmation link will be sent to your email.
                  </p>
                </div>
              </div>

              {/* Footer Note */}
              <div className="mt-4 pt-2.5 border-t border-dashed border-[#252321]/20 flex items-center justify-between text-[11px]">
                <span className="font-note-handwritten text-[#68635e]">
                  Isolated Personal Memory
                </span>
                <span className="font-serif italic text-[10px] text-[#4a654e] font-semibold">
                  Privacy Preserved
                </span>
              </div>
            </div>

            {/* Field Note Card */}
            <div 
              className="relative bg-[#fdfae7] p-4 rotate-[0.6deg]"
              style={{
                border: "1.5px solid #252321",
                borderRadius: "10px 14px 8px 16px / 14px 8px 16px 10px",
                boxShadow: "3px 4px 0px rgba(37, 35, 33, 0.8)"
              }}
            >
              <div className="flex items-start gap-3">
                <span className="material-symbols-outlined text-lg text-[#4a654e] mt-0.5 shrink-0">
                  verified
                </span>
                <div>
                  <h4 className="text-xs font-bold text-[#252321]">
                    5 Engineering Disciplines Covered Deeply
                  </h4>
                  <p className="text-[11px] text-[#68635e] mt-0.5 font-sans leading-relaxed">
                    Mechanical, Electrical, Computer Science, AI, and Civil Engineering with authentic Tier-A university syllabi and verified NPTEL lectures.
                  </p>
                </div>
              </div>
            </div>

          </section>

          {/* RIGHT COLUMN: Authentication & Entry Desk Card */}
          <section className="lg:col-span-7 order-1 lg:order-2">
            <div 
              className="bg-[#fdfae7]/95 p-6 sm:p-10 relative rotate-[0.5deg]"
              style={{
                border: "1.75px solid #252321",
                borderRadius: "255px 15px 225px 15px / 15px 225px 15px 255px",
                boxShadow: "4px 6px 0px rgba(37, 35, 33, 0.9), 12px 16px 28px rgba(70, 60, 50, 0.08)"
              }}
            >
              {/* Header inside the desk card */}
              <div className="mb-8">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#8ba88e]/20 border border-[#8ba88e] text-[#252321] text-xs font-medium mb-3">
                  <span className="material-symbols-outlined text-sm">
                    ink_pen
                  </span>
                  The Scholar’s Desk
                </div>
                <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-[#252321]">
                  Resume your trail.
                </h1>
                <p className="font-serif italic text-[#68635e] mt-1.5 text-base">
                  Step back into your living notebook to sketch thoughts and trace horizons.
                </p>
              </div>

              {error && (
                <div className="mb-4 p-3 border border-[#ba1a1a] bg-[#ffdad6]/40 text-[#93000a] text-xs rounded-md">
                  {error}
                </div>
              )}
              {message && (
                <div className="mb-4 p-3 border border-[#4a654e] bg-[#8ba88e]/20 text-[#252321] text-xs rounded-md">
                  {message}
                </div>
              )}

              {/* Entry Form */}
                <form onSubmit={handleAuth} className="space-y-5">
                  {/* Traveler Email */}
                  <div>
                    <div className="flex justify-between items-baseline mb-1.5">
                      <label className="block text-xs font-bold uppercase tracking-wider text-[#252321]" htmlFor="email">
                        Traveler&apos;s Email
                      </label>
                      <span className="text-xs font-note-handwritten text-[#68635e]">
                        inked identifier
                      </span>
                    </div>
                    <div className="relative">
                      <input
                        id="email"
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="e.g., scholar@university.edu"
                        className="w-full px-3.5 py-3 rounded-md text-sm text-[#252321] placeholder:text-[#68635e]/50 placeholder:font-note-handwritten placeholder:text-lg bg-[#fdfae7]/70 border-[1.5px] border-[#4a453f] focus:bg-white focus:border-[#252321] focus:outline-none focus:shadow-[2px_3px_0px_#252321] transition-all"
                        required
                      />
                      <div className="absolute right-3.5 top-3.5 pointer-events-none text-[#252321]/50">
                        <span className="material-symbols-outlined text-lg">mail</span>
                      </div>
                    </div>
                  </div>
  
                  {/* Password / Secret Seal */}
                  <div>
                    <div className="flex justify-between items-baseline mb-1.5">
                      <label className="block text-xs font-bold uppercase tracking-wider text-[#252321]" htmlFor="password">
                        Keyphrase / Secret Seal
                      </label>
                      <span 
                        onClick={handleResetPassword}
                        className="text-xs font-note-handwritten text-[#a65959] cursor-pointer hover:underline"
                      >
                        forgot keyphrase?
                      </span>
                    </div>
                    <div className="relative">
                      <input
                        id="password"
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="••••••••••••"
                        className="w-full px-3.5 py-3 rounded-md text-sm text-[#252321] placeholder:text-[#252321]/40 tracking-widest bg-[#fdfae7]/70 border-[1.5px] border-[#4a453f] focus:bg-white focus:border-[#252321] focus:outline-none focus:shadow-[2px_3px_0px_#252321] transition-all"
                        required
                      />
                      <div className="absolute right-3.5 top-3.5 pointer-events-none text-[#252321]/50">
                        <span className="material-symbols-outlined text-lg">lock</span>
                      </div>
                    </div>
                  </div>
  
                  {/* Remember Me */}
                  <div className="flex items-center justify-between pt-1">
                    <label className="flex items-center gap-2.5 cursor-pointer select-none group">
                      <input
                        type="checkbox"
                        checked={rememberMe}
                        onChange={(e) => setRememberMe(e.target.checked)}
                        className="w-4 h-4 rounded text-[#252321] border-[#252321] focus:ring-0 cursor-pointer"
                      />
                      <span className="text-xs text-[#252321] group-hover:text-black">
                        Keep me remembered on this parchment
                      </span>
                    </label>
                    <span className="text-[11px] font-serif italic text-[#68635e] hidden sm:inline">
                      Parchment Safe
                    </span>
                  </div>
  
                  {/* Primary Submission Button */}
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full mt-3 py-3.5 px-6 bg-[#252321] hover:bg-[#383430] text-[#fdfae7] font-semibold text-base rounded-md border-2 border-[#252321] transition-all flex items-center justify-center gap-2 group cursor-pointer shadow-[2px_3px_0px_rgba(37,35,33,0.9)] hover:shadow-[3px_5px_0px_rgba(37,35,33,0.9)] active:translate-x-0.5 active:translate-y-0.5"
                  >
                    <span>{loading ? "Verifying Registry..." : (isSignUp ? "Sign Up" : "Enter the Path")}</span>
                    <span className="group-hover:translate-x-1 transition-transform font-serif text-lg leading-none">
                      →
                    </span>
                  </button>
                </form>
  
                {/* Alternative Pathways Divider */}
                <div className="relative my-7 text-center">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-dashed border-[#252321]/30"></div>
                  </div>
                  <span className="relative bg-[#fdfae7] px-3 text-xs font-serif italic text-[#68635e]">
                    or alternate registration
                  </span>
                </div>
  
                {/* Secondary Actions */}
                <div className="flex justify-center">
                  <button
                    type="button"
                    onClick={() => setIsSignUp(!isSignUp)}
                    className="py-2.5 px-4 bg-transparent hover:bg-[#8ba88e]/20 text-[#252321] text-xs font-semibold rounded-md border-[1.5px] border-[#252321]/70 transition-all hover:-translate-y-0.5 flex items-center justify-center gap-1.5 cursor-pointer"
                    style={{
                      borderRadius: "12px 18px 10px 22px / 20px 10px 24px 12px"
                    }}
                  >
                    <span className="material-symbols-outlined text-sm">{isSignUp ? "login" : "person_add"}</span>
                    {isSignUp ? "Already have a journal? Sign In" : "New Traveler? Sign Up"}
                  </button>
                </div>

              {/* Charcoal corner stamp */}
              <div className="absolute bottom-2 right-3 pointer-events-none opacity-25">
                <span className="font-note-handwritten text-[11px] uppercase tracking-widest text-[#252321]">
                  Path-College-Edition-2026
                </span>
              </div>
            </div>
          </section>

        </div>
      </main>

      {/* Footer */}
      <footer className="w-full max-w-5xl mx-auto px-6 py-6 text-center z-10">
        <div className="inline-block border-b border-dashed border-[#252321]/30 pb-1 mb-2">
          <p className="font-serif italic text-sm text-[#423e3b]">
            &quot;Every return is a continuation of the first step.&quot;
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-4 text-xs text-[#68635e]">
          <span>Handcrafted in the Living Sketchbook System</span>
          <span>•</span>
          <span>College Engineering Edition</span>
          <span>•</span>
          <span>AICTE &amp; State University Aligned</span>
        </div>
      </footer>
    </div>
  );
}
