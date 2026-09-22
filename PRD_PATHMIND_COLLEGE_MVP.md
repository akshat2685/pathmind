# PATHMIND — College Engineering MVP
## Product Requirements Document (PRD)

**Version:** 1.0  
**Scope:** College-only MVP for engineering students  
**Primary market:** Engineering colleges in India  
**UI/UX:** Preserve the existing PATHMIND Living Sketchbook design system  
**Authentication:** Login-first; existing login design will be implemented as the entry experience

---

## 1. Product decision

PATHMIND is narrowing from a broad lifelong learning/career platform to a focused college product to validate whether students actually use it.

The MVP serves engineering-college learners and focuses on five target paths:

1. Mechanical Engineer
2. Electrical Engineer
3. Computer Science / Software Engineer
4. AI Engineer
5. Civil Engineer

The product will remain extensible, but these five paths receive the deepest knowledge, assessment, roadmap, resource, and personalization coverage.

The MVP is intentionally not a universal career platform.

---

## 2. Core product promise

PATHMIND should behave like a persistent academic and career-learning companion that knows:

- who the learner is
- which university they attend
- which engineering branch/path they are pursuing
- which semester they are in
- what subjects they are studying
- what their goals are
- what their strengths and weaknesses are
- how they learn best
- what resources they have already used
- what they have struggled with
- what assessments they have completed
- what progress they have made
- what they should do next

The product should not merely answer questions.

It should continuously convert the learner's current academic situation into a personalized study path.

---

## 3. MVP learner journey

### Entry

The learner first logs in.

After authentication, PATHMIND begins the learner profile conversation.

### Step 1 — Identity

Collect and persist:

- name
- university
- college/institute
- engineering branch/course
- semester
- academic year

### Step 2 — Purpose

Ask what the learner is trying to achieve.

Examples:

- score well in the current semester
- prepare for university exams
- understand subjects deeply
- clear a specific subject
- improve CGPA
- prepare for placements
- become job-ready for the selected engineering path
- prepare for a specific subject exam
- learn a topic deeply

The learner may also give an aspiration outside the five supported target paths.

### Step 3 — Supported path decision

If the aspiration belongs to one of the five supported paths, use the specialized PATHMIND engineering journey.

If the aspiration is outside the five supported paths, do NOT reject it.

Instead:

- acknowledge it
- provide a basic/high-level learning path
- explain that the current MVP has deeper personalization for the five supported engineering paths
- still use the general learning/accountability agent where possible

This is a product boundary, not a refusal.

### Step 4 — Academic context

Determine:

- university
- branch/course
- semester
- subjects
- exam dates or expected exam window
- desired score/grade/CGPA
- current confidence per subject
- available weekly time
- preferred learning style

### Step 5 — Evidence collection

The learner can provide:

- syllabus
- course outline
- subject list
- university links
- notes
- assignments
- previous marks
- PYQs
- textbooks
- reference material
- project work
- class notes
- assessment results

PATHMIND analyzes the evidence and detects what is already known.

### Step 6 — University/source research

PATHMIND researches the learner's university + course + semester.

Priority:

1. official university academic pages
2. official syllabus/regulations
3. official examination/PYQ repositories
4. official department/college pages
5. high-quality educational sources
6. verified open educational resources

Every recommended resource must have provenance and verification metadata.

### Step 7 — Personalized baseline

PATHMIND determines:

- strengths
- weaknesses
- prerequisite gaps
- concept gaps
- likely high-value topics
- exam-oriented gaps
- practical/understanding gaps
- learning preferences
- study behavior

The system must distinguish between:

- verified fact
- learner-reported information
- inferred signal
- uncertain hypothesis

### Step 8 — Personalized learning path

PATHMIND generates the next learning sequence.

Example:

```text
1. Watch the selected lecture/video.
2. Read the linked official/verified notes.
3. Solve these 10 concept questions.
4. Attempt this PYQ section.
5. Review incorrect answers.
6. Ask PATHMIND about anything unclear.
7. Take the checkpoint assessment.
8. Unlock the next topic if the mastery rule is satisfied.
```

The learner is told **what to do, in what order, and why**.

### Step 9 — Assessment

After a learning stage, PATHMIND generates or selects an assessment based on the exact material/resources used.

The learner completes the assessment.

PATHMIND evaluates mastery.

Possible outcomes:

- MASTERED
- PARTIALLY_MASTERED
- REINFORCEMENT_REQUIRED
- INSUFFICIENT_EVIDENCE

### Step 10 — Accountability

PATHMIND tracks:

- commitments
- planned study sessions
- missed actions
- completion streaks
- assessment performance
- deadlines
- exam dates
- time remaining

It should remind/challenge the learner based on actual state, not generic motivational text.

### Step 11 — Continuous adaptation

PATHMIND learns from every completed stage.

Examples:

- learner learns best from visual explanations
- learner consistently struggles with derivations
- learner performs well on theory but poorly on numericals
- learner prefers short videos followed by questions
- learner needs more spaced revision before PYQs

These become personalized learning signals and future memory.

---

## 4. Primary use cases

### UC-01 — Semester planning

Learner selects semester 3 and asks:

> Help me prepare for semester exams.

PATHMIND builds a semester plan using the verified university curriculum, exam window, current preparation and available study time.

### UC-02 — Single subject planning

Learner asks:

> I only want to prepare Data Structures for my semester exam.

PATHMIND limits the journey to that subject and does not generate an unrelated full-career roadmap.

### UC-03 — Specific topic help

Learner asks:

> Teach me Karnaugh maps for my Electrical Engineering exam.

PATHMIND uses the learner's current course context, learning preference and verified resources.

### UC-04 — PYQ preparation

PATHMIND identifies real previous-year questions from trusted sources, maps them to syllabus topics, and integrates them into the learning sequence.

### UC-05 — Weakness remediation

Learner repeatedly performs poorly on a concept.

PATHMIND changes the learning method and schedules reinforcement.

### UC-06 — Exam countdown

Learner gives the exam date.

PATHMIND reorganizes the sequence around the remaining time.

### UC-07 — Unsupported aspiration

Learner says:

> I want to become a photographer.

PATHMIND provides a basic pathway rather than rejecting the user, while clearly indicating that deeper college-engineering specialization is currently limited to the supported five paths.

---

## 5. Supported engineering depth

### Mechanical Engineer

Knowledge coverage should progressively include relevant engineering fundamentals and common mechanical subjects.

### Electrical Engineer

Coverage should include relevant electrical fundamentals, circuits, machines, power/electronics subjects according to the learner's curriculum.

### Computer Science / Software Engineer

Coverage should include programming, data structures, algorithms, computer systems, databases, software engineering, etc., according to university curriculum.

### AI Engineer

Coverage should include programming, mathematics, statistics, data structures, machine learning, deep learning and AI systems where relevant to the learner's program.

### Civil Engineer

Coverage should include relevant civil engineering fundamentals and core subjects according to the learner's curriculum.

The above are capability domains, not hardcoded semester syllabi. The learner's actual university curriculum remains authoritative for academic planning.

---

## 6. Source trust model

PATHMIND must not simply return links.

Each source becomes a structured SourceRecord with:

- title
- source type
- provider
- URL
- domain
- author/channel/institution
- publication date if available
- retrieved date
- syllabus/topic mapping
- verification status
- authority tier
- freshness
- content availability
- transcript/text extraction status where applicable

### Source tiers

**Tier A — authoritative**

- university official sites
- official syllabus documents
- official exam/PYQ repositories
- official government/education institutions
- institution-published course material

**Tier B — high-quality educational**

- NPTEL / SWAYAM
- IIT/IISc educational material
- reputable open educational institutions
- established academic publishers/resources

**Tier C — supporting resources**

- reputable educator websites
- high-quality educational video channels
- community resources with strong evidence of quality

Tier C cannot override a Tier A university requirement.

### Resource verification rule

A source is usable only if the system can verify:

- it is reachable
- it corresponds to the claimed topic
- it is appropriate for the learner's course/semester/level
- it is not obviously fabricated
- its provenance is stored

---

## 7. Resource experience

Resources are not displayed as an unstructured link list.

PATHMIND should create an ordered study plan:

```text
PHASE 1
Concept introduction

→ Video
→ Reading/notes
→ Worked example
→ Practice
→ PYQ
→ Reflection
→ Assessment
```

For videos, where technically available, store transcript/chapter information and tell the learner which portion to watch.

For documents, identify the relevant pages/sections.

For PYQs, map individual questions to topics where possible.

---

## 8. Personalized teaching behavior

The same content may be taught differently to different learners.

The agent can adapt based on stored learning preferences such as:

- prefers visual explanations
- prefers examples first
- prefers theory first
- prefers short videos
- prefers practice-heavy learning
- prefers step-by-step derivations
- prefers Hindi/English mix where supported
- prefers exam-oriented explanations
- prefers conceptual explanations

These are learning preferences, not fixed personality labels.

---

## 9. Memory

### Short-term memory

Used for the active session/task:

- current conversation
- current subject
- current semester
- current question
- current assessment
- resources already discussed
- immediate misconceptions
- current learning plan

### Long-term memory

Persisted across sessions:

- academic profile
- university
- course/branch
- semester history
- stable learning preferences
- recurring misconceptions
- assessment history
- completed phases
- performance trends
- prior resource effectiveness
- goals
- accountability commitments
- important learner decisions

The system must never invent memory.

---

## 10. Privacy boundary

A learner's personal memory is private.

No Student A data may be retrieved while answering Student B.

Shared knowledge may contain only generalized patterns without personally identifying learner history.

---

## 11. Accountability

The accountability agent can track:

- today's plan
- weekly plan
- semester plan
- deadlines
- exam dates
- planned study hours
- completed study hours where actually recorded
- missed commitments
- reinforcement tasks

Examples:

> You planned to finish Unit 2 by Wednesday. You are currently one task behind.

> Your exam is in 18 days. Based on the current verified syllabus and your remaining workload, the current plan needs adjustment.

The system must not claim a learner completed work unless actual evidence exists.

---

## 12. MVP success metrics

The iStart validation goal is adoption and usefulness, not feature count.

Primary metrics:

- login-to-first-study-plan conversion
- percentage of learners who complete initial profile
- percentage who start the first learning phase
- percentage who complete the first assessment
- weekly active learners
- repeat sessions per learner
- resource completion rate
- assessment completion rate
- learner-reported usefulness
- percentage returning for the second week
- percentage continuing into the second learning phase

Qualitative signals:

- learner feels understood
- recommendations match actual university requirements
- resources are genuinely useful
- learner understands what to do next
- learner trusts the sources
- learner feels accountability helps

---

## 13. Non-goals for this MVP

Do not build yet:

- school-student experience
- working-professional experience
- global career marketplace
- employer matching
- universal career graph
- full university ERP integration
- complete social network
- broad job board
- hundreds of career branches
- universal psychometric platform

Those can be added only after product usage validates demand.

---

## 14. Product principle

The MVP is successful when a student can say:

> "PATHMIND knows my university, my semester, my subjects, my strengths, my weaknesses, what resources I have already used, what I struggle with, what I need to do today, and what I should do next."

---
