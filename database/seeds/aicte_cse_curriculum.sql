-- ============================================================================
-- PathMind College MVP — Seed: AICTE Model Curriculum (B.Tech CSE)
-- ============================================================================
-- FILE ONLY. This file has NOT been executed against any database.
-- Run it only with explicit user approval (privileged backend / service-role
-- key), ideally in a transaction.
--
-- Source (transcribed 2026-09-24):
--   "Model Curriculum for UG Degree Course in Computer Science and Engineering"
--   (Engineering & Technology) — AICTE, revised edition 2022 (163-credit
--   structure, Semesters I-VIII).
--   Official PDF:
--   https://www.aicte.gov.in/sites/default/files/Updated-AICTE%20-%20UG%20CSE.pdf
--   (fetched and read 2026-09-24)
--
-- Scope: shared-knowledge tables only (source_records, universities, programs,
-- curricula, subjects, curriculum_subjects, curriculum_units). No PYQs, no
-- learner-private tables.
--
-- Design notes:
--   1. The `curricula` table stores ONE ROW PER SEMESTER (CHECK semester 1..8),
--      so the model curriculum is 8 curriculum rows joined to their subjects
--      via `curriculum_subjects`.
--   2. `aicte_model_university` is a REFERENCE record for the AICTE model
--      curriculum. It is NOT a real university, carries NO accreditation or
--      recognition claim, and must never be presented to learners as one.
--   3. Every row is inserted with verification_status='VERIFIED' because the
--      content is transcribed directly from the official AICTE document, and
--      the schema's RLS read policies require VERIFIED rows (chained through
--      a VERIFIED source_records row) to be readable by anon/authenticated
--      users.
--   4. `curriculum_units` rows are included ONLY where the model PDF publishes
--      a detailed module/unit table for the course. Subjects without published
--      module detail get NO units here (honest gap — filled locally per HEI).
--   5. Elective slot names (PEC Elective-I..IV, OEC I..III) are filled with
--      real elective courses taken from the PDF's own "Professional Electives
--      and Micro Specializations" appendix. The model curriculum leaves the
--      exact elective set to each HEI, so these are representative choices;
--      the PEC-SE / PEC-AML / PEC-DS / PEC-HCI / OEC-* slot codes are
--      seed-chosen, not AICTE-assigned.
--   6. Idempotent: every INSERT uses ON CONFLICT ... DO NOTHING against the
--      table's unique constraint, so the file can be re-run safely.
--   7. Academic year '2022-23' refers to the 2022 revised model-curriculum
--      edition.
--   8. Compiler Design: the Sem VII structure table lists it as PCC-CS602;
--      the detail section header reads PEC CS-602. The structure-table code
--      (PCC-CS602) is used here.
--
-- Expected row counts after a fresh run (idempotent — re-runs change nothing):
--   source_records        1
--   universities          1
--   programs              1
--   curricula             8
--   subjects              46
--   curriculum_subjects   46
--   curriculum_units      113
--   TOTAL                 216
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Source record: the official AICTE model curriculum PDF.
--    RLS: every other table's read policy chains back to a VERIFIED
--    source_records row, so this row must exist and be VERIFIED first.
-- ----------------------------------------------------------------------------
INSERT INTO public.source_records (
    source_id, url, canonical_url, title, domain, provider_name,
    provider_type, source_tier, source_type, verification_status,
    language, content_available, notes
) VALUES (
    'aicte_model_curriculum_ug_cse_2022',
    'https://www.aicte.gov.in/sites/default/files/Updated-AICTE%20-%20UG%20CSE.pdf',
    'https://www.aicte.gov.in/sites/default/files/Updated-AICTE%20-%20UG%20CSE.pdf',
    'Model Curriculum for UG Degree Course in Computer Science and Engineering (Engineering & Technology) — Revised Edition 2022',
    'www.aicte.gov.in',
    'All India Council for Technical Education',
    'GOVERNMENT',
    'OFFICIAL',
    'MODEL_CURRICULUM',
    'VERIFIED',
    'en',
    true,
    'AICTE model curriculum for B.Tech CSE, 163-credit structure across 8 semesters. Used as reference seed only; does not imply any university follows it verbatim.'
)
ON CONFLICT (source_id) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 2. Reference university record.
--    NOT a real university. Exists so the model-curriculum program has a
--    parent university_id; carries NO accreditation/recognition claim.
--    Never display to learners as an institution.
-- ----------------------------------------------------------------------------
INSERT INTO public.universities (
    university_id, name, normalized_name, country, state,
    official_domain, official_url, verification_status, source_id,
    aliases
) VALUES (
    'aicte_model_university',
    'AICTE Model Reference Institution (not a real university)',
    'aicte model reference institution',
    'India',
    'Pan-India (model curriculum reference only)',
    'aicte.gov.in',
    'https://www.aicte.gov.in',
    'VERIFIED',
    'aicte_model_curriculum_ug_cse_2022',
    '["aicte model university","aicte model curriculum reference"]'
)
ON CONFLICT (university_id) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 3. Program record: B.Tech CSE under the AICTE model curriculum.
-- ----------------------------------------------------------------------------
INSERT INTO public.programs (
    program_id, university_id, name, normalized_name, degree, branch,
    supported_path, duration_semesters, version, verification_status
) VALUES (
    'aicte_cse_btech',
    'aicte_model_university',
    'B.Tech Computer Science and Engineering (AICTE Model Curriculum, 2022 edition)',
    'b tech computer science and engineering aicte model curriculum',
    'B.Tech',
    'Computer Science and Engineering',
    'GENERAL_OTHER',
    8,
    1,
    'VERIFIED'
)
ON CONFLICT (program_id) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 4. Curricula: one row per semester (schema constraint semester 1..8).
--    Semester credit totals per the AICTE structure: 18 / 23 / 23 / 21 /
--    20 / 23 / 20 / 15 = 163.
-- ----------------------------------------------------------------------------
INSERT INTO public.curricula (
    curriculum_id, university_id, program_id, academic_year, semester, version, verification_status
) VALUES
    ('aicte_cse_sem1', 'aicte_model_university', 'aicte_cse_btech', '2022-23', 1, 1, 'VERIFIED'),
    ('aicte_cse_sem2', 'aicte_model_university', 'aicte_cse_btech', '2022-23', 2, 1, 'VERIFIED'),
    ('aicte_cse_sem3', 'aicte_model_university', 'aicte_cse_btech', '2022-23', 3, 1, 'VERIFIED'),
    ('aicte_cse_sem4', 'aicte_model_university', 'aicte_cse_btech', '2022-23', 4, 1, 'VERIFIED'),
    ('aicte_cse_sem5', 'aicte_model_university', 'aicte_cse_btech', '2022-23', 5, 1, 'VERIFIED'),
    ('aicte_cse_sem6', 'aicte_model_university', 'aicte_cse_btech', '2022-23', 6, 1, 'VERIFIED'),
    ('aicte_cse_sem7', 'aicte_model_university', 'aicte_cse_btech', '2022-23', 7, 1, 'VERIFIED'),
    ('aicte_cse_sem8', 'aicte_model_university', 'aicte_cse_btech', '2022-23', 8, 1, 'VERIFIED')
ON CONFLICT (curriculum_id) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 5. Subjects. Codes, L/T/P and credits follow the AICTE semester-structure
--    tables. lecture_hours / practical_hours store L and P (tutorials are not
--    a schema column). assessment_pattern is left NULL — the model PDF does
--    not prescribe an assessment scheme.
-- ----------------------------------------------------------------------------
INSERT INTO public.subjects (
    subject_id, code, name, credits, lecture_hours, practical_hours,
    assessment_pattern, verification_status
) VALUES
    -- Semester I (18 credits + 1 audit)
    ('aicte_cse_bsc_101',  'BSC-101',  'Physics-I',                                   5, 3, 2, NULL, 'VERIFIED'),
    ('aicte_cse_bsc_102',  'BSC-102',  'Mathematics-I',                               4, 3, 0, NULL, 'VERIFIED'),
    ('aicte_cse_esc_101',  'ESC-101',  'Basic Electrical Engineering',                5, 3, 2, NULL, 'VERIFIED'),
    ('aicte_cse_esc_102',  'ESC-102',  'Engineering Graphics & Design',               3, 1, 4, NULL, 'VERIFIED'),
    ('aicte_cse_hsmc_102', 'HSMC-102', 'Design Thinking',                             1, 0, 2, NULL, 'VERIFIED'),
    ('aicte_cse_au_101',   'AU-101',   'IDEA Lab Workshop',                           0, 2, 4, NULL, 'VERIFIED'),

    -- Semester II (23 credits + 1 audit)
    ('aicte_cse_bsc_202',  'BSC-202',  'Chemistry-I',                                 5, 3, 2, NULL, 'VERIFIED'),
    ('aicte_cse_bsc_201',  'BSC-201',  'Mathematics-II',                              4, 3, 0, NULL, 'VERIFIED'),
    ('aicte_cse_esc_201',  'ESC-201',  'Programming for Problem Solving',             5, 3, 4, NULL, 'VERIFIED'),
    ('aicte_cse_hsmc_201', 'HSMC-201', 'English',                                     3, 2, 2, NULL, 'VERIFIED'),
    ('aicte_cse_esc_202',  'ESC-202',  'Workshop / Manufacturing Practices',          3, 1, 4, NULL, 'VERIFIED'),
    ('aicte_cse_au_102',   'AU-102',   'Sports and Yoga or NSS/NCC',                  0, 2, 0, NULL, 'VERIFIED'),
    ('aicte_cse_hsmc_h102','HSMC-H102','Universal Human Values-II',                   3, 2, 0, NULL, 'VERIFIED'),

    -- Semester III (23 credits)
    ('aicte_cse_esc_301',  'ESC-301',  'Analog Electronic Circuits',                  5, 3, 4, NULL, 'VERIFIED'),
    ('aicte_cse_pcc_cs301','PCC-CS301','Data Structure and Algorithms',               5, 3, 4, NULL, 'VERIFIED'),
    ('aicte_cse_esc_302',  'ESC-302',  'Digital Electronics',                         5, 3, 4, NULL, 'VERIFIED'),
    ('aicte_cse_pcc_cs302','PCC-CS302','IT Workshop (SciLab/MATLAB)',                 3, 1, 4, NULL, 'VERIFIED'),
    ('aicte_cse_bsc_301',  'BSC-301',  'Mathematics-III (Differential Calculus)',     2, 2, 0, NULL, 'VERIFIED'),
    ('aicte_cse_hsmc_301', 'HSMC-301', 'Humanities-I',                                3, 3, 0, NULL, 'VERIFIED')
ON CONFLICT (subject_id) DO NOTHING;

INSERT INTO public.subjects (
    subject_id, code, name, credits, lecture_hours, practical_hours,
    assessment_pattern, verification_status
) VALUES
    -- Semester IV (21 credits + 1 mandatory non-credit)
    ('aicte_cse_pcc_cs401','PCC-CS401','Discrete Mathematics',                          4, 3, 0, NULL, 'VERIFIED'),
    ('aicte_cse_pcc_cs402','PCC-CS402','Computer Organization & Architecture',          5, 3, 4, NULL, 'VERIFIED'),
    ('aicte_cse_pcc_cs404','PCC-CS404','Design & Analysis of Algorithms',               5, 3, 4, NULL, 'VERIFIED'),
    ('aicte_cse_pcc_cs405','PCC-CS405','Advanced Programming',                          4, 3, 0, NULL, 'VERIFIED'),
    ('aicte_cse_hsmc_401', 'HSMC-401', 'Management 1 (Organizational Behaviour / Finance & Accounting)', 3, 3, 0, NULL, 'VERIFIED'),
    ('aicte_cse_mc_env',   'MC-ENV',   'Environmental Sciences',                        0, 0, 0, NULL, 'VERIFIED'),

    -- Semester V (20 credits + 1 mandatory non-credit)
    ('aicte_cse_esc_501',  'ESC-501',  'Signals & Systems',                             3, 3, 0, NULL, 'VERIFIED'),
    ('aicte_cse_pcc_cs505','PCC-CS505','Introduction to Database Systems',              5, 3, 4, NULL, 'VERIFIED'),
    ('aicte_cse_pcc_cs603','PCC-CS603','Machine Learning',                              4, 3, 0, NULL, 'VERIFIED'),
    ('aicte_cse_pcc_cs403','PCC-CS403','Operating Systems',                             5, 3, 4, NULL, 'VERIFIED'),
    ('aicte_cse_hsmc_501', 'HSMC-501', 'Humanities II',                                 3, 3, 0, NULL, 'VERIFIED'),
    ('aicte_cse_mc_const', 'MC-CONST', 'Constitution of India / Essence of Indian Knowledge Tradition', 0, 0, 0, NULL, 'VERIFIED')
ON CONFLICT (subject_id) DO NOTHING;

INSERT INTO public.subjects (
    subject_id, code, name, credits, lecture_hours, practical_hours,
    assessment_pattern, verification_status
) VALUES
    -- Semester VI (23 credits)
    ('aicte_cse_pcc_cs601','PCC-CS601','Computer Networks',                             5, 3, 4, NULL, 'VERIFIED'),
    ('aicte_cse_pec_cs601','PEC-CS601','Introductory Cyber Security',                   5, 3, 4, NULL, 'VERIFIED'),
    -- Representative elective choices (see header note 5). L/T/P 3/0/0 per slot.
    ('aicte_cse_pec_se',   'PEC-SE',   'Software Engineering (PEC Elective-I)',         3, 3, 0, NULL, 'VERIFIED'),
    ('aicte_cse_pec_aml',  'PEC-AML',  'Advanced Machine Learning (PEC Elective-II)',   3, 3, 0, NULL, 'VERIFIED'),
    ('aicte_cse_pcc_cs504','PCC-CS504','Theory of Computation',                         4, 3, 0, NULL, 'VERIFIED'),
    ('aicte_cse_proj_cs601','PROJ-CS601','Project-1',                                   3, 0, 6, NULL, 'VERIFIED'),

    -- Semester VII (20 credits)
    ('aicte_cse_pcc_cs602','PCC-CS602','Compiler Design',                               5, 3, 4, NULL, 'VERIFIED'),
    ('aicte_cse_pec_ds',   'PEC-DS',   'Principles of Distributed Systems (PEC Elective-III)', 3, 3, 0, NULL, 'VERIFIED'),
    ('aicte_cse_oec_cbda', 'OEC-CBDA', 'Building Cloud and Big Data Applications (Open Elective-I)', 3, 3, 0, NULL, 'VERIFIED'),
    ('aicte_cse_bsc_701',  'BSC-701',  'Biology',                                       3, 2, 0, NULL, 'VERIFIED'),
    ('aicte_cse_proj_cs701','PROJ-CS701','Project-II',                                  6, 0, 12, NULL, 'VERIFIED'),

    -- Semester VIII (15 credits)
    ('aicte_cse_pec_hci',  'PEC-HCI',  'Introduction to HCI (PEC Elective-IV)',         3, 3, 0, NULL, 'VERIFIED'),
    ('aicte_cse_oec_cv',   'OEC-CV',   'Computer Vision (Open Elective-II)',            3, 3, 0, NULL, 'VERIFIED'),
    ('aicte_cse_oec_nlp',  'OEC-NLP',  'Natural Language Processing (Open Elective-III)', 3, 3, 0, NULL, 'VERIFIED'),
    ('aicte_cse_proj_cs801','PROJ-CS801','Project-III',                                 6, 0, 12, NULL, 'VERIFIED')
ON CONFLICT (subject_id) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 6. Curriculum <-> subject joins (46 rows: one per subject in its semester).
-- ----------------------------------------------------------------------------
INSERT INTO public.curriculum_subjects (
    curriculum_id, subject_id, verification_status
) VALUES
    -- Semester I
    ('aicte_cse_sem1', 'aicte_cse_bsc_101',  'VERIFIED'),
    ('aicte_cse_sem1', 'aicte_cse_bsc_102',  'VERIFIED'),
    ('aicte_cse_sem1', 'aicte_cse_esc_101',  'VERIFIED'),
    ('aicte_cse_sem1', 'aicte_cse_esc_102',  'VERIFIED'),
    ('aicte_cse_sem1', 'aicte_cse_hsmc_102', 'VERIFIED'),
    ('aicte_cse_sem1', 'aicte_cse_au_101',   'VERIFIED'),
    -- Semester II
    ('aicte_cse_sem2', 'aicte_cse_bsc_202',  'VERIFIED'),
    ('aicte_cse_sem2', 'aicte_cse_bsc_201',  'VERIFIED'),
    ('aicte_cse_sem2', 'aicte_cse_esc_201',  'VERIFIED'),
    ('aicte_cse_sem2', 'aicte_cse_hsmc_201', 'VERIFIED'),
    ('aicte_cse_sem2', 'aicte_cse_esc_202',  'VERIFIED'),
    ('aicte_cse_sem2', 'aicte_cse_au_102',   'VERIFIED'),
    ('aicte_cse_sem2', 'aicte_cse_hsmc_h102','VERIFIED'),
    -- Semester III
    ('aicte_cse_sem3', 'aicte_cse_esc_301',  'VERIFIED'),
    ('aicte_cse_sem3', 'aicte_cse_pcc_cs301','VERIFIED'),
    ('aicte_cse_sem3', 'aicte_cse_esc_302',  'VERIFIED'),
    ('aicte_cse_sem3', 'aicte_cse_pcc_cs302','VERIFIED'),
    ('aicte_cse_sem3', 'aicte_cse_bsc_301',  'VERIFIED'),
    ('aicte_cse_sem3', 'aicte_cse_hsmc_301', 'VERIFIED'),
    -- Semester IV
    ('aicte_cse_sem4', 'aicte_cse_pcc_cs401','VERIFIED'),
    ('aicte_cse_sem4', 'aicte_cse_pcc_cs402','VERIFIED'),
    ('aicte_cse_sem4', 'aicte_cse_pcc_cs404','VERIFIED'),
    ('aicte_cse_sem4', 'aicte_cse_pcc_cs405','VERIFIED'),
    ('aicte_cse_sem4', 'aicte_cse_hsmc_401', 'VERIFIED'),
    ('aicte_cse_sem4', 'aicte_cse_mc_env',   'VERIFIED'),
    -- Semester V
    ('aicte_cse_sem5', 'aicte_cse_esc_501',  'VERIFIED'),
    ('aicte_cse_sem5', 'aicte_cse_pcc_cs505','VERIFIED'),
    ('aicte_cse_sem5', 'aicte_cse_pcc_cs603','VERIFIED'),
    ('aicte_cse_sem5', 'aicte_cse_pcc_cs403','VERIFIED'),
    ('aicte_cse_sem5', 'aicte_cse_hsmc_501', 'VERIFIED'),
    ('aicte_cse_sem5', 'aicte_cse_mc_const', 'VERIFIED'),
    -- Semester VI
    ('aicte_cse_sem6', 'aicte_cse_pcc_cs601','VERIFIED'),
    ('aicte_cse_sem6', 'aicte_cse_pec_cs601','VERIFIED'),
    ('aicte_cse_sem6', 'aicte_cse_pec_se',   'VERIFIED'),
    ('aicte_cse_sem6', 'aicte_cse_pec_aml',  'VERIFIED'),
    ('aicte_cse_sem6', 'aicte_cse_pcc_cs504','VERIFIED'),
    ('aicte_cse_sem6', 'aicte_cse_proj_cs601','VERIFIED'),
    -- Semester VII
    ('aicte_cse_sem7', 'aicte_cse_pcc_cs602','VERIFIED'),
    ('aicte_cse_sem7', 'aicte_cse_pec_ds',   'VERIFIED'),
    ('aicte_cse_sem7', 'aicte_cse_oec_cbda', 'VERIFIED'),
    ('aicte_cse_sem7', 'aicte_cse_bsc_701',  'VERIFIED'),
    ('aicte_cse_sem7', 'aicte_cse_proj_cs701','VERIFIED'),
    -- Semester VIII
    ('aicte_cse_sem8', 'aicte_cse_pec_hci',  'VERIFIED'),
    ('aicte_cse_sem8', 'aicte_cse_oec_cv',   'VERIFIED'),
    ('aicte_cse_sem8', 'aicte_cse_oec_nlp',  'VERIFIED'),
    ('aicte_cse_sem8', 'aicte_cse_proj_cs801','VERIFIED')
ON CONFLICT (curriculum_id, subject_id) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 7. Curriculum units — only for courses whose detailed module tables are
--    published in the AICTE PDF (113 rows total). Unit titles follow the PDF's
--    module names; topics are drawn from the PDF's module contents.
--    source_ids links every unit back to the AICTE source record.
-- ----------------------------------------------------------------------------

-- Physics-I (BSC-101), Sem I — 7 units (EM theory modules I–VII, Mechanics,
-- Quantum modules as published)
INSERT INTO public.curriculum_units (
    curriculum_id, subject_id, unit, title, topics, source_ids, verification_status
) VALUES
    ('aicte_cse_sem1', 'aicte_cse_bsc_101', 1, $$Electrostatics in Vacuum$$,
        $$["Electric field and electrostatic potential of charge distributions","Divergence and curl of the electrostatic field","Laplace's and Poisson's equations and uniqueness","Method of images and boundary conditions","Faraday's cage"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem1', 'aicte_cse_bsc_101', 2, $$Electrostatics in a Linear Dielectric Medium$$,
        $$["Dipole field and potential","Bound charges due to electric polarization","Electric displacement and boundary conditions","Electrostatics problems with dielectrics"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem1', 'aicte_cse_bsc_101', 3, $$Magnetostatics$$,
        $$["Biot-Savart law","Divergence and curl of the static magnetic field","Vector potential via Stokes' theorem","Magnetization, bound currents and auxiliary field H","Ferromagnetic, paramagnetic and diamagnetic materials"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem1', 'aicte_cse_bsc_101', 4, $$Faraday's Law and Maxwell's Equations$$,
        $$["Faraday's law and motional EMF","Lenz's law and electromagnetic braking","Displacement current and the continuity equation","Maxwell's equations in vacuum and non-conducting media","Poynting vector and energy flow"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem1', 'aicte_cse_bsc_101', 5, $$Electromagnetic Waves$$,
        $$["Wave equation and plane EM waves","Transverse nature and polarization","Energy and momentum of EM waves","Reflection and transmission at a dielectric interface"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem1', 'aicte_cse_bsc_101', 6, $$Mechanics: Motion, Central Forces and Rigid Bodies$$,
        $$["Newton's laws in rotating frames","Potential energy, central forces and Kepler orbits","Harmonic, damped and forced oscillators","Planar and three-dimensional rigid body motion","Foucault pendulum and Coriolis acceleration"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem1', 'aicte_cse_bsc_101', 7, $$Quantum Mechanics: The Schrodinger Equation$$,
        $$["Wave nature of particles","Time-dependent and time-independent Schrodinger equation","Born interpretation and uncertainty principle","Particle in a box and the harmonic oscillator","Tunneling and the scanning tunneling microscope"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED')
ON CONFLICT (curriculum_id, subject_id, unit) DO NOTHING;

-- Data Structure and Algorithms (PCC-CS301), Sem III — 7 units
INSERT INTO public.curriculum_units (
    curriculum_id, subject_id, unit, title, topics, source_ids, verification_status
) VALUES
    ('aicte_cse_sem3', 'aicte_cse_pcc_cs301', 1, $$Introduction and Basic Terminology$$,
        $$["Abstract data types vs data structures","Asymptotic notation: Big-O, Big-Omega, Big-Theta","Worst-case and average-case analysis"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem3', 'aicte_cse_pcc_cs301', 2, $$ADTs: Arrays, Linked Lists, Stacks, Queues, Dictionary and Trees$$,
        $$["Array and linked-list representations","Stacks and queues with applications","Dictionary ADT","Trees and binary trees, traversals"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem3', 'aicte_cse_pcc_cs301', 3, $$Priority Queues and Heaps$$,
        $$["Priority queue ADT","Binary heap implementation","Heap operations and heap sort"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem3', 'aicte_cse_pcc_cs301', 4, $$Binary Search Trees and Balanced Trees$$,
        $$["BST operations and analysis","AVL trees: rotations and balance","2-4 trees"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem3', 'aicte_cse_pcc_cs301', 5, $$Hash Tables and Tries$$,
        $$["Hash functions and collision resolution","Open addressing and chaining","Tries and applications"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem3', 'aicte_cse_pcc_cs301', 6, $$Sorting and Selection$$,
        $$["Comparison-based sorts: merge sort, quicksort","Lower bounds on sorting","Selection algorithms"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem3', 'aicte_cse_pcc_cs301', 7, $$Graphs: Representations and Traversal$$,
        $$["Adjacency matrix and adjacency list","Breadth-first search","Depth-first search and applications"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED')
ON CONFLICT (curriculum_id, subject_id, unit) DO NOTHING;

-- Discrete Mathematics (PCC-CS401), Sem IV — 6 units
INSERT INTO public.curriculum_units (
    curriculum_id, subject_id, unit, title, topics, source_ids, verification_status
) VALUES
    ('aicte_cse_sem4', 'aicte_cse_pcc_cs401', 1, $$Sets, Relations and Functions$$,
        $$["Set operations and Venn diagrams","Relations: equivalence and partial orders","Functions: injective, surjective, bijective"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem4', 'aicte_cse_pcc_cs401', 2, $$Proof Strategies$$,
        $$["Direct and contrapositive proof","Proof by contradiction","Mathematical induction and strong induction"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem4', 'aicte_cse_pcc_cs401', 3, $$Modular Arithmetic$$,
        $$["Congruences and modular inverses","Euclid's algorithm and extended Euclid","Applications: hashing and cryptography basics"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem4', 'aicte_cse_pcc_cs401', 4, $$Combinatorics$$,
        $$["Counting principles: sum and product rules","Permutations and combinations","Pigeonhole principle","Recurrence relations"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem4', 'aicte_cse_pcc_cs401', 5, $$Graphs$$,
        $$["Graph terminology and representations","Paths, cycles and connectivity","Eulerian and Hamiltonian paths","Trees"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem4', 'aicte_cse_pcc_cs401', 6, $$Logic$$,
        $$["Propositional logic and truth tables","Logical equivalence and inference rules","Predicates and quantifiers","Proof techniques in predicate logic"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED')
ON CONFLICT (curriculum_id, subject_id, unit) DO NOTHING;

-- Computer Organization & Architecture (PCC-CS402), Sem IV — 5 units
INSERT INTO public.curriculum_units (
    curriculum_id, subject_id, unit, title, topics, source_ids, verification_status
) VALUES
    ('aicte_cse_sem4', 'aicte_cse_pcc_cs402', 1, $$Introduction to Computer Architecture$$,
        $$["Levels of abstraction in computing","Von Neumann architecture","Performance measurement and benchmarks","Data representation and arithmetic"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem4', 'aicte_cse_pcc_cs402', 2, $$Instruction Set Architecture$$,
        $$["RISC-V instruction formats","Assembly programming basics","Addressing modes","Control-flow instructions and procedures"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem4', 'aicte_cse_pcc_cs402', 3, $$The Processor$$,
        $$["Single-cycle datapath and control","Pipelining and pipeline hazards","Data and control hazards, forwarding","Branch prediction"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem4', 'aicte_cse_pcc_cs402', 4, $$Memory Hierarchy$$,
        $$["Cache organization: direct-mapped, set-associative","Cache performance and replacement policies","Virtual memory and TLB"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem4', 'aicte_cse_pcc_cs402', 5, $$Storage and I/O$$,
        $$["Magnetic disks and flash storage","RAID","I/O buses and interfacing","Interrupts and DMA"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED')
ON CONFLICT (curriculum_id, subject_id, unit) DO NOTHING;

-- Design & Analysis of Algorithms (PCC-CS404), Sem IV — 6 units
INSERT INTO public.curriculum_units (
    curriculum_id, subject_id, unit, title, topics, source_ids, verification_status
) VALUES
    ('aicte_cse_sem4', 'aicte_cse_pcc_cs404', 1, $$Applications of Graph Search$$,
        $$["BFS/DFS revisited","Topological sorting","Connected components","Bipartite matching"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem4', 'aicte_cse_pcc_cs404', 2, $$Greedy Algorithms$$,
        $$["Greedy choice property","Activity selection and interval scheduling","Huffman coding","Minimum spanning trees: Kruskal and Prim"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem4', 'aicte_cse_pcc_cs404', 3, $$Divide and Conquer$$,
        $$["Recurrences and the Master theorem","Merge sort and quicksort analysis","Closest-pair and FFT overview"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem4', 'aicte_cse_pcc_cs404', 4, $$Dynamic Programming and Shortest Paths$$,
        $$["Optimal substructure and memoization","Knapsack, LCS and edit distance","Bellman-Ford and Dijkstra","Floyd-Warshall"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem4', 'aicte_cse_pcc_cs404', 5, $$Network Flows$$,
        $$["Max-flow min-cut theorem","Ford-Fulkerson and Edmonds-Karp","Applications: bipartite matching, image segmentation"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem4', 'aicte_cse_pcc_cs404', 6, $$Intractability and NP-Completeness$$,
        $$["P, NP and polynomial reductions","NP-complete problems: SAT, 3-SAT, CLIQUE","Cook-Levin theorem","Coping with NP-hardness: approximation"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED')
ON CONFLICT (curriculum_id, subject_id, unit) DO NOTHING;

-- Advanced Programming (PCC-CS405), Sem IV — 7 units
INSERT INTO public.curriculum_units (
    curriculum_id, subject_id, unit, title, topics, source_ids, verification_status
) VALUES
    ('aicte_cse_sem4', 'aicte_cse_pcc_cs405', 1, $$Familiarity with the Programming Environment$$,
        $$["Build systems and Make","IDEs and debuggers","Version control with Git"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem4', 'aicte_cse_pcc_cs405', 2, $$Basic Principles of the OO Development Process$$,
        $$["Classes, objects and encapsulation","UML basics","Iterative development"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem4', 'aicte_cse_pcc_cs405', 3, $$Advanced Features of OOP$$,
        $$["Interfaces and abstract classes","Inheritance and polymorphism","Generics and collections"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem4', 'aicte_cse_pcc_cs405', 4, $$Unit Testing$$,
        $$["Test-driven development","JUnit and test frameworks","Coverage and mocking"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem4', 'aicte_cse_pcc_cs405', 5, $$Using Language APIs$$,
        $$["Standard library deep dive","Concurrency APIs","Streams and functional idioms"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem4', 'aicte_cse_pcc_cs405', 6, $$Defensive Programming$$,
        $$["Exception handling","Assertions and contracts","Input validation and error handling"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem4', 'aicte_cse_pcc_cs405', 7, $$Modeling and Design Patterns$$,
        $$["Creational patterns","Structural patterns","Behavioral patterns"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED')
ON CONFLICT (curriculum_id, subject_id, unit) DO NOTHING;

-- Introduction to Database Systems (PCC-CS505), Sem V — 8 units
INSERT INTO public.curriculum_units (
    curriculum_id, subject_id, unit, title, topics, source_ids, verification_status
) VALUES
    ('aicte_cse_sem5', 'aicte_cse_pcc_cs505', 1, $$Introduction to Database Systems$$,
        $$["Data models: relational and semi-structured","Entity-relationship modeling","DBMS architecture and data independence"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem5', 'aicte_cse_pcc_cs505', 2, $$The Relational Model$$,
        $$["Relations, schemas and integrity constraints","Relational algebra","Relational calculus"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem5', 'aicte_cse_pcc_cs505', 3, $$SQL and Database Interaction$$,
        $$["DDL and DML","Complex queries, joins and subqueries","Views and indexes","JDBC/ODBC"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem5', 'aicte_cse_pcc_cs505', 4, $$Big Data and Semi-Structured Data$$,
        $$["Key-value stores","JSON data model","MongoDB basics"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem5', 'aicte_cse_pcc_cs505', 5, $$Database Design$$,
        $$["ER model to relational mapping","Functional dependencies","BCNF and 3NF normalization"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem5', 'aicte_cse_pcc_cs505', 6, $$Physical Design$$,
        $$["Storage: records, pages and files","Indexing and B+-trees","Hash-based indexing"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem5', 'aicte_cse_pcc_cs505', 7, $$Query Processing and Optimization$$,
        $$["Query parsing and logical plans","Cost-based optimization","Join ordering"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem5', 'aicte_cse_pcc_cs505', 8, $$Transaction Processing$$,
        $$["ACID properties","Serializability and conflict graphs","Two-phase locking","Crash recovery and logging"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED')
ON CONFLICT (curriculum_id, subject_id, unit) DO NOTHING;

-- Machine Learning (PCC-CS603), Sem V — 4 units
INSERT INTO public.curriculum_units (
    curriculum_id, subject_id, unit, title, topics, source_ids, verification_status
) VALUES
    ('aicte_cse_sem5', 'aicte_cse_pcc_cs603', 1, $$Introduction to Machine Learning$$,
        $$["Motivation and learning paradigms","Representation and features","Probability for ML","Supervised, unsupervised and reinforcement learning"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem5', 'aicte_cse_pcc_cs603', 2, $$Fundamentals of Machine Learning$$,
        $$["PCA for dimensionality reduction","K-nearest neighbors","Linear regression","Decision trees","Generalization, overfitting and train-validation-test splits"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem5', 'aicte_cse_pcc_cs603', 3, $$Selected Algorithms$$,
        $$["Ensembles and random forests","Linear SVM","K-means clustering","Logistic regression","Naive Bayes"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem5', 'aicte_cse_pcc_cs603', 4, $$Neural Network Learning$$,
        $$["Loss functions and gradient descent","Perceptron","Multi-layer perceptrons and backpropagation","Convolutional neural networks","Regularization techniques"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED')
ON CONFLICT (curriculum_id, subject_id, unit) DO NOTHING;

-- Operating Systems (PCC-CS403), Sem V — 7 units
INSERT INTO public.curriculum_units (
    curriculum_id, subject_id, unit, title, topics, source_ids, verification_status
) VALUES
    ('aicte_cse_sem5', 'aicte_cse_pcc_cs403', 1, $$Introduction to Operating Systems$$,
        $$["OS roles and services","System calls and kernel/user mode","OS structure: monolithic vs microkernel"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem5', 'aicte_cse_pcc_cs403', 2, $$Computer Organization and Architecture Refresher$$,
        $$["CPU, memory and I/O organization","Interrupts","Memory hierarchy recap"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem5', 'aicte_cse_pcc_cs403', 3, $$Processes$$,
        $$["Process control blocks","System calls: fork, exec, wait","Inter-process communication"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem5', 'aicte_cse_pcc_cs403', 4, $$Memory Management$$,
        $$["Address spaces and binding","Virtual memory and demand paging","Page replacement algorithms","Thrashing"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem5', 'aicte_cse_pcc_cs403', 5, $$Process Management$$,
        $$["Process lifecycle and context switching","CPU scheduling policies","Multilevel queues"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem5', 'aicte_cse_pcc_cs403', 6, $$Concurrency and Synchronization$$,
        $$["Threads and pthreads","Race conditions and critical sections","Semaphores, mutexes and monitors","Deadlocks: detection and avoidance"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem5', 'aicte_cse_pcc_cs403', 7, $$Persistence and File Systems$$,
        $$["File system interface and implementation","Journaling","Disks and RAID"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED')
ON CONFLICT (curriculum_id, subject_id, unit) DO NOTHING;

-- Constitution of India (MC-CONST), Sem V — 5 units
INSERT INTO public.curriculum_units (
    curriculum_id, subject_id, unit, title, topics, source_ids, verification_status
) VALUES
    ('aicte_cse_sem5', 'aicte_cse_mc_const', 1, $$The Constitution: Introduction$$,
        $$["Making of the Indian Constitution","Preamble","Fundamental rights and duties"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem5', 'aicte_cse_mc_const', 2, $$Union Government$$,
        $$["President and Parliament","Prime Minister and Council of Ministers","Judiciary at the Union level"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem5', 'aicte_cse_mc_const', 3, $$State Government$$,
        $$["Governor and State Legislature","Chief Minister and State Council of Ministers","High Courts"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem5', 'aicte_cse_mc_const', 4, $$Local Administration$$,
        $$["Panchayati Raj institutions","Municipalities","73rd and 74th amendments"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem5', 'aicte_cse_mc_const', 5, $$Election Commission$$,
        $$["Composition and functions of the Election Commission","Electoral process","Electoral reforms"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED')
ON CONFLICT (curriculum_id, subject_id, unit) DO NOTHING;

-- Computer Networks (PCC-CS601), Sem VI — 8 units
INSERT INTO public.curriculum_units (
    curriculum_id, subject_id, unit, title, topics, source_ids, verification_status
) VALUES
    ('aicte_cse_sem6', 'aicte_cse_pcc_cs601', 1, $$Introduction to the Internet$$,
        $$["How the Internet works: browsing a website","Packet switching vs circuit switching","Layering and the protocol stack","Performance metrics: throughput, delay, jitter, Little's law"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem6', 'aicte_cse_pcc_cs601', 2, $$Application Layer$$,
        $$["DNS: how name resolution works","HTTP, SMTP and SNMP","Peer-to-peer applications","Audio and video streaming"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem6', 'aicte_cse_pcc_cs601', 3, $$Linux Network Programming$$,
        $$["Socket programming in Linux","TCP and UDP client-server programs","Handling multiple clients"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem6', 'aicte_cse_pcc_cs601', 4, $$Transport Layer$$,
        $$["TCP and UDP: multiplexing and ports","Reliable transmission: sequence numbers, ACKs, retransmissions","TCP connection setup and teardown","Flow control and congestion control: slow start, AIMD"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem6', 'aicte_cse_pcc_cs601', 5, $$The IP Layer$$,
        $$["Network topology and router architecture","IPv4 and IPv6 addressing","IP forwarding and datagrams","NAT, firewalls and DMZ"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem6', 'aicte_cse_pcc_cs601', 6, $$Routing Protocols and Internet Architecture$$,
        $$["Link-state and distance-vector routing","Count-to-infinity and convergence","Intradomain routing: OSPF","Interdomain routing: BGP"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem6', 'aicte_cse_pcc_cs601', 7, $$Data Link Layer$$,
        $$["Error detection: parity and CRC","Medium access: Aloha, CSMA/CD","Switched LANs: ARP and Ethernet","Learning switches"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem6', 'aicte_cse_pcc_cs601', 8, $$Wireless Networks$$,
        $$["Wireless physical layer: SNR and interference","802.11 architecture and association","802.11 CSMA/CA","802.11 variants overview"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED')
ON CONFLICT (curriculum_id, subject_id, unit) DO NOTHING;

-- Introductory Cyber Security (PEC-CS601), Sem VI — 6 units (essential modules)
INSERT INTO public.curriculum_units (
    curriculum_id, subject_id, unit, title, topics, source_ids, verification_status
) VALUES
    ('aicte_cse_sem6', 'aicte_cse_pec_cs601', 1, $$Introduction and Basic Terminology$$,
        $$["CIA triad: confidentiality, integrity, availability","Cyber threats and attack surfaces","Recent cybersecurity incidents and analysis"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem6', 'aicte_cse_pec_cs601', 2, $$Basic Cryptography$$,
        $$["Symmetric vs asymmetric cryptography","RSA, Diffie-Hellman, DES, AES","Hashing: MD5, SHA-256","Digital signatures, certificates and PKI"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem6', 'aicte_cse_pec_cs601', 3, $$Authentication, Authorization and Privilege$$,
        $$["Strong authentication and 2FA","Access control: MAC vs DAC","Role-based authorization","Principle of least privilege and privilege escalation"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem6', 'aicte_cse_pec_cs601', 4, $$Application Security$$,
        $$["Buffer overflow, integer overflow, format-string bugs","Secure programming mitigations","Web client security: same-origin policy, cookies, sessions","XSS, CSRF, SQL injection, command injection","DNS, routing and IP vulnerabilities: DNSSEC, IPSec"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem6', 'aicte_cse_pec_cs601', 5, $$Perimeter Protection and Intrusion Detection$$,
        $$["Host intrusion detection and SIEM","Network IDS: signature vs behavior based","Snort","Firewalls: rules and customization"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem6', 'aicte_cse_pec_cs601', 6, $$Basic Malware Analysis$$,
        $$["Malware classes and characteristics","Static vs dynamic analysis","Signature vs behavioral detection"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED')
ON CONFLICT (curriculum_id, subject_id, unit) DO NOTHING;

-- Theory of Computation (PCC-CS504), Sem VI — 3 units
INSERT INTO public.curriculum_units (
    curriculum_id, subject_id, unit, title, topics, source_ids, verification_status
) VALUES
    ('aicte_cse_sem6', 'aicte_cse_pcc_cs504', 1, $$Finite Automaton$$,
        $$["Alphabets, formal languages and regular languages","DFA and NFA, subset construction","Closure properties and product construction","Pumping lemma and non-regular languages","Regular expressions and equivalence","DFA minimization"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem6', 'aicte_cse_pcc_cs504', 2, $$Grammars, Context-Free Languages and Machine Models$$,
        $$["Context-free grammars and Chomsky normal form","Pushdown automata: equivalence with CFGs","Closure properties of CFLs","Pumping lemma for CFLs","Deterministic CFLs and parsers"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem6', 'aicte_cse_pcc_cs504', 3, $$Turing Machines and Computability$$,
        $$["Turing machine models and Church-Turing hypothesis","Decidability and Turing recognizability","Undecidability by diagonalization","Reductions and Rice's theorem","Complexity classes: P, NP, EXP","NP-completeness and Cook-Levin"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED')
ON CONFLICT (curriculum_id, subject_id, unit) DO NOTHING;

-- Compiler Design (PCC-CS602), Sem VII — 8 units (essential modules)
INSERT INTO public.curriculum_units (
    curriculum_id, subject_id, unit, title, topics, source_ids, verification_status
) VALUES
    ('aicte_cse_sem7', 'aicte_cse_pcc_cs602', 1, $$Introduction to Compilers$$,
        $$["High-level vs low-level language abstractions","Phases of compilation","Bootstrapping and cross-compilation"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem7', 'aicte_cse_pcc_cs602', 2, $$Lexical Analysis$$,
        $$["Tokens, lexemes and token codes","Regular expressions for tokens","DFA-based token recognition","Generating scanners with LEX/Flex"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem7', 'aicte_cse_pcc_cs602', 3, $$Syntax Analysis$$,
        $$["Context-free grammars and parse trees","Top-down parsing: LL(1), recursive descent","Bottom-up parsing: LR(0), SLR","Parser generators: YACC/Bison"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem7', 'aicte_cse_pcc_cs602', 4, $$Semantic Analysis$$,
        $$["Abstract syntax trees","Attribute evaluation","Syntax-directed translation schemes"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem7', 'aicte_cse_pcc_cs602', 5, $$Applications of Semantic Analysis$$,
        $$["Declaration processing and type checking","Generating three-address code"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem7', 'aicte_cse_pcc_cs602', 6, $$Run-Time Support$$,
        $$["Activation records and calling conventions","Parameter passing: value, reference, name","Stack vs static allocation"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem7', 'aicte_cse_pcc_cs602', 7, $$Introduction to Code Optimization$$,
        $$["Control-flow graphs","Local optimizations: common subexpression elimination, copy propagation, dead-code elimination","Global optimization overview"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem7', 'aicte_cse_pcc_cs602', 8, $$Code Generation$$,
        $$["Generating assembly from three-address code","Instruction selection","Simple register allocation"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED')
ON CONFLICT (curriculum_id, subject_id, unit) DO NOTHING;

-- Representative electives (unit topics taken from the PDF's micro-specialization
-- appendix tables): 26 units
-- Software Engineering (PEC-SE), Sem VI — 4 units
INSERT INTO public.curriculum_units (
    curriculum_id, subject_id, unit, title, topics, source_ids, verification_status
) VALUES
    ('aicte_cse_sem6', 'aicte_cse_pec_se', 1, $$Iterative Software Development$$,
        $$["Iterative and incremental process models","Short cycles and agile approaches","Project planning for iterative processes"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem6', 'aicte_cse_pec_se', 2, $$Requirements and User Interfaces$$,
        $$["Requirements elicitation","User-interface requirements","Agile requirements practices"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem6', 'aicte_cse_pec_se', 3, $$Architecture, Design and Coding$$,
        $$["Software architecture and design","Coding with modern IDEs","Test-driven development"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem6', 'aicte_cse_pec_se', 4, $$Testing, Integration and Deployment$$,
        $$["Unit testing and test frameworks","Test automation and metrics","Integration and deployment"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED')
ON CONFLICT (curriculum_id, subject_id, unit) DO NOTHING;

-- Advanced Machine Learning (PEC-AML), Sem VI — 4 units
INSERT INTO public.curriculum_units (
    curriculum_id, subject_id, unit, title, topics, source_ids, verification_status
) VALUES
    ('aicte_cse_sem6', 'aicte_cse_pec_aml', 1, $$Deep Learning Architectures$$,
        $$["Convolutional neural networks","Recurrent neural networks","Autoencoders"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem6', 'aicte_cse_pec_aml', 2, $$Loss Functions and Training$$,
        $$["Loss functions for deep models","Training with gradient methods","Overfitting in deep learning"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem6', 'aicte_cse_pec_aml', 3, $$Learning with Limited Data$$,
        $$["Transfer learning and domain adaptation","Semi-supervised and self-supervised learning","Active and few-shot learning"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem6', 'aicte_cse_pec_aml', 4, $$Programming for Machine Learning$$,
        $$["PyTorch and TensorFlow","GPU and cloud usage","Debugging and visualization of models"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED')
ON CONFLICT (curriculum_id, subject_id, unit) DO NOTHING;

-- Principles of Distributed Systems (PEC-DS), Sem VII — 4 units
INSERT INTO public.curriculum_units (
    curriculum_id, subject_id, unit, title, topics, source_ids, verification_status
) VALUES
    ('aicte_cse_sem7', 'aicte_cse_pec_ds', 1, $$Models of Distributed Systems$$,
        $$["Need for distributed systems","Models for coordination among machines","Remote invocation and remote storage"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem7', 'aicte_cse_pec_ds', 2, $$Performance, Scalability and Reliability$$,
        $$["Performance metrics for distributed systems","Scalability techniques","Reliability and fault tolerance"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem7', 'aicte_cse_pec_ds', 3, $$Consistency and Correctness$$,
        $$["Consistency models","Correctness of distributed applications","Consensus basics"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem7', 'aicte_cse_pec_ds', 4, $$Building Distributed Applications$$,
        $$["Accessing remote applications and data","Designing distributed applications","Case studies"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED')
ON CONFLICT (curriculum_id, subject_id, unit) DO NOTHING;

-- Introduction to HCI (PEC-HCI), Sem VIII — 4 units
INSERT INTO public.curriculum_units (
    curriculum_id, subject_id, unit, title, topics, source_ids, verification_status
) VALUES
    ('aicte_cse_sem8', 'aicte_cse_pec_hci', 1, $$User-Centered Design$$,
        $$["Importance of user-centered design","Design process overview","Empathy for users"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem8', 'aicte_cse_pec_hci', 2, $$Observation and Inquiry Methods$$,
        $$["Contextual inquiry","Interviews, surveys and focus groups","Observation techniques"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem8', 'aicte_cse_pec_hci', 3, $$Prototyping$$,
        $$["Sketching","Low-fidelity prototyping","Iterative design"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem8', 'aicte_cse_pec_hci', 4, $$Usability Evaluation$$,
        $$["Usability evaluation methods","Heuristic evaluation","User testing"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED')
ON CONFLICT (curriculum_id, subject_id, unit) DO NOTHING;

-- Building Cloud and Big Data Applications (OEC-CBDA), Sem VII — 4 units
INSERT INTO public.curriculum_units (
    curriculum_id, subject_id, unit, title, topics, source_ids, verification_status
) VALUES
    ('aicte_cse_sem7', 'aicte_cse_oec_cbda', 1, $$Cloud Computing Models$$,
        $$["Cloud service models: IaaS, PaaS, SaaS","Enabling technologies","Virtualization and containerization"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem7', 'aicte_cse_oec_cbda', 2, $$Data-Intensive Computing$$,
        $$["Data-oriented programming","Distributed execution and runtimes","Streaming data management and processing"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem7', 'aicte_cse_oec_cbda', 3, $$Distributed Storage$$,
        $$["Remote and distributed file systems","Key-value storage","NoSQL columnar stores"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem7', 'aicte_cse_oec_cbda', 4, $$Cloud-Native Applications$$,
        $$["Resource abstraction and service-oriented architecture","Computing abstractions on the cloud","Building cloud-native applications"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED')
ON CONFLICT (curriculum_id, subject_id, unit) DO NOTHING;

-- Computer Vision (OEC-CV), Sem VIII — 3 units
INSERT INTO public.curriculum_units (
    curriculum_id, subject_id, unit, title, topics, source_ids, verification_status
) VALUES
    ('aicte_cse_sem8', 'aicte_cse_oec_cv', 1, $$ML Formulations for Vision$$,
        $$["Classification formulations for vision subtasks","Regression and structured prediction","Data-centric view of vision"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem8', 'aicte_cse_oec_cv', 2, $$Features and Embeddings$$,
        $$["Hand-crafted vs learned features","Embeddings for visual data","Role of data and learning in features"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem8', 'aicte_cse_oec_cv', 3, $$Learning in Vision Subtasks$$,
        $$["Object detection and segmentation","Laboratory experiments","Course project"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED')
ON CONFLICT (curriculum_id, subject_id, unit) DO NOTHING;

-- Natural Language Processing (OEC-NLP), Sem VIII — 3 units
INSERT INTO public.curriculum_units (
    curriculum_id, subject_id, unit, title, topics, source_ids, verification_status
) VALUES
    ('aicte_cse_sem8', 'aicte_cse_oec_nlp', 1, $$ML Formulations for Language$$,
        $$["Classification formulations for language subtasks","Regression and structured prediction","Data-centric view of NLP"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem8', 'aicte_cse_oec_nlp', 2, $$Features and Embeddings in NLP$$,
        $$["Word embeddings","Role of data and learning in feature learning","Contextual representations"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED'),
    ('aicte_cse_sem8', 'aicte_cse_oec_nlp', 3, $$Learning for NLP Subtasks$$,
        $$["Sequence labeling and text classification","Laboratory experiments","Course project"]$$,
        '["aicte_model_curriculum_ug_cse_2022"]', 'VERIFIED')
ON CONFLICT (curriculum_id, subject_id, unit) DO NOTHING;

COMMIT;

-- ----------------------------------------------------------------------------
-- Post-run verification (run manually after loading):
--
-- SELECT 'source_records',      COUNT(*) FROM public.source_records      WHERE source_id = 'aicte_model_curriculum_ug_cse_2022'; -- expect 1
-- SELECT 'universities',        COUNT(*) FROM public.universities        WHERE university_id = 'aicte_model_university';          -- expect 1
-- SELECT 'programs',            COUNT(*) FROM public.programs            WHERE program_id = 'aicte_cse_btech';                   -- expect 1
-- SELECT 'curricula',           COUNT(*) FROM public.curricula           WHERE curriculum_id LIKE 'aicte_cse_sem%';             -- expect 8
-- SELECT 'subjects',            COUNT(*) FROM public.subjects            WHERE subject_id LIKE 'aicte_cse_%';                   -- expect 46
-- SELECT 'curriculum_subjects', COUNT(*) FROM public.curriculum_subjects WHERE curriculum_id LIKE 'aicte_cse_sem%';            -- expect 46
-- SELECT 'curriculum_units',    COUNT(*) FROM public.curriculum_units    WHERE curriculum_id LIKE 'aicte_cse_sem%';            -- expect 113
-- SELECT semester, SUM(s.credits) AS semester_credits
--   FROM public.curriculum_subjects cs
--   JOIN public.subjects s ON s.subject_id = cs.subject_id
--   JOIN public.curricula c ON c.curriculum_id = cs.curriculum_id
--  WHERE c.curriculum_id LIKE 'aicte_cse_sem%'
--  GROUP BY semester ORDER BY semester;
-- -- expect 18 / 23 / 23 / 21 / 20 / 23 / 20 / 15 (audit/mandatory non-credit
-- -- subjects contribute 0), total 163.
-- ----------------------------------------------------------------------------
