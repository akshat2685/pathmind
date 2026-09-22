"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CollegeDashboard } from "@/components/pathmind/college/CollegeDashboard";
import { useAuth } from "@/lib/contexts/AuthContext";

export default function Home() {
  const router = useRouter();
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const { user, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading) {
      if (!user) {
        router.push("/login");
      } else {
        setIsAuthenticated(true);
      }
      setCheckingAuth(false);
    }
  }, [user, isLoading, router]);

  if (checkingAuth) {
    return (
      <div className="min-h-screen bg-[#f7f4e7] flex items-center justify-center font-sans text-xs font-serif italic text-[#68635e]">
        Opening the Scholar's Desk...
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return <CollegeDashboard />;
}
