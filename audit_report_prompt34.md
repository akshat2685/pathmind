# PATHMIND TECH STACK, BACKEND CONNECTIVITY & PRODUCTION INTEGRATION AUDIT

## 1. ACTUAL TECH STACK
Component | Technology | Actual File(s) | Status | Evidence
---|---|---|---|---
**Frontend Framework** | Next.js 15.5 (Turbopack) | `frontend/package.json` | CONNECTED | `next`, `react`, `react-dom` dependencies
**Language** | TypeScript (^5) / Python (3.10+) | `package.json`, `requirements.txt` | CONNECTED | Codebase languages
**CSS / Components** | Tailwind CSS v4, shadcn/ui, base-ui | `frontend/package.json` | CONNECTED | `tailwindcss`, `shadcn`
**Animations** | framer-motion (^13.1.1) | `frontend/package.json` | CONNECTED | Used in UI components
**Routing / State** | Next.js App Router, React Context | `frontend/src/app` | CONNECTED | Standard Next.js patterns
**Backend Framework** | FastAPI + Uvicorn | `backend/requirements.txt` | CONNECTED | `fastapi`, `uvicorn`
**Database** | Firestore | `backend/services/store.py` | PARTIAL | `google-cloud-firestore`. Includes memory fallback.
**AI SDK** | Gemini (`google-generativeai`) | `backend/services/*.py` | CONNECTED | Heavily imported across reasoning agents
**Agent Framework** | ADK | `backend/requirements.txt` | UNUSED | `adk` present but only imported in `knowledge_tools.py`
**Deployment** | GitHub Pages / Render | `.github/workflows/deploy-frontend.yml` | CONNECTED | Deploys frontend to GH Pages targeting Render backend URL
**Testing** | pytest, emulator | `backend/tests/` | CONNECTED | Test suite relies on Pytest and `FIRESTORE_EMULATOR_HOST`

## 2. FRONTEND CONNECTIVITY
- **Onboarding/Goal:** CONNECTED. Calls `${baseUrl}/api/career/goals`
- **Assessment:** CONNECTED. Calls `${baseUrl}/api/assessments/*`
- **Counseling/Path:** CONNECTED. Calls `${baseUrl}/api/career/counseling`
- **Roadmap/Adaptation:** CONNECTED. Calls `${baseUrl}/api/roadmap/*`, `${baseUrl}/api/adaptation/*`
- **Memory:** CONNECTED. Calls `/api/memory/personal`
- **Opportunities/Market:** CONNECTED. Calls `${baseUrl}/api/career/opportunities`
- **Resume/Portfolio:** CONNECTED. Calls `${baseUrl}/api/career/resume/tailor` and `/api/artifacts`
- **Execution:** CONNECTED. Calls `/api/execution/actions`

*Verdict:* API endpoints are correctly wired in the frontend using native `fetch` across all golden workflows.

## 3. BACKEND CONNECTIVITY
Backend services use FastAPI dependency injection (`Depends`) for authentication (`get_authenticated_person`) and database layers.
The architecture correctly separates route definitions (`backend/api/*.py`) from service logic (`backend/services/*.py`), connecting down to `FirestoreStore`.

## 4. FIRESTORE CONNECTIVITY
Status: **PARTIAL (Hybrid Memory/Firestore)**
`backend/services/store.py` dynamically activates the actual `google.cloud.firestore.AsyncClient` only if `GOOGLE_APPLICATION_CREDENTIALS` or `FIRESTORE_EMULATOR_HOST` are present.
- **CONNECTED:** Active deployments with credentials or local E2E tests using the emulator.
- **IN-MEMORY ONLY:** Runs without credentials, defaulting to nested Python dictionaries.
All core models (Goal, Assessment, Profile, Roadmap, Memory, Resume, etc.) correctly trigger `await asyncio.wait_for(doc_ref.set(...))` when connected.

## 5. GEMINI CONNECTIVITY
Status: **REAL GEMINI CALL**
The `google-generativeai` SDK is imported in 14 different agent services (e.g. `roadmap_engine.py`, `counseling.py`, `market_intelligence_service.py`).
- **Prompt Layer:** Deterministic JSON structured outputs are requested from `gemini-2.5-flash` using strict Pydantic schemas.
- **Fallback:** Try-catch blocks return deterministic JSON structures if Gemini raises an exception or rate-limits.

## 6. ADK CONNECTIVITY
Status: **CONFIGURED BUT UNUSED**
- `adk>=0.0.5` is installed via `requirements.txt`.
- Codebase searches reveal `from adk import tool` only in `knowledge_tools.py`, which is not actively integrated into the production agent routes.

## 7. EXTERNAL PROVIDERS
- **O\*NET / BLS:** MOCK/TEST ONLY. `RealisticMarketProviderAdapter` checks for `BLS_API_KEY`/`ONET_API_KEY`. If present, returns simulated static data; if absent, returns unavailable states.
- **ESCO / NCO / AISHE / NIRF:** NOT_IMPLEMENTED natively in real time, though referenced as sources in prompts.

## 8. OPPORTUNITY CONNECTIVITY
Status: **BROKEN / MOCKED**
`backend/providers/opportunity_provider.py` contains a `RealAPIProviderAdapter` pointing to the deprecated `https://jobs.github.com/positions.json`. Requires a valid `REAL_OPPORTUNITY_API_KEY` which is unused. Opportunities returned are essentially simulated or fail-closed (empty array).

## 9. MARKET CONNECTIVITY
Status: **LLM SYNTHESIS WITH MOCKED BASE**
`MarketIntelligenceService` uses Gemini to intelligently synthesize domain-specific labor market signals (e.g., distinguishing cricket trials from software interviews), but the underlying raw provider `RealisticMarketProviderAdapter` returns mocked UUIDs. A cricket goal will receive a realistically reasoned string from Gemini, but not live BLS/NCO data.

## 10. ASSESSMENT CONNECTIVITY
Status: **REAL, STATIC DEFINITIONS**
`backend/services/assessment.py` defines exactly 23 static questions across 3 frameworks:
1. **RIASEC (12 items)**: Career interests (R, I, A, S, E, C).
2. **SCCT (6 items)**: Self-efficacy and outcome expectations.
3. **LEARNING (5 items)**: Observable problem-solving (Recall, Explain, Apply, Error Detection, Reasoning).
These are domain-neutral, stored, and scored correctly.

## 11. RIASEC ANALYSIS
Status: **SEPARATED CORRECTLY**
The RIASEC instrument (Layer A) is completely independent of the goal-specific evaluations (Layer B). RIASEC results yield a 0-100 normalized array that acts as contextual evidence without overwriting or contaminating the user's explicit canonical goal.

## 12. DOMAIN-BIAS FINDINGS
Status: **GLOBAL FALLBACK BIAS DETECTED**
- `backend/services/counseling.py`: Hardcoded logic searches for `["code", "software", "developer", "engineering", "ai", "machine learning", "robotics"]` to yield specific fallback trajectories (e.g., "Systems & Distributed Software Architecture").
- `backend/services/roadmap_engine.py`: Default fallback explicitly generates a stage for "Python Foundations & Object-Oriented Engineering".
These biases only surface when LLM synthesis fails or in deterministic fallbacks, but they constitute a strict domain violation for a neutral platform.

## 13. AUTHENTICATION STATUS
Status: **REAL / HEADER-BASED / STRICT**
Authentication is enforced strictly via the `X-Person-ID` HTTP header in `backend/core/security.py` -> `get_authenticated_person`. It returns HTTP 400 for empty IDs. It no longer falls back to `"scholar-user"`.

## 14. MEMORY STATUS
Status: **REAL (Firestore/In-Memory)**
`memory_engine.py` uses `SecondBrainService` to ingest events. It safely responds with `NO_RECORDED_MEMORY` if no cross-stage linkages exist. Memories do not overwrite Canonical Goals or Profile Facts.

## 15. RESUME/PORTFOLIO STATUS
Status: **PARTIAL**
Endpoints like `POST /api/career/resume/tailor` exist and connect to `resume_agent.generate_tailored_resume()`. Portfolio artifacts hit `/api/artifacts/*`. The infrastructure exists but portfolio validation relies heavily on LLM synthesis without external credential checks.

## 16. DEPLOYMENT STATUS
Status: **PRODUCTION CONNECTED**
- **Frontend:** Deployed via GitHub Actions (`deploy-frontend.yml`) to GitHub Pages.
- **Backend:** Configured via `NEXT_PUBLIC_API_BASE_URL` to hit `https://pathmind-api.onrender.com`.

## 17. COMPLETE SYSTEM GRAPH

```text
USER
  ↓
FRONTEND (Next.js)
  ↓ ✅ CONNECTED
API (FastAPI)
  ↓ ✅ CONNECTED
ORCHESTRATOR / SECURITY (X-Person-ID validation)
  ↓ ✅ CONNECTED
SERVICES (RoadmapEngine, TrajectoryEngine, etc.)
  ↓ ✅ CONNECTED
AGENTS (Gemini 2.5 Flash SDK)
  ↓ ⭕ UNUSED (ADK Layer missing integration)
TOOLS (knowledge_tools.py)
  ↓ ⚠️ PARTIAL (Firestore) / ❌ BROKEN (Market/Opportunity API)
DATABASE / EXTERNAL PROVIDERS
  ↓ ✅ CONNECTED
RESPONSE
  ↓ ✅ CONNECTED
FRONTEND
```

## 18. CRITICAL GAPS
**CRITICAL**
1. **Domain Bias:** Hardcoded Python/Software fallbacks in `roadmap_engine.py` and `counseling.py` violate domain neutrality.
2. **Opportunity Provider:** Points to a dead GitHub jobs API; needs a real active provider (e.g., SerpAPI, Adzuna).

**HIGH**
3. **Market Provider:** BLS/ONET integration is entirely mocked.
4. **ADK Missing Integration:** The `adk` dependency is loaded but tools are never wired into the execution loop.

**MEDIUM**
5. **Resume Export:** Relies exclusively on LLM text generation rather than strict schema-to-PDF serialization.

**LOW**
6. **Firestore Implicit Failover:** In-memory failover silently masks connection issues in production if credentials drop.

## 19. EXACT FILES INVOLVED
- `frontend/package.json`
- `backend/requirements.txt`
- `backend/services/store.py`
- `backend/services/assessment.py`
- `backend/services/roadmap_engine.py` (Domain Bias)
- `backend/services/counseling.py` (Domain Bias)
- `backend/providers/opportunity_provider.py` (Broken API)
- `backend/providers/market_provider.py` (Mocked Data)
- `.github/workflows/deploy-frontend.yml`

## 20. RECOMMENDED FIX ORDER
1. Strip hardcoded software/Python biases from `roadmap_engine.py` and `counseling.py`.
2. Implement a working opportunity provider (replace GitHub Jobs API).
3. Connect a real Market API adapter (e.g. Adzuna or SerpAPI Jobs).
4. Integrate ADK tools officially into the agent workflows.
5. Add explicit Firestore connection exception throwing in production environments.
