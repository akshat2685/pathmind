# PATHMIND — Pitch Readiness Specification & Operational Audit

## 1. Executive Problem & Product Definition

### The Problem
Traditional career and technical education tools suffer from five fundamental structural failures:
1. **Vanity Metrics & Checkbox Illusions**: Platforms reward passive video watching and superficial checkbox completion with false badges, producing graduates unable to satisfy real-world engineering expectations.
2. **Amnesiac AI Copilots**: Generic conversational LLMs have no persistent memory across sessions. They cannot remember past struggles, earlier project architectures, or changing constraints, forcing users to re-prompt from scratch.
3. **Static, Fragile Roadmaps**: Linear syllabus tracks break as soon as a learner's life constraints change (e.g., examination blocks, reduced weekly hours, or shifted career interests).
4. **Disconnected Job Boards**: Conventional portals present aspirational postings with arbitrary keyword matching, obscuring the critical difference between *theoretical role interest* and *practical verified capability*.
5. **Simulated Vanity Data**: Many career tools manufacture fake streak counters, fabricated compatibility percentages, and simulated application progress.

### The Product
**PATHMIND** is a persistent, evidence-driven AI navigator for learning and career development. It establishes an authentic, continuous closed loop:
```text
Person → Understanding → Assessment → Goal → Career Path → Roadmap → Learning → Evidence → Mastery → Adaptation → Opportunities → Execution → Memory → Longitudinal Growth
```
Downstream milestones unlock solely through empirical evaluation of real work artifacts (git repositories, executable source code, test suites). The system remembers breakthroughs, adapts plans dynamically when constraints change, and matches learners to real opportunities with transparent fit versus readiness explainability.

---

## 2. Core Differentiation

| Dimension | Generic AI Chatbot / Copilot | Course Library (Coursera/Udemy) | Job Board (LinkedIn/Indeed) | **PATHMIND** |
| :--- | :--- | :--- | :--- | :--- |
| **Persistence** | Session-only; ephemeral context | Stores completion %; zero cognitive state | Profile resume snapshot | **Longitudinal Learner Model & Persistent Second Brain** |
| **Progression Authority** | Self-reported or purely conversational | Passive video watch checks | None | **Evidence-Gated Progression (Code, Tests, Verifiable Proof)** |
| **Adaptability** | Stateless re-prompting required | Rigid syllabus; cannot adapt | Static search filters | **Continuous Impact Analysis & User-Approved Replanning** |
| **Opportunity Match** | Inaccessible or hallucinated links | Irrelevant affiliate courses | Arbitrary keyword/boolean filters | **Fit vs. Readiness Separation (What you have vs. what you need)** |
| **Data Authenticity** | Hallucinates plausible answers | Checkbox vanity | Fake/stale postings common | **Zero Mock Runtime Rule; Provenance Grounding on All Claims** |
| **Autonomy & Agency** | Passive responder | Fixed catalog | Direct spam | **The AI recommends; the authenticated person decides** |

---

## 3. Technology Architecture

* **Google Agent Development Kit (ADK) & Gemini 2.5 Flash / Pro**: Structured schema-controlled reasoning, multi-turn psychometric counseling, artifact code evaluation, and natural memory synthesis.
* **Personal Context Graph**: Server-side materialized graph connecting user identity, active goals, demonstrated capabilities, and constraints.
* **Persistent Second Brain & Longitudinal Learner Model**: Temporal validity, cross-stage transfer detection, semantic hybrid vector retrieval, and milestone tracking.
* **Deterministic State Authority**: Strict boundary ensuring that AI agents propose adaptations, but only deterministic business rules and authenticated user approvals commit state mutations.
* **Universal Opportunity Intelligence**: Ingestion from official portals and curated career transition data with provenance tracking.
* **Zero-Mock Production Persistence**: Real Firestore document storage with server-side tenant isolation (`X-Person-ID` ownership enforcement).

---

## 4. Pitch Claim Validation Matrix

Every capability promoted during pitches has been audited and classified according to actual implementation and verification status:

| Pitch Claim | Classification | Evidence & Grounding |
| :--- | :--- | :--- |
| **"Progress is gated by real code evidence, not checkboxes"** | `DEMONSTRABLE` | Backend lock enforcement strictly blocks locked stages; passing test suites unlock downstream stages ([`test_roadmap_progressive.py`](file:///d:/learning%20path%20hackathon/backend/tests/test_roadmap_progressive.py)). |
| **"System remembers past breakthroughs to guide future recommendations"** | `DEMONSTRABLE` | Second Brain natural recall and cross-stage bridge detection query real historical memory events ([`test_second_brain.py`](file:///d:/learning%20path%20hackathon/backend/tests/test_second_brain.py)). |
| **"Roadmap adapts dynamically when real-life constraints change"** | `DEMONSTRABLE` | Constraint adaptation alters pacing and schedules while strictly preserving completed stages ([`test_adaptation_engine.py`](file:///d:/learning%20path%20hackathon/backend/tests/test_adaptation_engine.py)). |
| **"Opportunity matching distinguishes fit from readiness"** | `DEMONSTRABLE` | Evaluates requirements against demonstrated capabilities; flags unknown fields honestly rather than guessing ([`test_opportunity_intelligence.py`](file:///d:/learning%20path%20hackathon/backend/tests/test_opportunity_intelligence.py)). |
| **"Strict zero-mock data discipline across production runtime"** | `DEMONSTRABLE` | Audit verified 0 mock users, 0 demo shortcuts, and authentic empty states ([`test_production_security.py`](file:///d:/learning%20path%20hackathon/backend/tests/test_production_security.py)). |
| **"Multi-tenant data isolation and IDOR prevention"** | `DEMONSTRABLE` | Verified cross-tenant isolation where Person B cannot read or mutate Person A's data ([`test_production_security.py`](file:///d:/learning%20path%20hackathon/backend/tests/test_production_security.py)). |
| **"Live GitHub repository automated AST code evaluation"** | `DEMONSTRABLE` | Artifact Intelligence inspects AST complexity, imports, tests, and security ([`test_artifact_intelligence.py`](file:///d:/learning%20path%20hackathon/backend/tests/test_artifact_intelligence.py)). |
| **"Unified multi-agent orchestrator with loop prevention"** | `DEMONSTRABLE` | Task classification routes directly to domain agents with idempotency and cycle guards ([`test_orchestrator.py`](file:///d:/learning%20path%20hackathon/backend/tests/test_orchestrator.py)). |
| **"Proactive notifications on evidence drift and deadlocks"** | `DEMONSTRABLE` | Proactive engine generates intervention events with cooldowns and user dismissal ([`test_proactive_engine.py`](file:///d:/learning%20path%20hackathon/backend/tests/test_proactive_engine.py)). |
| **"Automated employer application submission on user behalf"** | `NOT_IMPLEMENTED` | Deliberately excluded: PATHMIND prepares materials; the person submits directly. |

---

## 5. External Dependencies & Failure Resilience

| Provider / Dependency | Role | Current Availability | Offline / Failure Behavior |
| :--- | :--- | :--- | :--- |
| **Gemini API (Google ADK)** | Deep reasoning & artifact evaluation | Operational via server-side key | Returns structured fallback evaluation or returns honest `SERVICE_UNAVAILABLE` without corrupting state. |
| **Firestore (GCP)** | Production state persistence | Operational | In-memory thread-safe dictionary fallback for local development and test runners. |
| **ESCO Classification API** | Official European Skills & Occupations | Operational (live API) | Cached local taxonomy with standard occupational descriptors. |
| **GitHub REST API** | Artifact code & repository inspection | Operational (public rate limit) | Validates URLs, checks commit metadata, and safely bounds payloads. |

---

## 6. Known Honest Limitations

1. **Static Export for Frontend**: The Next.js client is deployed as a high-performance static build on GitHub Pages (`basePath: "/pathmind"`), connecting to the Render backend. During cold backend starts (free-tier dormancy), the initial ping may take 20-30 seconds to wake.
2. **Third-Party Job Application APIs**: Job application workflows prepare tailored resumes, verification evidence packages, and interview preparation questions, but do not execute live automated submissions into third-party Applicant Tracking Systems (ATS).
3. **Offline Evaluation Ceiling**: Without live Gemini API credentials, code evidence evaluation falls back to deterministic AST parser assertions and test suite status checks.
