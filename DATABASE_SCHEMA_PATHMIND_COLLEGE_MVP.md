# PATHMIND — College Engineering MVP
## Firestore Database Schema

**Database:** Cloud Firestore  
**Auth:** Firebase Authentication  
**Primary tenant boundary:** authenticated learner UID

---

# 1. Design principles

1. One learner owns their private learner-scoped data.
2. Public/verified knowledge is separate from private learner memory.
3. Source provenance is mandatory for externally retrieved knowledge.
4. Academic curriculum is versioned.
5. Study plans are versioned.
6. Assessments are immutable after publication/submission except for administrative corrections.
7. Memory is typed and confidence/provenance aware.
8. Accountability events are timestamped.
9. No fake default learner IDs.
10. No fake resources or PYQs.

Firestore supports hierarchical documents/subcollections and flexible document structures, while access control should be enforced with Firebase Authentication + Security Rules for web/mobile clients or IAM for server-side access. citeturn756633search9turn756633search6

---

# 2. Top-level collections

```text
users/{uid}
universities/{universityId}
programs/{programId}
subjects/{subjectId}
curricula/{curriculumId}
source_records/{sourceId}
resource_records/{resourceId}
pyq_sets/{pyqSetId}
pyq_questions/{questionId}
assessment_blueprints/{assessmentId}
knowledge_topics/{topicId}
```

User-specific collections:

```text
users/{uid}/academic_context/{contextId}
users/{uid}/goals/{goalId}
users/{uid}/subject_profiles/{subjectId}
users/{uid}/learning_plans/{planId}
users/{uid}/learning_activities/{activityId}
users/{uid}/assessments/{assessmentId}
users/{uid}/assessment_results/{resultId}
users/{uid}/evidence/{evidenceId}
users/{uid}/memories_short/{memoryId}
users/{uid}/memories_long/{memoryId}
users/{uid}/learning_signals/{signalId}
users/{uid}/accountability_commitments/{commitmentId}
users/{uid}/study_sessions/{sessionId}
users/{uid}/progress_events/{eventId}
users/{uid}/chat_sessions/{sessionId}
users/{uid}/chat_messages/{messageId}
users/{uid}/preferences/{preferenceId}
```

---

# 3. users/{uid}

```json
{
  "uid": "firebase-auth-uid",
  "name": "Akshat",
  "email": "student@example.com",
  "photo_url": null,
  "created_at": "timestamp",
  "updated_at": "timestamp",
  "last_login_at": "timestamp",
  "profile_status": "INITIALIZED",
  "primary_university_id": "univ_xyz",
  "primary_program_id": "program_cse_xyz",
  "primary_branch": "COMPUTER_SCIENCE",
  "current_semester": 5,
  "current_academic_year": "2026-27",
  "supported_path": "COMPUTER_SCIENCE",
  "timezone": "Asia/Kolkata",
  "locale": "en-IN"
}
```

### supported_path enum

```text
MECHANICAL_ENGINEER
ELECTRICAL_ENGINEER
COMPUTER_SCIENCE_ENGINEER
AI_ENGINEER
CIVIL_ENGINEER
GENERAL_OTHER
```

`GENERAL_OTHER` is for aspirations outside the five deeply supported paths.

---

# 4. universities/{universityId}

```json
{
  "name": "Example University",
  "normalized_name": "example university",
  "country": "India",
  "state": "Rajasthan",
  "official_domain": "example.edu.in",
  "official_url": "https://example.edu.in",
  "verification_status": "VERIFIED",
  "source_id": "source_123",
  "last_verified_at": "timestamp",
  "aliases": ["Example Univ"],
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

---

# 5. programs/{programId}

```json
{
  "university_id": "univ_xyz",
  "name": "B.Tech Computer Science and Engineering",
  "normalized_name": "btech computer science engineering",
  "degree": "BTECH",
  "branch": "COMPUTER_SCIENCE",
  "supported_path": "COMPUTER_SCIENCE_ENGINEER",
  "duration_semesters": 8,
  "source_ids": ["source_123"],
  "effective_from": "2026-07-01",
  "effective_to": null,
  "version": 2,
  "verification_status": "VERIFIED"
}
```

---

# 6. curricula/{curriculumId}

```json
{
  "university_id": "univ_xyz",
  "program_id": "program_xyz",
  "academic_year": "2026-27",
  "semester": 5,
  "version": 1,
  "source_ids": ["source_123", "source_456"],
  "verification_status": "VERIFIED",
  "effective_from": "2026-07-01",
  "created_at": "timestamp"
}
```

Subcollection:

```text
curricula/{curriculumId}/subjects/{subjectId}
```

---

# 7. curricula/{curriculumId}/subjects/{subjectId}

```json
{
  "code": "CS501",
  "name": "Data Structures",
  "credits": 4,
  "lecture_hours": 3,
  "practical_hours": 2,
  "units": [
    {
      "unit": 1,
      "title": "Arrays and Linked Lists",
      "topics": ["..."],
      "source_ids": ["source_123"]
    }
  ],
  "assessment_pattern": {
    "internal": 30,
    "external": 70
  },
  "source_ids": ["source_123"],
  "verification_status": "VERIFIED"
}
```

---

# 8. source_records/{sourceId}

This is one of the most important collections.

```json
{
  "url": "https://example.edu.in/syllabus.pdf",
  "canonical_url": "https://example.edu.in/syllabus.pdf",
  "title": "B.Tech CSE Semester 5 Syllabus",
  "domain": "example.edu.in",
  "provider_name": "Example University",
  "provider_type": "UNIVERSITY",
  "source_tier": "A",
  "source_type": "OFFICIAL_SYLLABUS",
  "author": null,
  "published_at": null,
  "retrieved_at": "timestamp",
  "last_verified_at": "timestamp",
  "verification_status": "VERIFIED",
  "content_hash": "sha256...",
  "mime_type": "application/pdf",
  "language": "en",
  "content_available": true,
  "extracted_text_ref": "storage/path/or/document/ref",
  "transcript_ref": null,
  "topic_ids": ["topic_1", "topic_2"],
  "curriculum_ids": ["curriculum_123"],
  "quality_signals": {
    "domain_authority": 1.0,
    "curriculum_match": 0.98,
    "freshness": 0.95,
    "reachability": 1.0
  },
  "notes": "Official university syllabus",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

---

# 9. resource_records/{resourceId}

```json
{
  "title": "Understanding Linked Lists",
  "resource_type": "VIDEO",
  "provider": "NPTEL",
  "url": "https://...",
  "source_id": "source_abc",
  "source_tier": "B",
  "verification_status": "VERIFIED",
  "difficulty": "FOUNDATION",
  "estimated_minutes": 42,
  "language": "en",
  "topic_ids": ["linked_lists"],
  "curriculum_ids": ["curriculum_123"],
  "relevant_sections": [],
  "video_timestamps": [
    {
      "start_seconds": 1080,
      "end_seconds": 2040,
      "purpose": "Core concept"
    }
  ],
  "document_sections": [],
  "last_verified_at": "timestamp",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

---

# 10. pyq_sets/{pyqSetId}

```json
{
  "university_id": "univ_xyz",
  "program_id": "program_xyz",
  "semester": 5,
  "subject_id": "subject_xyz",
  "exam_year": 2025,
  "exam_type": "END_SEMESTER",
  "source_id": "source_pyq",
  "verification_status": "VERIFIED",
  "question_count": 12,
  "created_at": "timestamp"
}
```

---

# 11. pyq_questions/{questionId}

```json
{
  "pyq_set_id": "pyq_123",
  "question_number": "Q3",
  "question_text": "...",
  "marks": 10,
  "topic_ids": ["linked_lists"],
  "unit": 1,
  "difficulty": "MEDIUM",
  "source_id": "source_pyq",
  "verification_status": "VERIFIED"
}
```

---

# 12. users/{uid}/academic_context/{contextId}

```json
{
  "university_id": "univ_xyz",
  "program_id": "program_xyz",
  "branch": "COMPUTER_SCIENCE",
  "semester": 5,
  "academic_year": "2026-27",
  "subjects": ["subject_1", "subject_2"],
  "exam_window": {
    "start": "timestamp",
    "end": "timestamp"
  },
  "available_hours_per_week": 14,
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

---

# 13. users/{uid}/goals/{goalId}

```json
{
  "goal_type": "SEMESTER_EXAM",
  "raw_goal": "I want to score 8.5+ this semester",
  "normalized_goal": "IMPROVE_SEMESTER_PERFORMANCE",
  "target_subject_ids": ["subject_1"],
  "target_score": 8.5,
  "deadline": "timestamp",
  "status": "ACTIVE",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

---

# 14. users/{uid}/subject_profiles/{subjectId}

```json
{
  "subject_id": "subject_1",
  "confidence": 0.42,
  "strengths": ["theory"],
  "weaknesses": ["numericals"],
  "mastered_topics": ["topic_a"],
  "weak_topics": ["topic_b"],
  "attempt_count": 4,
  "last_assessment_score": 61,
  "trend": "IMPROVING",
  "updated_at": "timestamp"
}
```

---

# 15. users/{uid}/learning_plans/{planId}

```json
{
  "goal_id": "goal_123",
  "curriculum_id": "curriculum_123",
  "subject_scope": ["subject_1"],
  "plan_type": "SEMESTER_PREPARATION",
  "version": 3,
  "status": "ACTIVE",
  "generated_from": {
    "assessment_ids": ["assessment_1"],
    "source_ids": ["source_1", "source_2"],
    "memory_ids": ["memory_1"]
  },
  "start_date": "timestamp",
  "target_date": "timestamp",
  "created_at": "timestamp"
}
```

Subcollection:

```text
users/{uid}/learning_plans/{planId}/phases/{phaseId}
```

---

# 16. learning plan phase

```json
{
  "order": 1,
  "title": "Arrays Foundations",
  "objective": "Understand and apply array operations",
  "status": "AVAILABLE",
  "unlock_rule": {
    "required_assessment_score": 70,
    "required_activity_count": 4,
    "required_pyq_accuracy": 0.65
  },
  "resource_ids": ["resource_1", "resource_2"],
  "pyq_question_ids": ["pyq_q1", "pyq_q2"],
  "assessment_id": "assessment_1",
  "created_at": "timestamp"
}
```

---

# 17. users/{uid}/learning_activities/{activityId}

```json
{
  "plan_id": "plan_123",
  "phase_id": "phase_1",
  "activity_type": "WATCH",
  "resource_id": "resource_1",
  "order": 1,
  "instructions": "Watch the 18:00–34:00 section, then write three key ideas.",
  "status": "COMPLETED",
  "started_at": "timestamp",
  "completed_at": "timestamp",
  "completion_evidence": {
    "type": "SELF_REPORT",
    "ref": null
  }
}
```

---

# 18. users/{uid}/assessments/{assessmentId}

```json
{
  "plan_id": "plan_123",
  "phase_id": "phase_1",
  "subject_id": "subject_1",
  "topic_ids": ["topic_a", "topic_b"],
  "assessment_type": "MIXED",
  "version": 1,
  "status": "SUBMITTED",
  "question_ids": ["q1", "q2", "q3"],
  "knowledge_basis": {
    "resource_ids": ["resource_1", "resource_2"],
    "pyq_question_ids": ["pyq1"]
  },
  "created_at": "timestamp",
  "submitted_at": "timestamp"
}
```

---

# 19. users/{uid}/assessment_results/{resultId}

```json
{
  "assessment_id": "assessment_1",
  "score": 78,
  "normalized_score": 0.78,
  "mastery_status": "MASTERED",
  "topic_results": [
    {
      "topic_id": "topic_a",
      "score": 0.88,
      "status": "STRONG"
    },
    {
      "topic_id": "topic_b",
      "score": 0.55,
      "status": "WEAK"
    }
  ],
  "feedback": "Strong conceptual understanding; more practice needed for numerical application.",
  "evaluation_confidence": 0.84,
  "created_at": "timestamp"
}
```

---

# 20. users/{uid}/evidence/{evidenceId}

```json
{
  "type": "PDF",
  "title": "Semester Notes",
  "storage_ref": "gs://...",
  "source_url": null,
  "related_subject_id": "subject_1",
  "related_phase_id": "phase_1",
  "verification_status": "SUBMITTED",
  "verification_reason": null,
  "content_hash": "sha256...",
  "created_at": "timestamp",
  "verified_at": null
}
```

---

# 21. users/{uid}/memories_short/{memoryId}

```json
{
  "session_id": "session_123",
  "memory_type": "CURRENT_CONTEXT",
  "content": "Learner is currently revising Unit 2 for semester exams.",
  "topic_ids": ["topic_2"],
  "confidence": 0.99,
  "source_message_ids": ["message_1", "message_2"],
  "expires_at": "timestamp",
  "created_at": "timestamp"
}
```

Short-term memories are optimized for active conversations.

---

# 22. users/{uid}/memories_long/{memoryId}

```json
{
  "memory_type": "LEARNING_PREFERENCE",
  "content": "Learner prefers worked examples before theory explanations.",
  "status": "ACTIVE",
  "confidence": 0.91,
  "source_type": "OBSERVED_BEHAVIOR",
  "source_refs": ["assessment_1", "session_4"],
  "first_observed_at": "timestamp",
  "last_confirmed_at": "timestamp",
  "importance": 0.82,
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

---

# 23. users/{uid}/learning_signals/{signalId}

```json
{
  "signal_type": "REPEATED_MISCONCEPTION",
  "subject_id": "subject_1",
  "topic_id": "topic_2",
  "description": "Confuses BFS traversal order with DFS.",
  "confidence": 0.88,
  "evidence_refs": ["assessment_1", "assessment_2"],
  "recommended_intervention": "Use visual graph traversal animation followed by practice.",
  "created_at": "timestamp"
}
```

---

# 24. users/{uid}/accountability_commitments/{commitmentId}

```json
{
  "title": "Complete Unit 2 practice set",
  "plan_id": "plan_123",
  "phase_id": "phase_2",
  "due_at": "timestamp",
  "estimated_minutes": 60,
  "status": "PLANNED",
  "completion_evidence_ref": null,
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

---

# 25. users/{uid}/chat_sessions/{sessionId}

```json
{
  "title": "Semester 5 CSE preparation",
  "started_at": "timestamp",
  "last_active_at": "timestamp",
  "current_subject_id": "subject_1",
  "current_topic_id": "topic_2",
  "current_plan_id": "plan_123",
  "status": "ACTIVE"
}
```

---

# 26. users/{uid}/chat_messages/{messageId}

```json
{
  "session_id": "session_123",
  "role": "USER",
  "content": "I don't understand this derivation.",
  "timestamp": "timestamp",
  "memory_candidates": [],
  "source_refs": []
}
```

For large chat histories, consider sharding/archive rules rather than making one enormous document.

---

# 27. users/{uid}/study_sessions/{sessionId}

```json
{
  "plan_id": "plan_123",
  "started_at": "timestamp",
  "ended_at": "timestamp",
  "duration_minutes": 42,
  "activities_completed": ["activity_1", "activity_2"],
  "self_reported_focus": 4,
  "notes": "Numericals took longer than expected."
}
```

---

# 28. users/{uid}/progress_events/{eventId}

```json
{
  "event_type": "PHASE_COMPLETED",
  "entity_type": "PHASE",
  "entity_id": "phase_1",
  "metadata": {
    "assessment_id": "assessment_1",
    "score": 78
  },
  "timestamp": "timestamp"
}
```

This collection creates an audit trail for the learner journey.

---

# 29. indexes / query patterns

Expected queries include:

- user by uid
- current academic context by learner
- active goal by learner
- current plan by learner
- active phase by plan
- recent short-term memories by session
- active long-term memories by type
- weak topics by subject
- assessment results by topic
- upcoming accountability commitments
- curriculum by university/program/semester
- resources by topic/curriculum/verification_status
- PYQs by university/semester/subject/year

Create Firestore indexes only for actual observed compound queries.

---

# 30. Security model

### Learner-private collections

All `users/{uid}/...` documents are private to the authenticated UID.

### Shared knowledge collections

These are readable by authenticated learners only when the resource/source is in an approved state.

### Admin/provider writes

University/curriculum/source records should be writable only through trusted server-side services or authorized administrative flows.

### Important Firebase behavior

Firestore Security Rules control mobile/web client access, while server client libraries use IAM/credentials and bypass Firestore Security Rules. Therefore, the architecture should avoid exposing unrestricted Firestore access to the web app and should enforce server-side authorization as well. citeturn756633search6turn756633search2

---

# 31. Atomic progression

When an assessment changes phase state, the update may need to atomically update:

```text
assessment_result
phase.status
next_phase.status
progress_event
subject_profile
```

Use a Firestore transaction or batch where the consistency requirement is real. Firestore supports atomic transactions and batched writes. citeturn756633search0

---

# 32. No fake-state rule

The database must never store:

- fabricated assessment scores
- fabricated completions
- fabricated PYQs
- fabricated source records
- fabricated resources
- fabricated learner memories
- fake default learners

Unavailable state must be explicit.

Examples:

```text
NOT_AVAILABLE
UNVERIFIED
INSUFFICIENT_EVIDENCE
SOURCE_UNAVAILABLE
PYQ_NOT_AVAILABLE
```

---

# 33. Future extensibility

The schema intentionally supports adding later:

- more engineering branches
- additional universities
- non-engineering colleges
- placements
- internships
- certifications
- school learners
- working professionals

without changing the core learner-memory-learning architecture.
