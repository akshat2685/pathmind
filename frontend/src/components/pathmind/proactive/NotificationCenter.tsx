"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Bell,
  X,
  CheckCircle2,
  ArrowRight,
  ShieldCheck
} from "lucide-react";

interface InterventionItem {
  intervention_id: string;
  person_id: string;
  event_id: string;
  type: string;
  priority: string;
  title: string;
  what_happened: string;
  why_it_matters: string;
  what_should_i_do: string;
  what_happens_if_ignored: string;
  action_url: string;
  status: string;
  created_at: string;
}

interface NotificationPrefs {
  enable_opportunity_alerts: boolean;
  enable_mastery_alerts: boolean;
  enable_blocker_alerts: boolean;
  enable_reinforcement_alerts: boolean;
  quiet_hours_enabled: boolean;
}

export function NotificationCenter() {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"ALERTS" | "PREFS">("ALERTS");
  const [interventions, setInterventions] = useState<InterventionItem[]>([]);
  const [prefs, setPrefs] = useState<NotificationPrefs>({
    enable_opportunity_alerts: true,
    enable_mastery_alerts: true,
    enable_blocker_alerts: true,
    enable_reinforcement_alerts: true,
    quiet_hours_enabled: false
  });

  const fetchInterventions = useCallback(async () => {
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      const res = await fetch(`${baseUrl}/api/proactive/interventions`, {
        headers: { "X-Person-ID": personId }
      });
      if (res.ok) {
        const data: InterventionItem[] = await res.json();
        setInterventions(data);
      }
    } catch (err) {
      console.error(err);
    }
  }, []);

  const fetchPrefs = useCallback(async () => {
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      const res = await fetch(`${baseUrl}/api/proactive/preferences`, {
        headers: { "X-Person-ID": personId }
      });
      if (res.ok) {
        const data: NotificationPrefs = await res.json();
        setPrefs(data);
      }
    } catch (err) {
      console.error(err);
    }
  }, []);

  useEffect(() => {
    fetchInterventions();
    fetchPrefs();
  }, [fetchInterventions, fetchPrefs]);

  const handleAct = async (intvId: string) => {
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      await fetch(`${baseUrl}/api/proactive/interventions/${intvId}/act`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Person-ID": personId
        },
        body: JSON.stringify({ feedback_note: "Acted from Notification Center" })
      });
      await fetchInterventions();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDismiss = async (intvId: string) => {
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      await fetch(`${baseUrl}/api/proactive/interventions/${intvId}/dismiss`, {
        method: "POST",
        headers: { "X-Person-ID": personId }
      });
      await fetchInterventions();
    } catch (err) {
      console.error(err);
    }
  };

  const handleTogglePref = async (key: keyof NotificationPrefs) => {
    const updated = { ...prefs, [key]: !prefs[key] };
    setPrefs(updated);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";
      const personId = typeof window !== "undefined"
        ? (localStorage.getItem("pathmind_user_name")?.toLowerCase().replace(/\s+/g, "-") || "scholar-user")
        : "scholar-user";

      await fetch(`${baseUrl}/api/proactive/preferences`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Person-ID": personId
        },
        body: JSON.stringify(updated)
      });
    } catch (err) {
      console.error(err);
    }
  };

  const getPriorityStyle = (priority: string) => {
    switch (priority) {
      case "CRITICAL":
        return "bg-rose-950/60 text-rose-300 border-rose-600/60";
      case "HIGH":
        return "bg-amber-950/60 text-amber-300 border-amber-600/60";
      case "NORMAL":
        return "bg-primary/20 text-primary border-primary/40";
      default:
        return "bg-surface-container text-on-surface-variant border-outline";
    }
  };

  const unreadCount = interventions.filter(i => i.status === "PENDING").length;

  return (
    <>
      {/* Bell Trigger Button */}
      <button
        onClick={() => setIsOpen(true)}
        aria-label="Proactive notifications"
        aria-expanded={isOpen}
        aria-controls="proactive-notifications-panel"
        className="relative p-2.5 rounded-full bg-surface-container border border-outline hover:border-primary/50 text-on-surface transition-all cursor-pointer focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none"
        title="Proactive Notifications"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-rose-500 text-white text-[10px] font-black flex items-center justify-center animate-pulse">
            {unreadCount}
          </span>
        )}
      </button>

      {/* Slide-over Drawer Modal */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs animate-in fade-in">
          <div
            id="proactive-notifications-panel"
            role="region"
            aria-label="Proactive Intelligence Notifications"
            className="bg-surface border-l border-outline w-full max-w-md h-full flex flex-col shadow-2xl animate-in slide-in-from-right duration-300"
          >
            {/* Drawer Header */}
            <div className="p-6 border-b border-outline flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <ShieldCheck className="w-5 h-5 text-primary" />
                <h3 className="font-bold text-lg text-on-surface">Proactive Intelligence</h3>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                aria-label="Close proactive notifications panel"
                className="p-1.5 rounded-xl hover:bg-surface-container text-on-surface-variant cursor-pointer focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Tab Selector */}
            <div className="flex border-b border-outline text-xs font-bold">
              <button
                onClick={() => setActiveTab("ALERTS")}
                className={`flex-1 py-3 border-b-2 text-center transition-all cursor-pointer ${
                  activeTab === "ALERTS" ? "border-primary text-primary" : "border-transparent text-on-surface-variant hover:text-on-surface"
                }`}
              >
                Active Interventions ({unreadCount})
              </button>
              <button
                onClick={() => setActiveTab("PREFS")}
                className={`flex-1 py-3 border-b-2 text-center transition-all cursor-pointer ${
                  activeTab === "PREFS" ? "border-primary text-primary" : "border-transparent text-on-surface-variant hover:text-on-surface"
                }`}
              >
                Preferences
              </button>
            </div>

            {/* Drawer Content */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4 text-xs">
              {activeTab === "ALERTS" ? (
                interventions.length === 0 ? (
                  <div className="p-8 text-center text-on-surface-variant space-y-2">
                    <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
                    <p className="font-semibold text-on-surface">Everything on Track</p>
                    <p className="text-[11px]">No urgent interventions detected. Keep progressing on your active stage.</p>
                  </div>
                ) : (
                  interventions.map((intv) => (
                    <div
                      key={intv.intervention_id}
                      className="p-5 rounded-3xl bg-surface-container border border-outline space-y-3 shadow-sm"
                    >
                      <div className="flex items-center justify-between">
                        <span className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider border ${getPriorityStyle(intv.priority)}`}>
                          {intv.priority} Priority
                        </span>
                        <span className="text-[10px] text-on-surface-variant">
                          {new Date(intv.created_at).toLocaleDateString()}
                        </span>
                      </div>

                      <h4 className="font-bold text-sm text-on-surface">{intv.title}</h4>

                      {/* 4-Part Structure */}
                      <div className="space-y-2 text-[11px] text-on-surface-variant">
                        <div>
                          <strong className="text-on-surface block">What Happened:</strong>
                          <span>{intv.what_happened}</span>
                        </div>
                        <div>
                          <strong className="text-on-surface block">Why It Matters:</strong>
                          <span>{intv.why_it_matters}</span>
                        </div>
                        <div className="p-2.5 rounded-xl bg-surface border border-outline/50">
                          <strong className="text-primary block">Recommended Action:</strong>
                          <span className="text-on-surface">{intv.what_should_i_do}</span>
                        </div>
                      </div>

                      {/* Action & Dismiss Buttons */}
                      <div className="pt-2 flex items-center justify-between gap-2">
                        <button
                          onClick={() => handleDismiss(intv.intervention_id)}
                          className="px-3 py-1.5 rounded-xl border border-outline hover:bg-surface text-on-surface-variant text-[11px] font-semibold cursor-pointer"
                        >
                          Dismiss
                        </button>
                        <Link
                          href={intv.action_url}
                          onClick={() => {
                            handleAct(intv.intervention_id);
                            setIsOpen(false);
                          }}
                          className="px-4 py-1.5 rounded-xl bg-primary text-on-primary font-bold text-[11px] shadow-sm flex items-center gap-1 cursor-pointer"
                        >
                          <span>Act Now</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </Link>
                      </div>
                    </div>
                  ))
                )
              ) : (
                /* Preferences Tab */
                <div className="space-y-4">
                  <div className="p-4 rounded-2xl bg-surface-container border border-outline space-y-3">
                    <h4 className="font-bold text-sm text-on-surface">Proactive Alert Categories</h4>
                    <p className="text-on-surface-variant text-[11px]">
                      Customize which proactive triggers can surface in your personal companion workspace.
                    </p>

                    <div className="space-y-2.5 pt-2">
                      <label className="flex items-center justify-between cursor-pointer">
                        <span className="text-on-surface font-medium">Opportunity Deadlines</span>
                        <input
                          type="checkbox"
                          checked={prefs.enable_opportunity_alerts}
                          onChange={() => handleTogglePref("enable_opportunity_alerts")}
                          className="w-4 h-4 text-primary rounded"
                        />
                      </label>

                      <label className="flex items-center justify-between cursor-pointer">
                        <span className="text-on-surface font-medium">Mastery Breakthroughs</span>
                        <input
                          type="checkbox"
                          checked={prefs.enable_mastery_alerts}
                          onChange={() => handleTogglePref("enable_mastery_alerts")}
                          className="w-4 h-4 text-primary rounded"
                        />
                      </label>

                      <label className="flex items-center justify-between cursor-pointer">
                        <span className="text-on-surface font-medium">Targeted Reinforcement</span>
                        <input
                          type="checkbox"
                          checked={prefs.enable_reinforcement_alerts}
                          onChange={() => handleTogglePref("enable_reinforcement_alerts")}
                          className="w-4 h-4 text-primary rounded"
                        />
                      </label>

                      <label className="flex items-center justify-between cursor-pointer">
                        <span className="text-on-surface font-medium">Prerequisite Blockers</span>
                        <input
                          type="checkbox"
                          checked={prefs.enable_blocker_alerts}
                          onChange={() => handleTogglePref("enable_blocker_alerts")}
                          className="w-4 h-4 text-primary rounded"
                        />
                      </label>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
