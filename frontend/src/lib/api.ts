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

/**
 * Fetch against the backend with the Supabase session's Bearer token.
 *
 * Merges caller-supplied headers over the auth headers. When there is no
 * session the request goes out without Authorization and the backend
 * answers 401 honestly.
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
  return fetch(apiUrl(path), { ...init, headers });
}
