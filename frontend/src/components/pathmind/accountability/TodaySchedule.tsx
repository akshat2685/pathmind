"use client";

import { useEffect, useState } from "react";
import { authedFetch } from "@/lib/api";

interface Commitment {
  commitment_id: string;
  title: string;
  due_at: string | null;
  estimated_minutes: number;
  status: "planned" | "in_progress" | "completed" | "cancelled" | "missed";
  roadmap_phase?: string | null;
}

interface TodayData {
  date: string;
  streak_days: number;
  open_commitments: Commitment[];
  due_today_or_overdue: Commitment[];
  total_planned_minutes: number;
  total_completed_minutes: number;
  completion_rate: number;
}

/**
 * TodaySchedule — the daily accountability loop.
 * Shows streak, today's open commitments, and lets the learner
 * mark commitments done. Same trust contract as the college MVP:
 * streak is consecutive days with >= 1 completion; zero = zero.
 */
export function TodaySchedule() {
  const [data, setData] = useState<TodayData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const [adding, setAdding] = useState(false);

  async function load() {
    try {
      const res = await authedFetch("/api/accountability/today");
      if (!res.ok) throw new Error("Could not load today's schedule.");
      setData((await res.json()) as TodayData);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function setStatus(id: string, status: Commitment["status"]) {
    const res = await authedFetch(`/api/accountability/commitments/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    if (res.ok) load();
  }

  async function addCommitment() {
    const title = newTitle.trim();
    if (!title || adding) return;
    setAdding(true);
    try {
      const res = await authedFetch("/api/accountability/commitments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title }),
      });
      if (res.ok) {
        setNewTitle("");
        load();
      }
    } finally {
      setAdding(false);
    }
  }

  if (loading) {
    return (
      <div className="sketch-border p-6 bg-surface-container-low/90 text-center">
        <p className="font-body-sm text-on-surface-variant">Loading today's plan…</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="sketch-border p-6 bg-surface-container-low/90 text-center">
        <p className="font-body-sm text-error">{error || "Could not load."}</p>
        <button
          type="button"
          onClick={() => { setLoading(true); load(); }}
          className="ink-wash-btn px-4 py-1 mt-3 cursor-pointer"
        >
          Retry
        </button>
      </div>
    );
  }

  const urgentIds = new Set(data.due_today_or_overdue.map((c) => c.commitment_id));

  return (
    <div className="sketch-border p-6 bg-surface-container-low/90 space-y-5">
      <div className="flex items-center justify-between">
        <h3 className="font-note-handwritten text-2xl text-on-surface">Today</h3>
        <div className="flex items-center gap-2" title="Consecutive days with at least one completed commitment">
          <span className="material-symbols-outlined text-amber-500">local_fire_department</span>
          <span className="font-label-lg text-on-surface">
            {data.streak_days} day{data.streak_days === 1 ? "" : "s"}
          </span>
        </div>
      </div>

      {data.open_commitments.length === 0 ? (
        <p className="font-body-sm text-on-surface-variant">
          Nothing committed yet. Add one below — small promises, kept daily, are the whole game.
        </p>
      ) : (
        <ul className="space-y-2">
          {data.open_commitments.map((c) => (
            <li
              key={c.commitment_id}
              className={
                "flex items-center gap-3 p-3 rounded-lg border " +
                (urgentIds.has(c.commitment_id)
                  ? "border-amber-500/50 bg-amber-500/5"
                  : "border-outline-variant/40")
              }
            >
              <button
                type="button"
                onClick={() => setStatus(c.commitment_id, "completed")}
                className="shrink-0 w-6 h-6 rounded-full border-2 border-secondary/60 hover:bg-secondary/20 cursor-pointer"
                title="Mark done"
                aria-label={`Mark "${c.title}" done`}
              />
              <div className="flex-1 min-w-0">
                <p className="font-body-md text-on-surface truncate">{c.title}</p>
                <p className="text-[11px] font-label-md text-on-surface-variant/70">
                  {c.estimated_minutes} min
                  {urgentIds.has(c.commitment_id) ? " · due" : ""}
                  {c.status === "in_progress" ? " · in progress" : ""}
                </p>
              </div>
              {c.status === "planned" && (
                <button
                  type="button"
                  onClick={() => setStatus(c.commitment_id, "in_progress")}
                  className="text-xs font-label-md text-secondary hover:underline cursor-pointer shrink-0"
                >
                  Start
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      <div className="flex gap-2">
        <input
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") addCommitment(); }}
          placeholder="Commit to something today…"
          className="flex-1 bg-surface-container-high/60 border border-outline-variant/40 rounded-lg px-3 py-2 font-body-sm text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none focus:border-secondary"
        />
        <button
          type="button"
          onClick={addCommitment}
          disabled={adding || !newTitle.trim()}
          className="ink-wash-btn-primary px-4 py-2 cursor-pointer disabled:opacity-50"
        >
          Add
        </button>
      </div>

      <div className="flex items-center gap-4 text-xs font-label-md text-on-surface-variant/80">
        <span>
          {data.total_completed_minutes}/{data.total_planned_minutes} min done
        </span>
        <span>{Math.round(data.completion_rate * 100)}% completion</span>
      </div>
    </div>
  );
}
