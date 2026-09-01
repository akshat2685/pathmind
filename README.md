# PATHMIND — Intelligent Longitudinal Career & Learning Navigation Engine

**PATHMIND** is an evidence-informed, psychometrically grounded career navigation and adaptive learning engine built with **Google Agent Development Kit (ADK)** and **Gemini 2.5 Flash**.

Unlike generic personality quizzes or arbitrary chatbot recommendations, PATHMIND enforces a strict **Evidence-Informed Protocol**: anchoring validated psychometrics (RIASEC, SCCT) to verified behavioral evidence (source code, projects, hackathon achievements), continuously scaffolding learners along progressive roadmaps, and maintaining private longitudinal memory alongside anonymized collective intelligence.

---

## 🌟 The 6-Chapter Experience

```text
┌─────────────────────────┐     ┌─────────────────────────┐     ┌─────────────────────────┐
│ Chapter I: Initiation   │ ──> │ Chapter II: Counseling  │ ──> │ Chapter III: Explorer   │
│ Profile & Identity      │     │ Psychometrics & Evidence│     │ Trajectory Brain & Paths│
└─────────────────────────┘     └─────────────────────────┘     └─────────────────────────┘
             │                                                               │
             ▼                                                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐     ┌─────────────────────────┐
│ Chapter VI: Launchpad   │ <── │ Chapter V: Memory Vault │ <── │ Chapter IV: Journey     │
│ Readiness & Opps        │     │ Longitudinal Memory     │     │ Progressive Roadmap     │
└─────────────────────────┘     └─────────────────────────┘     └─────────────────────────┘
```

1. **Chapter I: The Initiation (`/onboarding`)**
   - Builds a structured longitudinal profile capturing education, target roles, constraints, and learning preferences without assumptions.
2. **Chapter II: Evidence-Informed Counseling (`/assessment`)**
   - Standardized Holland RIASEC & Lent-Brown SCCT assessments combined with 5 observable practical tasks (code debugging, technical writing, trade-off analysis).
3. **Chapter III: Trajectory Brain & Career Explorer (`/explorer`)**
   - Synthesizes 2–3 grounded candidate pathways with skill gap taxonomies, education routes, counterfactual branches, and case study provenance.
4. **Chapter IV: Progressive Journey & Adaptive Learning (`/journey`)**
   - Server-side lock-enforced milestone roadmap with multi-dimensional mastery evaluations (`PASS` / `REINFORCE`), active remediation insertion, and dynamic constraint adaptation.
5. **Chapter V: Longitudinal Memory Vault (`/memory`)**
   - Structured private memory (Episodic, Semantic, Preference, Strategy, Goal) with natural conversational recall and Past &rarr; Present knowledge transfer bridges alongside anonymized shared learning patterns.
6. **Chapter VI: Accountability Partner & Career Launchpad (`/readiness`)**
   - Multi-gap categorization, universal persona support (students, switchers, working professionals), transferable skills matrix (`HAVE`, `REUSE`, `BUILD`), strategic credential recommendations (`PROJECT > CERTIFICATE`), verified real-world opportunities board, and evidence-grounded tailored resume with ATS keyword optimization.

---

## 🏛️ System Architecture

```text
                                  PATHMIND SYSTEM
                                         │
        ┌────────────────────────────────┴────────────────────────────────┐
        ▼                                                                 ▼
[ Next.js 15 App Router ]                                     [ FastAPI Backend API ]
  • Stitch Analog Paper Theme                                   • Router Architecture
  • Motion Micro-animations                                     • Server-side Lock Engine
  • 8 Production Routes                                         • Privacy Filter Boundary
        │                                                                 │
        └────────────────────────────────┬────────────────────────────────┘
                                         ▼
                             [ Google ADK Multi-Agent Core ]
  ┌─────────────────────────┬─────────────────────────┬─────────────────────────┐
  │ CounselingAgent         │ TrajectoryAgent         │ RoadmapArchitectAgent   │
  │ EvidenceEvaluatorAgent  │ PersonalAgentEngine     │ MemoryAgent             │
  │ PersonalizationAgent    │ PatternAgent            │ CareerReadinessAgent    │
  │ CredentialAgent         │ AccountabilityAgent     │ ResumeAgent             │
  └─────────────────────────┴─────────────────────────┴─────────────────────────┘
                                         │
                                         ▼
                               [ Gemini 2.5 Flash ]
                                         │
                                         ▼
                      [ Knowledge Layer & Persistent Vault ]
  • European Skills/Competences (ESCO) & National Classification of Occupations (NCO)
  • Google Cloud Firestore / Isolated Multi-Tenant In-Memory Vault
```

---

## 🚀 Live Public Deployment

| Service | Host | Live URL | Health Status |
|---|---|---|---|
| **Frontend Web App** | GitHub Pages | [https://akshat2685.github.io/pathmind](https://akshat2685.github.io/pathmind) | **Online & Deployed** |
| **Backend API** | Render Web Service | [https://pathmind-api.onrender.com](https://pathmind-api.onrender.com) | **Active & Monitored** |
| **API Health Check** | Render | [https://pathmind-api.onrender.com/health](https://pathmind-api.onrender.com/health) | `{"status": "ok"}` |
| **Interactive Docs** | Swagger UI | [https://pathmind-api.onrender.com/docs](https://pathmind-api.onrender.com/docs) | Complete OpenAPI Spec |

---

## 🛠️ Technology Stack

- **Frontend**: Next.js 15 (Turbopack, App Router, React 19), Tailwind CSS, Framer Motion, Google Fonts (Newsreader, Courier Prime, Playfair Display).
- **Backend**: Python 3.14, FastAPI, Pydantic V2, Uvicorn, AsyncIO, Pytest.
- **AI & Reasoning**: Google Agent Development Kit (ADK) pattern, Google Gemini 2.5 Flash (`gemini-2.5-flash`).
- **Data & Standards**: ESCO API adapter, NCO mapping, Firestore Async client.
- **CI / CD**: GitHub Actions (`.github/workflows/deploy-frontend.yml`), Render Web Service git-triggered deployments.

---

## 💻 Local Development Setup

### 1. Backend Setup
```bash
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1   # On Linux/macOS: source venv/bin/activate
pip install -r requirements.txt

# Run test suite (40 tests across all 6 engines)
pytest -v

# Start local backend server
uvicorn main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
cd frontend
npm install

# Run development server
npm run dev

# Run production build validation
npm run build
```

---

## 🛡️ Privacy & Security Boundaries

1. **Strict Server-Side Isolation**: Person data, private memories, roadmap states, and evaluations require explicit authentication and authorization (`person_id` isolation). Person A can never access Person B's private records.
2. **Deterministic Privacy Filter**: Before any learning event contributes to the shared collective intelligence layer, all personal names, emails, user IDs, exact timestamps, and conversational messages are stripped.
3. **No Fabricated Facts**: Resumes and career readiness claims are derived exclusively from verified learning submissions and portfolio milestones.
4. **Credential Discipline**: Zero credentials or private keys are exposed in frontend bundles, public JavaScript, or client code.

---

## 🧪 Test Suite Summary

- **Pytest Suite (`pytest -v`)**: **40 / 40 passed (100%)**
  - Psychometrics & Observable Tasks: 11 tests
  - Trajectory Brain & Career Explorer: 5 tests
  - Progressive Roadmap & Server-Side Locks: 6 tests
  - Longitudinal Memory & Natural Recall: 6 tests
  - Career Readiness, Accountability & Resume: 8 tests
  - Knowledge Providers & Health: 4 tests
- **Next.js Production Build**: **8 / 8 routes compiled and statically optimized with 0 errors**.
