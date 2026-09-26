"""
Clearly-labeled test fixtures for the college MVP test suite.

Seeds the in-memory fake Supabase client (see fake_supabase.py) with
canonical-looking but explicitly synthetic fixtures:
- "Anna University" (annauniv.edu) and "AICTE Model University"
  (univ_aicte_model), both marked VERIFIED
- one program per supported engineering branch at univ_aicte_model
- semester-3 curricula for all five branches, two subjects per branch,
  two units per subject
- a verified PYQ set for CS-301 containing question "Q1(a)"
- one VIDEO + one NOTES resource for CS-301 with timestamps/page refs

Nothing here is real institutional data; the values exist only so tests can
verify honest behavior (real lookups, real "not available" states).
"""

from fake_supabase import FakeSupabaseAdapter


BRANCHES = [
    "MECHANICAL_ENGINEER",
    "ELECTRICAL_ENGINEER",
    "COMPUTER_SCIENCE_ENGINEER",
    "AI_ENGINEER",
    "CIVIL_ENGINEER",
]

BRANCH_SUBJECTS = {
    "COMPUTER_SCIENCE_ENGINEER": [
        ("CS-301", "Data Structures", [
            (1, "Linked Lists & Array Formulations",
             ["Linked Lists", "Arrays"], 0.5),
            (2, "Trees and Graphs", ["Trees", "Graphs"], 0.5),
        ]),
        ("CS-302", "Operating Systems", [
            (1, "Process Management", ["Processes", "Scheduling"], 0.5),
            (2, "Memory Management", ["Paging", "Virtual Memory"], 0.5),
        ]),
    ],
    "AI_ENGINEER": [
        ("AI-301", "Machine Learning Foundations", [
            (1, "Supervised Learning", ["Regression", "Classification"], 0.5),
            (2, "Model Evaluation", ["Cross Validation", "Metrics"], 0.5),
        ]),
        ("AI-302", "Neural Networks", [
            (1, "Perceptrons", ["Activation Functions", "Backpropagation"], 0.5),
            (2, "CNN Architectures", ["Convolution", "Pooling"], 0.5),
        ]),
    ],
    "MECHANICAL_ENGINEER": [
        ("ME-301", "Thermodynamics", [
            (1, "Laws of Thermodynamics", ["First Law", "Second Law"], 0.5),
            (2, "Heat Engines", ["Carnot Cycle", "Efficiency"], 0.5),
        ]),
        ("ME-302", "Fluid Mechanics", [
            (1, "Fluid Statics", ["Pressure", "Buoyancy"], 0.5),
            (2, "Bernoulli Applications", ["Continuity", "Flow Rate"], 0.5),
        ]),
    ],
    "ELECTRICAL_ENGINEER": [
        ("EE-301", "Circuit Theory", [
            (1, "Network Theorems", ["Thevenin", "Norton"], 0.5),
            (2, "AC Analysis", ["Phasors", "Impedance"], 0.5),
        ]),
        ("EE-302", "Power Systems", [
            (1, "Transmission Lines", ["Parameters", "Losses"], 0.5),
            (2, "Fault Analysis", ["Symmetrical Faults", "Protection"], 0.5),
        ]),
    ],
    "CIVIL_ENGINEER": [
        ("CE-301", "Structural Analysis", [
            (1, "Trusses", ["Method of Joints", "Method of Sections"], 0.5),
            (2, "Beams", ["Shear Force", "Bending Moment"], 0.5),
        ]),
        ("CE-302", "Geotechnical Engineering", [
            (1, "Soil Properties", ["Classification", "Compaction"], 0.5),
            (2, "Foundations", ["Bearing Capacity", "Settlement"], 0.5),
        ]),
    ],
}


def seed_college_mvp(adapter: FakeSupabaseAdapter) -> FakeSupabaseAdapter:
    client = adapter.client

    # --- Universities -------------------------------------------------
    client.table("universities").insert([
        {
            "university_id": "univ_anna",
            "name": "Anna University",
            "normalized_name": "anna university",
            "official_domain": "annauniv.edu",
            "verification_status": "VERIFIED",
            "country": "India",
            "state": "Tamil Nadu",
        },
        {
            "university_id": "univ_aicte_model",
            "name": "AICTE Model University",
            "normalized_name": "aicte model university",
            "official_domain": "aicte.example.edu",
            "verification_status": "VERIFIED",
            "country": "India",
            "state": "Delhi",
        },
    ]).execute()

    # --- Programs / curricula / subjects ------------------------------
    for branch in BRANCHES:
        program_id = f"prog_aicte_{branch.lower()}"
        client.table("programs").insert({
            "program_id": program_id,
            "university_id": "univ_aicte_model",
            "branch": branch,
            "name": f"B.Tech {branch.replace('_', ' ').title()} (Model)",
            "degree_type": "BTECH",
        }).execute()

        curriculum_id = f"curric_aicte_{branch.lower()}_s3"
        client.table("curricula").insert({
            "curriculum_id": curriculum_id,
            "program_id": program_id,
            "university_id": "univ_aicte_model",
            "semester": 3,
            "verification_status": "VERIFIED",
        }).execute()

        for code, name, units in BRANCH_SUBJECTS[branch]:
            client.table("subjects").insert({
                "subject_id": code,
                "code": code,
                "name": name,
                "credits": 4,
            }).execute()
            client.table("curriculum_subjects").insert({
                "curriculum_id": curriculum_id,
                "subject_id": code,
            }).execute()
            for u, title, topics, weightage in units:
                client.table("curriculum_units").insert({
                    "curriculum_id": curriculum_id,
                    "subject_id": code,
                    "unit": u,
                    "title": title,
                    "topics": topics,
                    "weightage": weightage,
                    "verification_status": "VERIFIED",
                }).execute()

    # --- Resources for CS-301 (plan generation needs WATCH + READ) -----
    client.table("learning_resources").insert([
        {
            "resource_id": "res_cs301_video1",
            "subject_id": "CS-301",
            "resource_type": "VIDEO",
            "title": "Data Structures: Linked Lists Lecture",
            "provider": "Test Provider",
            "url": "https://example.edu/video/cs301-linked-lists",
            "source_id": "src_test_official",
            "source_tier": "B",
            "verification_status": "VERIFIED",
            "estimated_minutes": 45,
            "video_timestamps": [
                {"start_seconds": 0, "end_seconds": 1200,
                 "purpose": "Linked list fundamentals"}
            ],
            "document_sections": [],
        },
        {
            "resource_id": "res_cs301_notes1",
            "subject_id": "CS-301",
            "resource_type": "NOTES",
            "title": "Data Structures Official Notes",
            "provider": "Test Provider",
            "url": "https://example.edu/notes/cs301",
            "source_id": "src_test_official",
            "source_tier": "B",
            "verification_status": "VERIFIED",
            "estimated_minutes": 30,
            "video_timestamps": [],
            "document_sections": [
                {"start_page": 12, "end_page": 28,
                 "section_title": "Linked Lists & Arrays"}
            ],
        },
    ]).execute()

    # --- Verified PYQ set for CS-301 -----------------------------------
    client.table("verification_sources").insert({
        "source_id": "src_test_official",
        "source_type": "UNIVERSITY_OFFICIAL",
        "title": "Test University Exam Archive",
        "url": "https://example.edu/exams",
        "verification_status": "VERIFIED",
    }).execute()
    client.table("pyq_sets").insert({
        "pyq_set_id": "pyq_cs301_2024",
        "university_id": "univ_aicte_model",
        "program_id": "prog_aicte_computer_science_engineer",
        "semester": 3,
        "subject_id": "CS-301",
        "exam_year": 2024,
        "verification_status": "VERIFIED",
        "source_id": "src_test_official",
    }).execute()
    client.table("pyq_questions").insert([
        {
            "question_id": "pyq_cs301_q1",
            "pyq_set_id": "pyq_cs301_2024",
            "question_number": "Q1(a)",
            "question_text": "Explain the time complexity of inserting a node at the head of a singly linked list.",
            "marks": 5,
            "topic_ids": ["Linked Lists"],
            "unit": 1,
            "difficulty": "MEDIUM",
            "source_id": "src_test_official",
            "verification_status": "VERIFIED",
        },
        {
            "question_id": "pyq_cs301_q2",
            "pyq_set_id": "pyq_cs301_2024",
            "question_number": "Q1(b)",
            "question_text": "Compare arrays and linked lists for random access performance.",
            "marks": 5,
            "topic_ids": ["Arrays"],
            "unit": 1,
            "difficulty": "EASY",
            "source_id": "src_test_official",
            "verification_status": "VERIFIED",
        },
    ]).execute()

    return adapter


def install_fake_adapter(monkeypatch=None):
    """
    Installs a fresh seeded fake adapter into every module namespace the
    backend reads it from. Returns (adapter, restore).

    restore() puts the original attributes back — module-scoped fixtures
    should call it on teardown so other test modules (e.g. connectivity
    tests asserting honest 503s without credentials) are unaffected.
    """
    import backend.services.supabase_adapter as sa_mod
    import backend.core.security as sec_mod
    import backend.providers.curriculum_registry as cr_mod
    import backend.services.college_store as cs_mod

    adapter = FakeSupabaseAdapter()
    seed_college_mvp(adapter)

    if monkeypatch is not None:
        monkeypatch.setattr(sa_mod, "get_supabase_adapter", lambda: adapter)
        monkeypatch.setattr(sec_mod, "get_supabase_adapter", lambda: adapter)
        monkeypatch.setattr(cr_mod, "get_supabase_adapter", lambda: adapter)
        monkeypatch.setattr(cs_mod.college_store, "adapter", adapter)
        monkeypatch.setattr(cs_mod, "get_supabase_adapter", lambda: adapter)
        return adapter, lambda: None

    saved = {
        "sa": sa_mod.get_supabase_adapter,
        "sec": sec_mod.get_supabase_adapter,
        "cr": cr_mod.get_supabase_adapter,
        "cs_adapter": cs_mod.college_store.adapter,
        "cs": cs_mod.get_supabase_adapter,
    }
    sa_mod.get_supabase_adapter = lambda: adapter
    sec_mod.get_supabase_adapter = lambda: adapter
    cr_mod.get_supabase_adapter = lambda: adapter
    cs_mod.college_store.adapter = adapter
    cs_mod.get_supabase_adapter = lambda: adapter

    def restore():
        sa_mod.get_supabase_adapter = saved["sa"]
        sec_mod.get_supabase_adapter = saved["sec"]
        cr_mod.get_supabase_adapter = saved["cr"]
        cs_mod.college_store.adapter = saved["cs_adapter"]
        cs_mod.get_supabase_adapter = saved["cs"]

    return adapter, restore
