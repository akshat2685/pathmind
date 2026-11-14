"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/api/client";

interface HealthCheckResult {
  loading: boolean;
  status: number | null;
  data: Record<string, unknown> | null;
  error: string | null;
}

export default function DiagnosticsPage() {
  const [apiHealth, setApiHealth] = useState<HealthCheckResult>({
    loading: true,
    status: null,
    data: null,
    error: null,
  });

  const [dbHealth, setDbHealth] = useState<HealthCheckResult>({
    loading: true,
    status: null,
    data: null,
    error: null,
  });

  const runDiagnostics = async () => {
    setApiHealth({ loading: true, status: null, data: null, error: null });
    setDbHealth({ loading: true, status: null, data: null, error: null });

    // 1. Test FastAPI backend connectivity
    const apiRes = await apiClient.get<Record<string, unknown>>("/api/health");
    setApiHealth({
      loading: false,
      status: apiRes.status,
      data: apiRes.data,
      error: apiRes.error || null,
    });

    // 2. Test Supabase database connectivity through FastAPI
    const dbRes = await apiClient.get<Record<string, unknown>>("/api/health/database");
    setDbHealth({
      loading: false,
      status: dbRes.status,
      data: dbRes.data,
      error: dbRes.error || null,
    });
  };

  useEffect(() => {
    runDiagnostics();
  }, []);

  return (
    <div className="min-h-screen bg-[#f7f4e7] text-[#252321] font-sans p-6 sm:p-12 selection:bg-[#8ba88e]/40">
      <div className="max-w-3xl mx-auto space-y-8">
        
        {/* Top Navigation */}
        <div className="flex items-center justify-between border-b border-[#252321]/20 pb-4">
          <Link
            href="/login"
            className="inline-flex items-center gap-2 text-xs font-serif italic text-[#4a654e] hover:underline"
          >
            ← Back to Scholar&apos;s Desk
          </Link>
          <span className="text-xs uppercase tracking-widest font-mono text-[#68635e]">
            Diagnostic Pipeline
          </span>
        </div>

        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-[#252321]">
            System Connectivity Audit
          </h1>
          <p className="font-serif italic text-sm text-[#68635e] mt-1">
            Verifying the live runtime chain: Browser → Next.js → FastAPI → Supabase PostgreSQL
          </p>
        </div>

        {/* Diagnostics Cards */}
        <div className="space-y-4">
          
          {/* Check 1: FastAPI Health */}
          <div
            className="p-5 bg-[#fdfae7] border-[1.5px] border-[#252321] rounded-lg shadow-[3px_4px_0px_rgba(37,35,33,0.9)]"
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-[#252321] text-[#fdfae7]">
                  GET /api/health
                </span>
                <span className="text-xs font-semibold text-[#252321]">
                  FastAPI Backend Server
                </span>
              </div>
              <div>
                {apiHealth.loading ? (
                  <span className="text-xs italic text-[#68635e]">Querying...</span>
                ) : apiHealth.status === 200 ? (
                  <span className="text-xs font-bold text-[#2e5e34] bg-[#8ba88e]/30 px-2 py-0.5 rounded border border-[#8ba88e]">
                    ✓ HTTP 200 OK
                  </span>
                ) : (
                  <span className="text-xs font-bold text-[#ba1a1a] bg-[#ffdad6] px-2 py-0.5 rounded border border-[#ba1a1a]">
                    ✗ HTTP {apiHealth.status || "ERR"}
                  </span>
                )}
              </div>
            </div>

            <div className="bg-[#ede8d5] p-3 rounded font-mono text-xs overflow-x-auto text-[#252321]">
              <pre>
                {apiHealth.loading
                  ? "Awaiting response..."
                  : JSON.stringify(apiHealth.data || { error: apiHealth.error }, null, 2)}
              </pre>
            </div>
          </div>

          {/* Check 2: Supabase Database Health */}
          <div
            className="p-5 bg-[#fdfae7] border-[1.5px] border-[#252321] rounded-lg shadow-[3px_4px_0px_rgba(37,35,33,0.9)]"
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-[#252321] text-[#fdfae7]">
                  GET /api/health/database
                </span>
                <span className="text-xs font-semibold text-[#252321]">
                  Supabase PostgreSQL Connectivity
                </span>
              </div>
              <div>
                {dbHealth.loading ? (
                  <span className="text-xs italic text-[#68635e]">Querying...</span>
                ) : dbHealth.status === 200 ? (
                  <span className="text-xs font-bold text-[#2e5e34] bg-[#8ba88e]/30 px-2 py-0.5 rounded border border-[#8ba88e]">
                    ✓ HTTP 200 CONNECTED
                  </span>
                ) : (
                  <span className="text-xs font-bold text-[#ba1a1a] bg-[#ffdad6] px-2 py-0.5 rounded border border-[#ba1a1a]">
                    ✗ HTTP {dbHealth.status || "ERR"} UNAVAILABLE
                  </span>
                )}
              </div>
            </div>

            <div className="bg-[#ede8d5] p-3 rounded font-mono text-xs overflow-x-auto text-[#252321]">
              <pre>
                {dbHealth.loading
                  ? "Awaiting server-side Supabase verification..."
                  : JSON.stringify(dbHealth.data || { error: dbHealth.error }, null, 2)}
              </pre>
            </div>
          </div>

        </div>

        {/* Action Button */}
        <div className="pt-2 flex gap-4">
          <button
            onClick={runDiagnostics}
            className="px-4 py-2 bg-[#252321] hover:bg-[#383430] text-[#fdfae7] text-xs font-semibold rounded shadow-[2px_3px_0px_rgba(37,35,33,0.9)] cursor-pointer"
          >
            Re-run Diagnostic Probe
          </button>
        </div>

      </div>
    </div>
  );
}
