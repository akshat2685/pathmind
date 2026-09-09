# PATHMIND Operational Runbook & Production Security Guide

This runbook outlines operational procedures, security threat models, incident triage protocols, and failure recovery policies for the PATHMIND production deployment.

---

## 1. Architecture Overview

```
[ GitHub Pages Frontend (Next.js Static) ]
                 │
                 │ HTTPS (Restricted CORS)
                 ▼
     [ Render Web Service Backend ]
   (FastAPI + Uvicorn + Security Middleware)
     ┌───────────┴────────────────┐
     ▼                            ▼
[ Google Cloud Firestore ]   [ Google ADK / Gemini 1.5 ]
(Encrypted at Rest/Transit)   (Model Reasoning & Analysis)
```

---

## 2. Security Threat Model & Implemented Controls

| Threat Category | Potential Attack | Enforced Production Control |
|---|---|---|
| **Identity & Auth** | Forged identities, path traversal in headers (`../../admin`) | Strict regex validation (`^[a-zA-Z0-9_\-\.]{3,64}$`), Bearer token / header parsing in `backend/core/security.py`. |
| **Authorization / IDOR** | Manipulating `person_id` to inspect/mutate another user's records | `enforce_person_ownership` server-side check. Cross-person queries return `403 Forbidden`. |
| **SSRF** | Passing `http://169.254.169.254` (cloud metadata) or RFC 1918 private IPs | `validate_safe_url` blocks loopback, private IPv4/IPv6, link-local, and cloud metadata IPs. |
| **Prompt Injection** | Embedding `Ignore previous instructions` in repos, resumes, or opportunities | `sanitize_external_content` strips override tokens and wraps untrusted input in `[DATA_UNTRUSTED_CONTENT]`. |
| **AI State Mutation** | Raw model hallucinating state changes | Deterministic state authority: models only emit `ActionProposal`s; changes are verified and applied deterministically. |
| **API Abuse / DoS** | High-frequency automated polling or token exhaustion | `SecurityRateLimiter` sliding-window throttling returning `429 Too Many Requests` with `Retry-After`. |
| **Information Leakage** | Verbose error stack traces exposing file paths | `StructuredErrorMiddleware` sanitizes 500 errors to standard JSON and correlation `X-Request-ID`. |
| **Clickjacking / MIME** | Embedding in malicious iframes, MIME-type confusion | Security headers injected: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `CSP`. |

---

## 3. Incident Triage Runbooks

### Runbook A: Backend Service Unavailable / 502 / Degraded

1. **Check Liveness**:
   ```bash
   curl -I https://pathmind-api.onrender.com/health/live
   ```
   - If HTTP 200: Application process is running. Issue is likely upstream or database readiness.
   - If HTTP 502 / Connection Refused: Service crashed or deploying on Render. Inspect Render logs.
2. **Check Readiness**:
   ```bash
   curl https://pathmind-api.onrender.com/health/ready
   ```
   - Checks `datastore` and `ai_reasoning` status without leaking connection strings.
3. **Inspect Render Dashboard**:
   - Verify environment variables `GEMINI_API_KEY`, `GOOGLE_APPLICATION_CREDENTIALS`, and `FIRESTORE_PROJECT_ID`.
   - Verify memory/CPU utilization (ensure no OOM errors).

---

### Runbook B: Gemini API Unavailable or Rate Limited

1. **Symptom**:
   - Health endpoint reports `ai_reasoning: degraded`.
   - AI-driven suggestions return `SOURCE_UNAVAILABLE` or `TIMEOUT`.
2. **Expected Behavior**:
   - PATHMIND operates in **Deterministic Degraded Mode**.
   - Preserved persisted goals, roadmaps, evidence, and mission control tasks continue to render normally from Firestore.
   - Zero hallucinated recommendations are presented.
3. **Action**:
   - Check Google AI Studio quota limits for the active `GEMINI_API_KEY`.
   - Verify network egress from Render to `generativelanguage.googleapis.com`.
   - If quota exhausted, rotate to backup API key in Render Dashboard.

---

### Runbook C: Provider Outage (GitHub API / ESCO)

1. **Symptom**:
   - Artifact verification or opportunity searches take up to 3.0s and return partial or offline results.
2. **Expected Behavior**:
   - The system returns cached verified opportunities and canonical artifacts with status `PARTIAL`.
   - The UI displays explicit status ("Offline cache active / Remote provider unreachable").
3. **Action**:
   - Do nothing immediately; the system's bounded timeouts (2.0–3.0s) prevent request hanging.
   - Verify status on `https://www.githubstatus.com`.

---

### Runbook D: Database Transient Failure & Recovery

1. **Symptom**:
   - `/health/ready` reports `datastore: unhealthy`.
2. **Expected Behavior**:
   - In-memory tenant buckets serve local reads gracefully while reconnect attempts proceed with exponential backoff.
3. **Action**:
   - Verify Google Cloud Firestore IAM permissions for the associated service account.
   - Check Google Cloud Status Dashboard for Firestore outages in the deployment region.

---

### Runbook E: Deployment Rollback Protocol

If a production release introduces regression:
1. **GitHub Pages (Frontend)**:
   - Identify last stable commit hash on `main`:
     ```bash
     git log -n 5 --oneline
     ```
   - Revert commit or redeploy stable tag through GitHub Actions workflow.
2. **Render (Backend)**:
   - Go to Render Dashboard -> **Deploys**.
   - Select the previous successful deploy and click **Rollback to this deploy**.
   - Verify `/health/ready` returns HTTP 200.

---

## 4. Environment Variables Checklist

| Variable | Environment | Description | Private? |
|---|---|---|---|
| `GEMINI_API_KEY` | Backend (Render) | Google Gemini API Key for model reasoning | **YES (Secret)** |
| `GOOGLE_APPLICATION_CREDENTIALS` | Backend (Render) | Path to Firestore service account credentials | **YES (Secret)** |
| `FIRESTORE_PROJECT_ID` | Backend (Render) | Google Cloud Project ID | No |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend (GitHub Pages) | Public URL of the backend API (`https://pathmind-api.onrender.com`) | No |

---

## 5. Security & Isolation Invariant

> **No user's data may ever be exposed to, or mutated by, another person.**
> Every query, trace, memory, goal, artifact, and roadmap mutation is strictly scoped to the verified `X-Person-ID` identity server-side.
