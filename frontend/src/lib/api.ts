"use client";

import { getAuthHeaders } from "./auth";

/**
 * Canonical backend base URL for the PATHMIND main frontend.
 *
 * Single source of truth — components must use this (via `apiUrl` /
 * `authedFetch`) instead of inlining
 * `process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com"`
 * per call site.
 */
export const API_BASE: string =
  process.env.NEXT_PUBLIC_API_BASE_URL || "https://pathmind-api.onrender.com";

/** Join API_BASE with a `/api/...` path. */
export function apiUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE.replace(/\/$/, "")}${p}`;
}

export interface AuthedFetchInit extends Omit<RequestInit, "headers"> {
  headers?: Record<string, string>;
}

/** Local keys holding the learner's identity; dropped on auth expiry. */
const PATHMIND_IDENTITY_KEYS = [
  "pathmind_person_id",
  "pathmind_user_name",
  "pathmind_user_identity",
  "pathmind_user_goal",
  "pathmind_user_evidence",
];

/**
 * Fetch against the backend with the Supabase session's Bearer token.
 *
 * Merges caller-supplied headers over the auth headers. When there is no
 * session the request goes out without Authorization and the backend
 * answers 401 honestly.
 *
 * Centralized 401 handling: when the backend says the token is invalid or
 * expired, clear the stale local identity (so the app never silently
 * renders as a new/anonymous user) and send the traveler to the sign-in
 * page. Redirect is skipped when already on a sign-in route to avoid loops.
 */
export async function authedFetch(
  path: string,
  init: AuthedFetchInit = {}
): Promise<Response> {
  const authHeaders = await getAuthHeaders();
  const headers: Record<string, string> = {
    ...authHeaders,
    ...(init.headers ?? {}),
  };
  const res = await fetch(apiUrl(path), { ...init, headers });
  if (res.status === 401 && typeof window !== "undefined") {
    const p = window.location.pathname;
    const onSigninRoute =
      p === "/signin" ||
      p === "/login" ||
      p.startsWith("/signin/") ||
      p.startsWith("/login/");
    if (!onSigninRoute) {
      for (const k of PATHMIND_IDENTITY_KEYS) {
        localStorage.removeItem(k);
      }
      window.location.assign("/signin");
    }
  }
  return res;
}
