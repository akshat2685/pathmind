"use client";

import { getSupabaseClient } from "./supabase";

/**
 * Returns the Authorization header for the current Supabase session.
 *
 * The backend (`get_authenticated_person` in backend/core/security.py)
 * requires `Authorization: Bearer <supabase-jwt>` and derives the person
 * id from the verified token. Self-asserted X-Person-ID headers are no
 * longer accepted.
 *
 * Returns an empty object when there is no session or Supabase is not
 * configured — the backend then responds 401 honestly. No login UI is
 * built here (product decision); this just wires the token plumbing so an
 * authenticated session works end to end.
 */
export async function getAuthHeaders(): Promise<Record<string, string>> {
  try {
    const client = getSupabaseClient();
    if (!client) return {};
    const { data, error } = await client.auth.getSession();
    if (error || !data.session?.access_token) return {};
    return { Authorization: `Bearer ${data.session.access_token}` };
  } catch {
    return {};
  }
}

/**
 * Returns the current authenticated user's id, or null when signed out.
 * Convenience for UI display only — never sent as an identity assertion.
 */
export async function getCurrentUserId(): Promise<string | null> {
  try {
    const client = getSupabaseClient();
    if (!client) return null;
    const { data } = await client.auth.getUser();
    return data.user?.id ?? null;
  } catch {
    return null;
  }
}
