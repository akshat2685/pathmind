import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { getSupabaseClient } from "@/lib/supabase";

/**
 * College-slice Supabase client — same import path college code uses.
 *
 * Lazily resolved on first use (Proxy) so importing this module never throws
 * when env vars are missing: the build prerender and unconfigured deploys
 * must not crash at import time. With env vars set this is the exact same
 * client getSupabaseClient() returns. Access without configuration throws a
 * clear error at the call site, where callers degrade to unauthenticated.
 */
function resolveClient(): SupabaseClient {
  const client = getSupabaseClient();
  if (!client) {
    throw new Error(
      "Supabase is not configured (set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY)."
    );
  }
  return client;
}

export const supabase = new Proxy({} as SupabaseClient, {
  get(_target, prop) {
    const client = resolveClient();
    const value = (client as unknown as Record<string | symbol, unknown>)[prop];
    return typeof value === "function"
      ? (value as (...args: unknown[]) => unknown).bind(client)
      : value;
  },
});
