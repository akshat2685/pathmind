# PATHMIND — College Engineering MVP
## Technical Requirements Document (TRD)

**Version:** 1.0

---

## 1. Technical architecture

```text
                         LEARNER
                            |
                            v
                    NEXT.JS WEB APP
                            |
                     Firebase Auth
                            |
                            v
                     FASTAPI BACKEND
                            |
                     ID TOKEN VERIFY
                            |
                            v
                     ADK ROOT AGENT
                            |
        +-------------------+-------------------+
        |                   |                   |
        v                   v                   v
  Academic Agent      Learning Agent     Accountability Agent
        |                   |                   |
        +-------------------+-------------------+
                            |
                     ADK TOOLS / SERVICES
                            |
        +-------------------+-------------------------+
        |                   |                         |
        v                   v                         v
   Learner State       Knowledge/RAG             Progress Engine
        |                   |                         |
        v                   v                         v
    Firestore       Source Retriever           Firestore
                            |
                 +----------+----------+
                 |                     |
                 v                     v
          Official University     Verified Learning
              Sources               Resources
```

---

## 2. Technology stack

### Frontend

- Next.js 15.x / App Router
- TypeScript
- Tailwind CSS v4
- shadcn/base-ui
- Framer Motion
- Firebase Authentication client SDK

Preserve the current PATHMIND visual system.

### Backend

- Python
- FastAPI
- Uvicorn
- Pydantic
- Google ADK
- Gemini
- Firebase Admin SDK / Google Cloud Firestore

### Database

- Cloud Firestore

### Authentication

- Firebase Authentication

Recommended MVP authentication methods:

- Google sign-in
- email/password or email-link, depending on the supplied login design

Exact UX should follow the existing login design.

### Hosting

Current PATHMIND deployment pattern may remain:

- frontend: GitHub Pages or the team's selected web host
- backend: Render or equivalent managed runtime
- Firestore/Firebase: Google Cloud/Firebase

Do not change hosting solely for architecture aesthetics.

---

## 3. Authentication flow

```text
Login UI
   |
   v
Firebase Auth
   |
   v
ID token
   |
   v
Frontend API request
   |
Authorization: Bearer <token>
   |
   v
FastAPI
   |
Firebase Admin token verification
   |
   v
person_id / auth.uid
```

Every learner-scoped request must resolve identity from authenticated credentials.

Do not accept arbitrary learner IDs from the client as authoritative identity.

---

## 4. Agent architecture

Use one learner-facing root agent with specialized sub-agents/services where helpful.

Conceptual structure:

```text
RootLearnerAgent
│
├── ProfileContextAgent
├── AcademicPlanningAgent
├── SourceResearchAgent
├── LearningCoachAgent
├── AssessmentAgent
├── AccountabilityAgent
└── MemoryService
```

Avoid creating a large swarm of agents.

The root agent should orchestrate; deterministic services should enforce product rules.

---

## 5. ADK role

The product must use actual Google ADK orchestration.

ADK is responsible for:

- agent definition
- tool invocation
- delegation where needed
- session context
- agent-level orchestration

Narrow tools should be exposed rather than unrestricted database access.

Possible tools:

```text
get_learner_profile()
get_academic_context()
get_current_semester()
get_current_subjects()
get_active_goal()
get_learning_preferences()
search_university_sources()
get_verified_curriculum()
get_verified_resources()
get_verified_pyqs()
create_study_plan()
evaluate_source()
create_assessment()
evaluate_assessment()
record_learning_signal()
record_memory()
retrieve_short_term_memory()
retrieve_long_term_memory()
create_accountability_commitment()
get_accountability_state()
update_progress()
```

Tools should be typed and scoped.

The agent should not have generic `firestore_query()` or unrestricted database access.

---

## 6. Gemini role

Gemini handles:

- conversation
- intent understanding
- structured extraction
- explanation
- personalized teaching
- assessment generation where appropriate
- open-ended assessment evaluation where appropriate
- synthesis of learner evidence
- study strategy recommendations

Deterministic application code handles:

- auth
- identity
- state transitions
- source verification status
- schedule calculations
- exam countdown calculations
- progress persistence
- assessment scoring rules where objective
- unlock rules
- permissions
- database writes

---

## 7. University research pipeline

This is one of the most important technical components.

### Input

```text
university
college
branch/course
semester
subject
exam objective
```

### Pipeline

```text
Learner request
      |
      v
University resolver
      |
      v
Canonical university entity
      |
      v
Source discovery
      |
      v
Official source prioritization
      |
      v
Document/page retrieval
      |
      v
Content extraction
      |
      v
Normalization
      |
      v
Verification
      |
      v
Source pack
      |
      v
Curriculum/topic mapping
```

---

## 8. Source verification architecture

A source should not be considered trusted because Gemini says it is trustworthy.

Trust must be based on observable provenance and rules.

### Source evaluation signals

- domain authority
- institution identity
- URL reachability
- document metadata
- source type
- publication date if available
- curriculum match
- topic match
- duplication/corroboration
- extraction quality
- freshness

### Source status

```text
DISCOVERED
FETCHED
PARSED
VERIFIED
STALE
UNVERIFIABLE
REJECTED
```

Only `VERIFIED` resources should be promoted into the recommended study plan.

---

## 9. Source hierarchy

Recommended priority:

```text
Tier A
Official university / university examination / official syllabus

Tier B
Official college/department / government / IIT/NPTEL/SWAYAM-style sources

Tier C
Established high-quality educational publishers/providers

Tier D
Community/educator material
```

Tier D can supplement but should not override an authoritative university syllabus.

---

## 10. Search and grounding

The knowledge layer may use Google Search grounding/search tools or an equivalent verified retrieval adapter, but the final application must persist the resulting source provenance.

A generated answer without source provenance must not be presented as a verified university-specific fact.

---

## 11. Curriculum model

Curriculum should be represented as:

```text
University
  -> Program
      -> Branch
          -> Semester
              -> Subject
                  -> Unit
                      -> Topic
```

Each node should support:

- source reference
- syllabus text
- effective academic year
- version
- confidence

A learner plan should use the specific curriculum version applicable to the learner where available.

---

## 12. PYQ pipeline

```text
University + Course + Semester + Subject
        |
        v
PYQ source discovery
        |
        v
Document retrieval
        |
        v
Parsing / extraction
        |
        v
Question normalization
        |
        v
Topic mapping
        |
        v
Difficulty classification
        |
        v
Learning-plan integration
```

The system should never invent PYQs.

If PYQs cannot be verified:

```text
PYQ_NOT_AVAILABLE
```

must be returned internally and the learner told clearly that verified PYQs were unavailable.

---

## 13. Resource pipeline

Each study plan item must contain more than a link.

```text
Resource
 ├── metadata
 ├── source provenance
 ├── content type
 ├── coverage
 ├── relevant sections/pages/timestamps
 ├── estimated time
 ├── prerequisite level
 ├── learning role
 └── next action
```

Example:

```text
1. Watch 18:20–34:10 of Video A
2. Read pages 12–19 of Document B
3. Solve Questions 1–8
4. Attempt PYQ 2024 Q3
5. Complete checkpoint assessment
```

---

## 14. Learning engine

The learning engine creates ordered activities.

Possible activity types:

- WATCH
- READ
- PRACTICE
- SOLVE_PYQ
- BUILD
- EXPLAIN
- REFLECT
- REVIEW
- ASSESS

The activity sequence is personalized.

---

## 15. Assessment engine

The assessment engine must use the actual resources/learning activities that the learner was exposed to.

Inputs:

- learner profile
- semester
- subject
- topic
- target objective
- resources completed
- prior assessment performance
- known weaknesses
- question history

Assessment types:

- MCQ
- short answer
- numerical/problem solving
- explanation
- practical/task-based

The model should not generate answers or scores before the learner responds.

---

## 16. Assessment integrity

Store:

- assessment blueprint
- question IDs
- source/knowledge basis
- learner responses
- evaluation results
- timestamp
- assessment version

Objective answers should be scored deterministically where possible.

LLM-based evaluation should return structured reasoning signals and confidence, and should not silently convert uncertain grading into false precision.

---

## 17. Personalization engine

Maintain a learner learning-profile vector/state such as:

```text
learning_preferences
content_preferences
pace
common_error_types
strong_subjects
weak_subjects
confidence_by_subject
preferred_language
preferred_explanation_style
resource_effectiveness
assessment_patterns
```

Do not reduce the learner to one personality score.

---

## 18. Memory architecture

### Short-term

Session-scoped or task-scoped context:

```text
current conversation
current task
current subject
current topic
current sources
current assessment
current misconceptions
```

### Long-term

Persistent cross-session memory:

```text
stable learner preferences
recurring misconceptions
academic history
previous plans
completed phases
assessment trends
resource effectiveness
goals
accountability commitments
important decisions
```

Use explicit memory types and provenance.

---

## 19. Memory write policy

Not every message becomes long-term memory.

A candidate memory should be evaluated for:

- stability
- usefulness
- future relevance
- confidence
- sensitivity
- redundancy

Examples worth storing:

> Prefers examples before theory.

> Repeatedly struggles with Laplace-transform algebra.

> Has a 25 May university exam for Subject X.

Examples that may remain short-term only:

> Can you explain this one line again?

---

## 20. Accountability engine

Create a commitment model:

```text
Commitment
 ├── learner
 ├── task
 ├── deadline
 ├── expected_duration
 ├── status
 ├── source_plan
 └── completion_evidence
```

Status:

```text
PLANNED
IN_PROGRESS
COMPLETED
MISSED
RESCHEDULED
CANCELLED
```

Never mark completed from a UI click alone if the product requires evidence.

---

## 21. Exam timeline engine

Input:

- exam date
- syllabus scope
- learner weekly availability
- subject difficulty
- topic mastery
- remaining workload

Output:

- remaining days
- priority subjects/topics
- weekly schedule
- revision windows
- PYQ windows
- assessment checkpoints
- buffer time

All date calculations are deterministic.

---

## 22. API surface

Conceptual API endpoints:

```text
POST /api/auth/session
GET  /api/learner/profile
PATCH /api/learner/profile
POST /api/agent/interact
GET  /api/academic/universities/search
GET  /api/academic/curriculum
GET  /api/academic/subjects
GET  /api/academic/pyqs
POST /api/sources/verify
GET  /api/resources/recommended
POST /api/learning/plans
GET  /api/learning/plans/current
POST /api/learning/activities/:id/complete
POST /api/assessments
POST /api/assessments/:id/submit
GET  /api/assessments/:id/result
GET  /api/memory/short-term
GET  /api/memory/long-term
POST /api/memory/feedback
POST /api/accountability/commitments
GET  /api/accountability/today
GET  /api/accountability/progress
```

Final route naming should follow existing project conventions.

---

## 23. Structured agent response

```json
{
  "message": "Here is your plan for Unit 2.",
  "state": "LEARNING",
  "ui_blocks": [
    {
      "type": "LEARNING_PLAN",
      "data": {
        "subject": "...",
        "steps": []
      }
    },
    {
      "type": "RESOURCE_LIST",
      "data": {
        "resources": []
      }
    },
    {
      "type": "NEXT_ACTION",
      "data": {
        "label": "Start checkpoint"
      }
    }
  ],
  "sources": []
}
```

---

## 24. Error model

Never fake success.

Use explicit machine-readable errors/states:

```text
AUTH_REQUIRED
UNIVERSITY_NOT_FOUND
CURRICULUM_NOT_FOUND
SOURCE_UNAVAILABLE
SOURCE_UNVERIFIABLE
PYQ_NOT_AVAILABLE
RESOURCE_NOT_VERIFIED
INSUFFICIENT_EVIDENCE
ASSESSMENT_UNAVAILABLE
PERSISTENCE_UNAVAILABLE
MEMORY_NOT_FOUND
GOAL_NOT_SUPPORTED_DEEPLY
```

---

## 25. Deployment and observability

Log structured events for:

- agent request
- tool call
- source retrieval
- source verification
- assessment generation
- assessment submission
- memory retrieval
- memory write
- progress update
- accountability reminder

Do not log raw sensitive learner content unless necessary.

Track latency by stage so slow source retrieval or agent calls can be diagnosed.

---

## 26. Security

Authentication must be verified server-side.

Learner data must be isolated by authenticated UID.

Admin/service credentials must never be exposed to the frontend.

Firestore access must follow appropriate Security Rules for any direct client access, and server-side Admin SDK access must use IAM/credentials. Firebase documents that mobile/web client libraries use Security Rules, while server client libraries bypass those rules and therefore require IAM. citeturn756633search6turn756633search2

Use transactions for atomic progression updates where multiple documents need to change together. Firestore supports atomic transactions and batched writes. citeturn756633search0

---

## 27. Testing strategy

### Unit tests

- source verification
- topic mapping
- semester calculation
- assessment scoring
- memory classification
- timeline calculations
- progression rules

### Integration tests

- login -> learner creation
- learner -> university search
- university -> curriculum retrieval
- curriculum -> learning plan
- learning plan -> assessment
- assessment -> baseline
- baseline -> pathway
- memory across sessions

### Acceptance tests

A fresh learner should be able to:

1. log in
2. select university
3. select branch/path
4. select semester
5. select subject or broad semester goal
6. receive verified curriculum context
7. receive ordered verified resources
8. study
9. ask questions
10. complete assessment
11. receive strength/weakness feedback
12. receive the next personalized phase
13. return later and have PATHMIND remember the journey

---

## 28. Technical principle

The architecture must remain generic within the engineering-college domain.

Do not write five separate systems.

Use:

```text
university
+
course
+
semester
+
subject
+
learner evidence
+
assessment
+
learning behavior
+
exam timeline
+
verified knowledge
→
personalized learner state
```

The five supported paths are curated knowledge coverage, not five hardcoded application branches.

