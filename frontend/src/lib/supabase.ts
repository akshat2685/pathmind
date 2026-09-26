"use client";

import { createClient, type SupabaseClient } from "@supabase/supabase-js";

let _client: SupabaseClient | null = null;

/**
 * Shared Supabase browser client for the PATHMIND main frontend.
 *
 * Uses the public anon key only (NEXT_PUBLIC_*); the service-role key is
 * never present in the browser. The backend verifies the user's JWT
 * server-side via `get_authenticated_person` and derives person identity
 * from it — the frontend never self-asserts a person id.
 *
 * Returns null when the env vars are not configured, so call sites can
 * degrade to unauthenticated requests (backend answers 401 honestly).
 */
export function getSupabaseClient(): SupabaseClient | null {
  if (_client) return _client;
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anonKey) return null;
  _client = createClient(url, anonKey);
  return _client;
}
