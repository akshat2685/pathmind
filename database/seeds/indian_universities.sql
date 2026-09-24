-- ============================================================================
-- PathMind College MVP — Seed: 5 Indian Universities (catalog identities)
-- ============================================================================
-- FILE ONLY. This file documents the seed; execution happens via the
-- service-role REST loader (PostgREST bypasses RLS) or psql with explicit
-- user approval, ideally in a transaction.
--
-- Scope: university identity rows ONLY (official names, domains, states).
-- Branch curricula (5 branches x 5 universities) come from the official
-- syllabus research seed once verified. No subjects/curricula here.
--
-- Verification: names + official domains are the universities' own published
-- identities (their official websites). Each university row is chained to a
-- VERIFIED source_records row pointing at its official homepage, satisfying
-- the RLS read policy ("Anyone can view universities").
-- ============================================================================

INSERT INTO public.source_records (
    source_id, url, canonical_url, title, domain, provider_name,
    provider_type, source_tier, source_type, verification_status,
    language, content_available, notes
) VALUES
    (
        'univ_official_rtu',
        'https://www.rtu.ac.in',
        'https://www.rtu.ac.in',
        'Rajasthan Technical University — Official Website',
        'www.rtu.ac.in',
        'Rajasthan Technical University, Kota',
        'GOVERNMENT_UNIVERSITY',
        'OFFICIAL',
        'UNIVERSITY_IDENTITY',
        'VERIFIED',
        'en',
        true,
        'Official homepage of Rajasthan Technical University (RTU), Kota — used as the identity source for the RTU catalog record.'
    ),
    (
        'univ_official_aktu',
        'https://aktu.ac.in',
        'https://aktu.ac.in',
        'Dr. A.P.J. Abdul Kalam Technical University — Official Website',
        'aktu.ac.in',
        'Dr. A.P.J. Abdul Kalam Technical University, Lucknow',
        'GOVERNMENT_UNIVERSITY',
        'OFFICIAL',
        'UNIVERSITY_IDENTITY',
        'VERIFIED',
        'en',
        true,
        'Official homepage of Dr. A.P.J. Abdul Kalam Technical University (AKTU), Lucknow — used as the identity source for the AKTU catalog record.'
    ),
    (
        'univ_official_vtu',
        'https://vtu.ac.in',
        'https://vtu.ac.in',
        'Visvesvaraya Technological University — Official Website',
        'vtu.ac.in',
        'Visvesvaraya Technological University, Belagavi',
        'GOVERNMENT_UNIVERSITY',
        'OFFICIAL',
        'UNIVERSITY_IDENTITY',
        'VERIFIED',
        'en',
        true,
        'Official homepage of Visvesvaraya Technological University (VTU), Belagavi — used as the identity source for the VTU catalog record.'
    ),
    (
        'univ_official_anna',
        'https://www.annauniv.edu',
        'https://www.annauniv.edu',
        'Anna University — Official Website',
        'www.annauniv.edu',
        'Anna University, Chennai',
        'GOVERNMENT_UNIVERSITY',
        'OFFICIAL',
        'UNIVERSITY_IDENTITY',
        'VERIFIED',
        'en',
        true,
        'Official homepage of Anna University, Chennai — used as the identity source for the Anna University catalog record.'
    ),
    (
        'univ_official_jntuh',
        'https://jntuh.ac.in',
        'https://jntuh.ac.in',
        'Jawaharlal Nehru Technological University Hyderabad — Official Website',
        'jntuh.ac.in',
        'Jawaharlal Nehru Technological University Hyderabad',
        'GOVERNMENT_UNIVERSITY',
        'OFFICIAL',
        'UNIVERSITY_IDENTITY',
        'VERIFIED',
        'en',
        true,
        'Official homepage of Jawaharlal Nehru Technological University Hyderabad (JNTUH) — used as the identity source for the JNTUH catalog record.'
    )
ON CONFLICT (source_id) DO NOTHING;

-- ----------------------------------------------------------------------------
-- Universities: 5 Indian technical universities for the College MVP.
-- normalized_name carries the searchable tokens (name + short codes + city);
-- the /universities search matches normalized_name with ILIKE.
-- ----------------------------------------------------------------------------
INSERT INTO public.universities (
    university_id, name, normalized_name, country, state,
    official_domain, official_url, verification_status, source_id,
    aliases
) VALUES
    (
        'rtu',
        'Rajasthan Technical University',
        'rajasthan technical university rtu kota',
        'India',
        'Rajasthan',
        'rtu.ac.in',
        'https://www.rtu.ac.in',
        'VERIFIED',
        'univ_official_rtu',
        '["rtu", "rajasthan technical university"]'
    ),
    (
        'aktu',
        'Dr. A.P.J. Abdul Kalam Technical University',
        'dr a p j abdul kalam technical university aktu uptu lucknow uttar pradesh technical university',
        'India',
        'Uttar Pradesh',
        'aktu.ac.in',
        'https://aktu.ac.in',
        'VERIFIED',
        'univ_official_aktu',
        '["aktu", "uptu", "uttar pradesh technical university", "dr a p j abdul kalam technical university"]'
    ),
    (
        'vtu',
        'Visvesvaraya Technological University',
        'visvesvaraya technological university vtu belagavi',
        'India',
        'Karnataka',
        'vtu.ac.in',
        'https://vtu.ac.in',
        'VERIFIED',
        'univ_official_vtu',
        '["vtu", "visvesvaraya technological university"]'
    ),
    (
        'anna_university',
        'Anna University',
        'anna university chennai',
        'India',
        'Tamil Nadu',
        'annauniv.edu',
        'https://www.annauniv.edu',
        'VERIFIED',
        'univ_official_anna',
        '["anna university"]'
    ),
    (
        'jntuh',
        'Jawaharlal Nehru Technological University Hyderabad',
        'jawaharlal nehru technological university hyderabad jntuh jntu',
        'India',
        'Telangana',
        'jntuh.ac.in',
        'https://jntuh.ac.in',
        'VERIFIED',
        'univ_official_jntuh',
        '["jntuh", "jntu hyderabad", "jawaharlal nehru technological university hyderabad"]'
    )
ON CONFLICT (university_id) DO NOTHING;
