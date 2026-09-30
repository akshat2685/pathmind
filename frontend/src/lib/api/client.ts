/**
 * PATHMIND Centralized HTTP API Client.
 * Routes all frontend requests to FastAPI using NEXT_PUBLIC_API_URL.
 * The browser communicates ONLY with FastAPI, NEVER directly with Supabase.
 */

import { supabase } from "@/lib/supabase/client";

const API_BASE_URL = (
  typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL
    ? process.env.NEXT_PUBLIC_API_URL
    : "http://localhost:8000"
).replace(/\/$/, "");

export interface ApiResponse<T = unknown> {
  data: T | null;
  status: number;
  ok: boolean;
  error?: string;
}

export interface RequestOptions extends Omit<RequestInit, "body"> {
  headers?: Record<string, string>;
  params?: Record<string, string | number | boolean | undefined>;
}

/**
 * FastAPI error bodies come in a few shapes:
 *   { detail: "some message" }                          (HTTPException)
 *   { detail: [ { loc: [...], msg: "...", type } ] }    (422 validation errors)
 *   { detail: { msg: "..." } }
 *   { error: "..." } / { message: "..." }
 * Normalize any of them into ONE human-readable string. Never String() a raw
 * object/array here — that is exactly how "[object Object]" leaked into the UI.
 */
interface FastApiErrorItem {
  loc?: Array<string | number>;
  msg?: string;
  message?: string;
}

function describeErrorItem(item: unknown): string {
  if (typeof item === "string") return item;
  if (item && typeof item === "object") {
    const e = item as FastApiErrorItem;
    const msg = e.msg || e.message;
    if (msg) {
      // Prefix the field path ("email: field required") so form users know
      // WHICH input failed; the leading "body" segment is noise.
      const loc = Array.isArray(e.loc)
        ? e.loc.filter((part) => part !== "body").join(".")
        : "";
      return loc ? `${loc}: ${msg}` : msg;
    }
    try {
      return JSON.stringify(item);
    } catch {
      return "Unknown error";
    }
  }
  return item == null ? "Unknown error" : String(item);
}

export function extractErrorMessage(data: unknown, fallback: string): string {
  if (!data || typeof data !== "object") return fallback;
  const d = data as { detail?: unknown; error?: unknown; message?: unknown };
  const candidate = d.detail ?? d.error ?? d.message;
  if (typeof candidate === "string" && candidate) return candidate;
  if (Array.isArray(candidate)) {
    if (candidate.length === 0) return fallback;
    return candidate.map(describeErrorItem).join("; ");
  }
  if (candidate && typeof candidate === "object") {
    return describeErrorItem(candidate);
  }
  return fallback;
}

async function request<T = unknown>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  const url = `${API_BASE_URL}${cleanEndpoint}`;

  const defaultHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };

  const { data: { session } } = await supabase.auth.getSession();
  if (session?.access_token) {
    defaultHeaders["Authorization"] = `Bearer ${session.access_token}`;
  }

  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        ...defaultHeaders,
        ...(options.headers || {}),
      },
    });

    let responseData: T | null = null;
    const contentType = res.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      responseData = await res.json();
    } else {
      const text = await res.text();
      responseData = (text ? text : null) as unknown as T;
    }

    if (!res.ok) {
      // detail can be a string, an ARRAY (FastAPI 422), or an object — always
      // normalize to a readable string, never String() the raw value.
      const errorMessage = extractErrorMessage(
        responseData,
        `HTTP Error ${res.status}: ${res.statusText}`
      );
      return {
        data: responseData,
        status: res.status,
        ok: false,
        error: errorMessage,
      };
    }

    return {
      data: responseData,
      status: res.status,
      ok: true,
    };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Network error";
    return {
      data: null,
      status: 0,
      ok: false,
      error: message,
    };
  }
}

export const apiClient = {
  baseUrl: API_BASE_URL,

  async get<T = unknown>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<ApiResponse<T>> {
    let url = endpoint;
    if (options.params) {
      const searchParams = new URLSearchParams();
      for (const [k, v] of Object.entries(options.params)) {
        if (v !== undefined) {
          searchParams.append(k, String(v));
        }
      }
      const qs = searchParams.toString();
      if (qs) {
        url += (url.includes("?") ? "&" : "?") + qs;
      }
    }
    return request<T>(url, {
      method: "GET",
      headers: options.headers,
      signal: options.signal,
    });
  },

  async post<T = unknown, B = unknown>(
    endpoint: string,
    body?: B,
    options: RequestOptions = {}
  ): Promise<ApiResponse<T>> {
    return request<T>(endpoint, {
      method: "POST",
      headers: options.headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: options.signal,
    });
  },

  async put<T = unknown, B = unknown>(
    endpoint: string,
    body?: B,
    options: RequestOptions = {}
  ): Promise<ApiResponse<T>> {
    return request<T>(endpoint, {
      method: "PUT",
      headers: options.headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: options.signal,
    });
  },

  async patch<T = unknown, B = unknown>(
    endpoint: string,
    body?: B,
    options: RequestOptions = {}
  ): Promise<ApiResponse<T>> {
    return request<T>(endpoint, {
      method: "PATCH",
      headers: options.headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: options.signal,
    });
  },

  async delete<T = unknown>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<ApiResponse<T>> {
    return request<T>(endpoint, {
      method: "DELETE",
      headers: options.headers,
      signal: options.signal,
    });
  },
};

export default apiClient;
