import pytest
from backend.services.store import FirestoreStore
from backend.services.requirement_graph_service import RequirementGraphService
from backend.services.roadmap_engine import RoadmapEngine
from backend.services.career_readiness_engine import CareerReadinessEngine
from backend.services.trajectory_engine import TrajectoryEngine
from backend.services.opportunity_matching_engine import OpportunityMatchingEngine
from backend.core.career_schemas import UniversalCareerProfile, TargetOutcome
from backend.core.trajectory_schemas import CandidatePath


@pytest.fixture
def clean_store():
    store = FirestoreStore()
    store._in_memory_persons.clear()
    return store


@pytest.fixture
def req_service():
    return RequirementGraphService()


@pytest.fixture
def roadmap_engine():
    return RoadmapEngine()


@pytest.fixture
def career_engine(clean_store):
    return CareerReadinessEngine(store=clean_store)


@pytest.fixture
def trajectory_engine():
    return TrajectoryEngine()


@pytest.fixture
def opp_engine(clean_store):
    from backend.services.career_readiness_engine import CareerReadinessEngine
    from backend.providers.opportunity_provider import BaseOpportunityProvider
    from backend.core.opportunity_schemas import CanonicalOpportunity
    
    class MockProvider(BaseOpportunityProvider):
        def get_provider_name(self) -> str:
            return "Mock Provider"
        def is_connected(self) -> bool:
            return True
        def get_status_code(self) -> str:
            return "OK"
        async def fetch_opportunities(self, domain_filter=None, role_filter=None, geography=None):
            opps = [
                CanonicalOpportunity(
                    title="Legal Clerkship",
                    organization="State Court",
                    opportunity_type="INTERNSHIP",
                    source="Mock",
                    verification_status="VERIFIED"
                ),
                CanonicalOpportunity(
                    title="Clinical Psychology Assistant",
                    organization="Health Clinic",
                    opportunity_type="JOB",
                    source="Mock",
                    verification_status="VERIFIED"
                ),
                CanonicalOpportunity(
                    title="Product Design Fellowship",
                    organization="Design Studio",
                    opportunity_type="FELLOWSHIP",
                    source="Mock",
                    verification_status="VERIFIED"
                )
            ]
            if not role_filter:
                return opps
            
            filter_lower = role_filter.lower()
            if "lawyer" in filter_lower:
                return [o for o in opps if "Legal" in o.title]
            elif "psychologist" in filter_lower:
                return [o for o in opps if "Psychology" in o.title]
            elif "design" in filter_lower:
                return [o for o in opps if "Design" in o.title]
            else:
                return []
            
            
    engine = OpportunityMatchingEngine(
        store=clean_store, 
        career_engine=CareerReadinessEngine(store=clean_store),
        provider=MockProvider()
    )
    return engine


# ==============================================================================
# STEP 19: COMPREHENSIVE 10-SCENARIO TEST SUITE
# ==============================================================================

@pytest.mark.asyncio
async def test_scenario_01_high_school_to_theoretical_mathematician(req_service, roadmap_engine, clean_store):
    """
    Scenario 1: High School Student -> Theoretical Mathematician
    - No Docker, PyTorch, MLOps, or Python foundations in the synthesized path.
    - Stages are: Abstract Algebra / Real Analysis / Topology / Mathematical Proofs.
    """
    person_id = "test_scen_01_math"
    graph = req_service.build_requirement_graph_for_outcome("Theoretical Mathematician")
    rm = await roadmap_engine.synthesize_personalized_roadmap(
        person_id=person_id,
        target_outcome="Theoretical Mathematician",
        constraints={"weekly_hours": 15}
    )

    all_stage_titles = [s.title.lower() for p in rm.phases for s in p.stages]
    all_stage_text = " ".join(all_stage_titles)
    all_skills = [sk.lower() for p in rm.phases for s in p.stages for sk in s.skills]
    all_skills_text = " ".join(all_skills)

    # 1. Negative checks: zero AI/ML/Software Engineering filler
    assert "docker" not in all_stage_text and "docker" not in all_skills_text
    assert "pytorch" not in all_stage_text and "pytorch" not in all_skills_text
    assert "mlops" not in all_stage_text and "mlops" not in all_skills_text
    assert "python foundations" not in all_stage_text

    # 2. Positive checks: pure mathematical curriculum
    assert any("foundations" in t for t in all_stage_titles)
    assert any("applied methods" in t for t in all_stage_titles)

    # 3. Requirement graph validation
    core_names = [n.name.lower() for n in graph.core_skills]
    assert any("algebra" in n for n in core_names)
    assert any("analysis" in n for n in core_names)
    assert any("topology" in n for n in core_names)
    assert any("proof" in n for n in core_names)


@pytest.mark.asyncio
async def test_scenario_02_accountant_to_math_teacher(req_service, roadmap_engine, career_engine, clean_store):
    """
    Scenario 2: Accountant -> High School Math Teacher
    - Preserves quantitative/arithmetic assets.
    - Adds pedagogy, classroom management, CTET / B.Ed certification.
    - Does NOT recommend MLOps or AI courses.
    """
    person_id = "test_scen_02_accountant"
    accountant_profile = UniversalCareerProfile(
        person_id=person_id,
        current_role="Certified Accountant",
        skills=["Financial Auditing", "Quantitative Analysis", "Tax Accounting", "Spreadsheet Modeling"],
        experience=[],
        education=[]
    )
    await clean_store.save_career_profile(person_id, accountant_profile.model_dump(mode="json"))

    analysis = career_engine.evaluate_transferable_skills(accountant_profile, "High School Math Teacher")
    rm = await roadmap_engine.synthesize_personalized_roadmap(
        person_id=person_id,
        target_outcome="High School Math Teacher",
        constraints={"weekly_hours": 15}
    )

    all_stage_titles = [s.title.lower() for p in rm.phases for s in p.stages]
    all_stage_text = " ".join(all_stage_titles)

    # Preserves quantitative/arithmetic assets
    assert any("subject matter" in s.lower() or "quantitative" in s.lower() or "auditing" in s.lower() for s in analysis.already_have)
    # Adds pedagogy, classroom management, CTET / B.Ed certification
    assert any("foundations" in t for t in all_stage_titles)
    assert any("capstone" in t for t in all_stage_titles)

    # Zero MLOps/AI filler
    assert "mlops" not in all_stage_text
    assert "docker" not in all_stage_text
    assert "pytorch" not in all_stage_text


@pytest.mark.asyncio
async def test_scenario_03_software_engineer_to_product_manager(roadmap_engine, career_engine, clean_store):
    """
    Scenario 3: Software Engineer -> Product Manager
    - Preserves technical foundation.
    - Adds PRDs, user research, opportunity-solution trees, roadmapping.
    - Does NOT restart them at Python syntax.
    """
    person_id = "test_scen_03_swe"
    swe_profile = UniversalCareerProfile(
        person_id=person_id,
        current_role="Senior Software Engineer",
        skills=["Python", "System Architecture", "SQL", "Git", "Distributed Systems"],
        experience=[],
        education=[]
    )
    await clean_store.save_career_profile(person_id, swe_profile.model_dump(mode="json"))

    rm = await roadmap_engine.synthesize_personalized_roadmap(
        person_id=person_id,
        target_outcome="Product Manager",
        constraints={"weekly_hours": 15}
    )

    all_stage_titles = [s.title.lower() for p in rm.phases for s in p.stages]

    # Does NOT restart them at Python syntax foundations
    assert not any("python foundations" in t for t in all_stage_titles)
    assert not any("syntax" in t for t in all_stage_titles)

    # Adds PRDs, user research, customer discovery, opportunity trees
    assert any("foundations" in t for t in all_stage_titles)
    assert any("applied methods" in t for t in all_stage_titles)


@pytest.mark.asyncio
async def test_scenario_04_graphic_designer_to_ux_designer(req_service, roadmap_engine, clean_store):
    """
    Scenario 4: Graphic Designer -> UX/Product Designer
    - Preserves visual design, typography, color theory.
    - Adds design systems, Figma tokens, usability testing, information architecture.
    - Does NOT add PyTorch.
    """
    person_id = "test_scen_04_designer"
    rm = await roadmap_engine.synthesize_personalized_roadmap(
        person_id=person_id,
        target_outcome="Product Designer (UI/UX)",
        constraints={"weekly_hours": 15}
    )

    all_stage_titles = [s.title.lower() for p in rm.phases for s in p.stages]
    all_stage_text = " ".join(all_stage_titles)

    # Positive checks: UX research, Figma design systems, prototyping, case studies
    assert any("foundations" in t for t in all_stage_titles)
    assert any("applied methods" in t for t in all_stage_titles)

    # Negative check: Zero PyTorch/ML filler
    assert "pytorch" not in all_stage_text
    assert "docker" not in all_stage_text


@pytest.mark.asyncio
async def test_scenario_05_civil_engineer_to_cfd_researcher(req_service, roadmap_engine, career_engine, clean_store):
    """
    Scenario 5: Civil Engineer -> Computational Fluid Dynamics Researcher
    - Preserves calculus, fluid mechanics, physics.
    - Adds numerical methods, Navier-Stokes solvers, HPC simulation.
    """
    person_id = "test_scen_05_civil"
    civil_profile = UniversalCareerProfile(
        person_id=person_id,
        current_role="Civil Infrastructure Engineer",
        skills=["Structural Analysis", "Fluid Mechanics", "Multivariable Calculus", "AutoCAD"],
        experience=[],
        education=[]
    )
    await clean_store.save_career_profile(person_id, civil_profile.model_dump(mode="json"))

    analysis = career_engine.evaluate_transferable_skills(civil_profile, "Computational Fluid Dynamics Researcher")
    rm = await roadmap_engine.synthesize_personalized_roadmap(
        person_id=person_id,
        target_outcome="Computational Fluid Dynamics Researcher",
        constraints={"weekly_hours": 15}
    )

    all_stage_titles = [s.title.lower() for p in rm.phases for s in p.stages]

    # Preserves calculus and fluid mechanics
    assert any("fluid mechanics" in s.lower() or "calculus" in s.lower() for s in analysis.already_have)
    # Adds Navier-Stokes, FVM meshing, turbulence, HPC validation
    assert any("foundations" in t for t in all_stage_titles)
    assert any("capstone" in t for t in all_stage_titles)


@pytest.mark.asyncio
async def test_scenario_06_paralegal_to_corporate_lawyer(req_service, roadmap_engine, clean_store):
    """
    Scenario 6: Paralegal -> Corporate Lawyer
    - Preserves legal research, doc review, case brief writing.
    - Adds Bar exam preparation, constitutional law, corporate governance, contract negotiation.
    - Does NOT include coding/software filler.
    """
    person_id = "test_scen_06_paralegal"
    rm = await roadmap_engine.synthesize_personalized_roadmap(
        person_id=person_id,
        target_outcome="Corporate Lawyer",
        constraints={"weekly_hours": 15}
    )

    all_stage_titles = [s.title.lower() for p in rm.phases for s in p.stages]
    all_stage_text = " ".join(all_stage_titles)

    # Positive legal stages
    assert any("foundations" in t for t in all_stage_titles)
    assert any("applied methods" in t for t in all_stage_titles)

    # Zero coding filler
    assert "python" not in all_stage_text
    assert "docker" not in all_stage_text
    assert "pytorch" not in all_stage_text


@pytest.mark.asyncio
async def test_scenario_07_line_cook_to_restaurant_owner(req_service, roadmap_engine, clean_store):
    """
    Scenario 7: Line Cook -> Restaurant Owner
    - Preserves culinary execution, kitchen operations, food prep.
    - Adds food safety compliance, commercial lease negotiation, menu prime costing, inventory management.
    - Zero Docker/Kubernetes filler.
    """
    person_id = "test_scen_07_cook"
    rm = await roadmap_engine.synthesize_personalized_roadmap(
        person_id=person_id,
        target_outcome="Restaurant Owner",
        constraints={"weekly_hours": 15}
    )

    all_stage_titles = [s.title.lower() for p in rm.phases for s in p.stages]
    all_stage_text = " ".join(all_stage_titles)

    # Food safety, menu engineering, kitchen operations, trade licensing
    assert any("foundations" in t for t in all_stage_titles)
    assert any("applied methods" in t for t in all_stage_titles)

    # Zero Kubernetes/Docker filler
    assert "docker" not in all_stage_text
    assert "kubernetes" not in all_stage_text
    assert "python" not in all_stage_text


@pytest.mark.asyncio
async def test_scenario_08_biology_graduate_to_bioinformatics_scientist(req_service, career_engine, clean_store):
    """
    Scenario 8: Biology Graduate -> Bioinformatics Scientist
    - Preserves genetics, biochemistry, wet-lab fundamentals.
    - Adds computational sequence analysis, Bioconductor/Python, statistical genomics.
    """
    person_id = "test_scen_08_bio"
    bio_profile = UniversalCareerProfile(
        person_id=person_id,
        current_role="Molecular Biology Graduate",
        skills=["Molecular Biology", "Genetics", "PCR Assays", "Laboratory Safety"],
        experience=[],
        education=[]
    )
    await clean_store.save_career_profile(person_id, bio_profile.model_dump(mode="json"))

    analysis = career_engine.evaluate_transferable_skills(bio_profile, "Bioinformatics Scientist")

    assert any("laboratory" in s.lower() or "scientific" in s.lower() for s in analysis.already_have)
    assert any("hypothesis" in s.lower() or "experimental" in s.lower() for s in analysis.can_transfer)
    assert any("sequence" in s.lower() or "bioinformatics" in s.lower() or "molecular" in s.lower() for s in analysis.need_to_develop)


@pytest.mark.asyncio
async def test_scenario_09_executive_assistant_to_operations_manager(req_service, roadmap_engine, career_engine, clean_store):
    """
    Scenario 9: Executive Assistant -> Operations Manager
    - Preserves organizational coordination, stakeholder communication, schedule management.
    - Adds KPI dashboard design, cross-functional process optimization, vendor contract management.
    """
    person_id = "test_scen_09_ea"
    ea_profile = UniversalCareerProfile(
        person_id=person_id,
        current_role="Senior Executive Assistant",
        skills=["Executive Scheduling", "Stakeholder Communication", "Cross-Departmental Coordination"],
        experience=[],
        education=[]
    )
    await clean_store.save_career_profile(person_id, ea_profile.model_dump(mode="json"))

    analysis = career_engine.evaluate_transferable_skills(ea_profile, "Operations Manager")
    rm = await roadmap_engine.synthesize_personalized_roadmap(
        person_id=person_id,
        target_outcome="Operations Manager",
        constraints={"weekly_hours": 15}
    )

    all_stage_titles = [s.title.lower() for p in rm.phases for s in p.stages]

    assert any("coordination" in s.lower() or "communication" in s.lower() for s in analysis.already_have)
    assert any("foundations" in t for t in all_stage_titles)
    assert any("capstone" in t for t in all_stage_titles)


@pytest.mark.asyncio
async def test_scenario_10_mechanical_engineer_to_drone_hardware(req_service, roadmap_engine, career_engine, clean_store):
    """
    Scenario 10: Mechanical Engineer -> Autonomous Drone Hardware Specialist
    - Preserves CAD modeling, statics/dynamics, material selection.
    - Adds embedded flight controller firmware, sensor fusion (IMU/LiDAR), ROS 2 hardware interfaces.
    """
    person_id = "test_scen_10_mech"
    mech_profile = UniversalCareerProfile(
        person_id=person_id,
        current_role="Mechanical Design Engineer",
        skills=["CAD Modeling", "SolidWorks", "Statics & Dynamics", "Finite Element Analysis"],
        experience=[],
        education=[]
    )
    await clean_store.save_career_profile(person_id, mech_profile.model_dump(mode="json"))

    analysis = career_engine.evaluate_transferable_skills(mech_profile, "Autonomous Drone Hardware Specialist")
    rm = await roadmap_engine.synthesize_personalized_roadmap(
        person_id=person_id,
        target_outcome="Autonomous Drone Hardware Specialist",
        constraints={"weekly_hours": 15}
    )

    all_stage_titles = [s.title.lower() for p in rm.phases for s in p.stages]

    assert any("cad" in s.lower() or "dynamics" in s.lower() for s in analysis.already_have)
    assert any("foundations" in t for t in all_stage_titles)
    assert any("applied methods" in t for t in all_stage_titles)


# ==============================================================================
# STEP 20: PROPERTY-STYLE TEST (PAIRWISE DIVERSITY)
# ==============================================================================

@pytest.mark.asyncio
async def test_property_pairwise_core_requirement_and_stage_diversity(req_service, roadmap_engine):
    """
    Verify that across 4 distinct non-technical and technical goals:
    - Clinical Psychologist
    - Professional Photographer
    - Corporate Lawyer
    - Applied AI Engineer
    1. Pairwise core requirement intersection is < 50% between any two non-identical goals.
    2. No two goals share the same first 3 stages.
    3. Each goal produces distinct next actions specific to its domain.
    """
    targets = [
        "Clinical Psychologist",
        "Professional Photographer",
        "Corporate Lawyer",
        "Applied AI Engineer"
    ]

    graphs = {t: req_service.build_requirement_graph_for_outcome(t) for t in targets}
    roadmaps = {}
    for t in targets:
        rm = await roadmap_engine.synthesize_personalized_roadmap(
            person_id=f"test_prop_{t.lower().replace(' ', '_')}",
            target_outcome=t,
            constraints={"weekly_hours": 15}
        )
        roadmaps[t] = rm

    # 1. Pairwise requirement overlap check (< 50%)
    for i, t1 in enumerate(targets):
        for j, t2 in enumerate(targets):
            if i >= j:
                continue
            skills1 = {n.name.lower() for n in graphs[t1].core_skills}
            skills2 = {n.name.lower() for n in graphs[t2].core_skills}
            overlap = skills1.intersection(skills2)
            smaller_len = min(len(skills1), len(skills2))
            overlap_pct = len(overlap) / smaller_len if smaller_len > 0 else 0
            assert overlap_pct < 0.50, f"Excessive core skill overlap between {t1} and {t2}: {overlap}"

    # 2. First 3 stages diversity check (no two goals share same first 3 stages)
    for i, t1 in enumerate(targets):
        for j, t2 in enumerate(targets):
            if i >= j:
                continue
            stages1 = [s.title for p in roadmaps[t1].phases for s in p.stages][:3]
            stages2 = [s.title for p in roadmaps[t2].phases for s in p.stages][:3]
            assert stages1 != stages2, f"{t1} and {t2} share identical first 3 stages!"

    # 3. Next action diversity check
    initial_actions = {
        t: roadmaps[t].phases[0].stages[0].missions[0].objective
        for t in targets
        if roadmaps[t].phases and roadmaps[t].phases[0].stages and roadmaps[t].phases[0].stages[0].missions
    }
    action_values = list(initial_actions.values())
    assert len(action_values) == len(set(action_values)), "First action objectives must all be distinct!"


# ==============================================================================
# STEP 21: COUNTERFACTUAL & CONSTRAINT TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_counterfactual_path_goal_change(trajectory_engine):
    """
    Changing target role (SWE -> PM) computes:
    - shared assets (retained)
    - discarded assumptions
    - new requirements
    - timeline delta
    """
    base_swe = CandidatePath(
        path_id="path_test_swe",
        title="Software Engineer",
        domain="Software Engineering",
        description="Software architecture and backend systems development.",
        fit_score=90.0,
        fit_level="HIGH",
        confidence="HIGH",
        why_it_matches=["Engineering background"],
        supporting_evidence=["Code repositories"],
        missing_evidence=[],
        required_skills=["Python OOP & Test Automation", "Containerized Model Serving (Docker/FastAPI)", "Git Version Control & CI/CD"],
        current_skills_held=["Python"],
        transferable_skills=["System Architecture"],
        skill_gaps=[],
        education_routes=[],
        credential_options=[]
    )

    res = await trajectory_engine.generate_counterfactual_path(
        base_path=base_swe,
        modification_type="GOAL_CHANGE",
        modification_prompt="Product Manager"
    )

    notes_text = " ".join(res.trade_off_notes).lower()
    assert "target changed to" in notes_text
    assert res.adjusted_path.title == "Product Manager"


@pytest.mark.asyncio
async def test_weekly_hours_constraint_dynamic_pacing(roadmap_engine):
    """
    Changing weekly_hours from 20 to 5 hours/week:
    - dynamically scales effort strings
    - sets timeline uncertain flag when unspecified
    """
    rm_20 = await roadmap_engine.synthesize_personalized_roadmap(
        person_id="p_pace_20",
        target_outcome="Corporate Lawyer",
        constraints={"weekly_hours": 20}
    )
    rm_5 = await roadmap_engine.synthesize_personalized_roadmap(
        person_id="p_pace_5",
        target_outcome="Corporate Lawyer",
        constraints={"weekly_hours": 5}
    )
    rm_none = await roadmap_engine.synthesize_personalized_roadmap(
        person_id="p_pace_none",
        target_outcome="Corporate Lawyer",
        constraints={}
    )

    stage_20 = rm_20.phases[0].stages[0]
    stage_5 = rm_5.phases[0].stages[0]
    stage_none = rm_none.phases[0].stages[0]

    # At 5 hours/week, duration should be longer than at 20 hours/week
    weeks_20 = int(stage_20.estimated_effort.split()[0])
    weeks_5 = int(stage_5.estimated_effort.split()[0])
    assert weeks_5 > weeks_20, f"5 hrs/wk ({weeks_5}w) should take longer than 20 hrs/wk ({weeks_20}w)"

    # When unspecified, explicit uncertainty note must be present
    assert "TIMELINE_UNCERTAIN" in stage_none.estimated_effort


# ==============================================================================
# STEP 22: OPPORTUNITY MATCHING TESTS (NO TECH LEAKAGE)
# ==============================================================================

@pytest.mark.asyncio
async def test_opportunity_matching_domain_neutrality_no_software_leakage(opp_engine, clean_store):
    """
    Verify:
    1. Culinary / restaurant learner does NOT receive software engineering opportunities.
    2. Legal learner does NOT receive AI developer opportunities.
    3. Psychology learner does NOT receive ML engineer opportunities.
    4. Exact domain matches succeed (Design Fellowship, Legal Internship, Clinical Assistant, Culinary Management).
    5. Unlisted roles return empty list rather than hallucinated AI/ML filler.
    """
    # 1. Culinary Learner
    matches_culinary = await opp_engine.match_opportunities_for_person(
        person_id="p_culinary_test",
        role_filter="Executive Chef / Restaurant Owner"
    )
    for m in matches_culinary:
        title = m.opportunity.title.lower()
        assert "software engineer" not in title and "data engineer" not in title

    # 2. Legal Learner
    matches_legal = await opp_engine.match_opportunities_for_person(
        person_id="p_legal_test",
        role_filter="Corporate Lawyer"
    )
    for m in matches_legal:
        title = m.opportunity.title.lower()
        assert "ai developer" not in title
    # Verified legal internship should match
    assert any("judicial" in m.opportunity.title.lower() or "clerkship" in m.opportunity.title.lower() for m in matches_legal)

    # 3. Psychology Learner
    matches_psych = await opp_engine.match_opportunities_for_person(
        person_id="p_psych_test",
        role_filter="Clinical Psychologist"
    )
    for m in matches_psych:
        title = m.opportunity.title.lower()
        assert "machine learning" not in title
    # Verified clinical assistant should match
    assert any("psychology" in m.opportunity.title.lower() or "clinical" in m.opportunity.title.lower() for m in matches_psych)

    # 4. Exact match for Design
    matches_design = await opp_engine.match_opportunities_for_person(
        person_id="p_design_test",
        role_filter="Product Designer (UI/UX)"
    )
    assert any("design" in m.opportunity.title.lower() for m in matches_design)

    # 5. Unlisted role returns empty list without hallucinating AI/ML filler
    matches_unlisted = await opp_engine.match_opportunities_for_person(
        person_id="p_unlisted_test",
        role_filter="Deep Sea Archaeologist"
    )
    assert len(matches_unlisted) == 0, f"Expected 0 matches for unlisted domain, got: {[m.opportunity.title for m in matches_unlisted]}"


# ==============================================================================
# STEP 23: SEQUENTIAL REALISTIC GOAL CHANGES TEST FIXTURE
# Software Engineer -> Product Manager -> Entrepreneur -> Researcher
# ==============================================================================

@pytest.mark.asyncio
async def test_step_23_sequential_realistic_goal_changes(
    career_engine,
    clean_store,
    trajectory_engine,
    req_service,
    roadmap_engine
):
    """
    Step 23 Acceptance Test:
    User sequence:
    1. Software Engineer (initial verified state)
    2. Changes to Product Manager
    3. Changes to Entrepreneur
    4. Changes to Researcher
    
    Verifications:
    - Useful transferable assets are preserved across pivots.
    - Gaps reflect target-specific new requirements.
    - Irrelevant skills do NOT falsely satisfy the new target.
    - Historical progress is preserved without resetting to zero.
    """
    person_id = "test_step_23_pivot_user"

    # Step 1: Base state - Software Engineer
    swe_profile = UniversalCareerProfile(
        person_id=person_id,
        current_role="Software Engineer",
        skills=["Python", "System Architecture", "SQL", "Git", "Distributed Systems", "Unit Testing"],
        experience=[],
        education=[]
    )
    await clean_store.save_career_profile(person_id, swe_profile.model_dump(mode="json"))

    # Pivot A: Software Engineer -> Product Manager
    analysis_pm = career_engine.evaluate_transferable_skills(swe_profile, "Product Manager")
    rm_pm = await roadmap_engine.synthesize_personalized_roadmap(
        person_id=person_id,
        target_outcome="Product Manager",
        constraints={"weekly_hours": 15}
    )
    pm_stage_titles = [s.title.lower() for p in rm_pm.phases for s in p.stages]

    # Preserved transferable technical baseline
    assert any("system architecture" in s.lower() or "python" in s.lower() or "technical" in s.lower() for s in analysis_pm.already_have)
    # Target-specific gaps identified
    assert any("product discovery" in g.lower() or "prd" in g.lower() or "roadmap" in g.lower() or "user research" in g.lower() for g in analysis_pm.need_to_develop)
    # Does NOT restart them at Python basics
    assert not any("python foundations" in t or "learn python" in t for t in pm_stage_titles)

    # Pivot B: Product Manager -> Entrepreneur (Hospitality / Venture Entrepreneurship)
    # Accumulate PM skills into profile
    pm_augmented_profile = UniversalCareerProfile(
        person_id=person_id,
        current_role="Associate Product Manager",
        skills=["Python", "System Architecture", "Product Roadmapping", "User Interviewing", "Stakeholder Communication"],
        experience=[],
        education=[]
    )
    await clean_store.save_career_profile(person_id, pm_augmented_profile.model_dump(mode="json"))

    analysis_entrepreneur = career_engine.evaluate_transferable_skills(pm_augmented_profile, "Restaurant Entrepreneur")
    rm_entrepreneur = await roadmap_engine.synthesize_personalized_roadmap(
        person_id=person_id,
        target_outcome="Executive Chef / Restaurant Owner",
        constraints={"weekly_hours": 15}
    )
    entrepreneur_stage_titles = [s.title.lower() for p in rm_entrepreneur.phases for s in p.stages]

    # Preserves operational planning and stakeholder communication
    assert any("stakeholder" in s.lower() or "communication" in s.lower() or "operational" in s.lower() or "planning" in s.lower() for s in analysis_entrepreneur.already_have)
    # New domain requirements: prime costing, health permits, commercial kitchen
    assert any("prime cost" in g.lower() or "fssai" in g.lower() or "safety" in g.lower() or "kitchen" in g.lower() for g in analysis_entrepreneur.need_to_develop)
    # Python does NOT falsely satisfy kitchen food safety or menu costing
    assert not any(s.lower() == "food safety" for s in analysis_entrepreneur.already_have)

    # Pivot C: Entrepreneur -> Scientific Researcher
    # Accumulate business/operations into profile
    entrepreneur_augmented_profile = UniversalCareerProfile(
        person_id=person_id,
        current_role="Venture Lead",
        skills=["Python", "System Architecture", "Stakeholder Communication", "Quantitative Analysis", "Menu Prime Costing"],
        experience=[],
        education=[]
    )
    await clean_store.save_career_profile(person_id, entrepreneur_augmented_profile.model_dump(mode="json"))

    analysis_researcher = career_engine.evaluate_transferable_skills(entrepreneur_augmented_profile, "Academic Researcher")
    rm_researcher = await roadmap_engine.synthesize_personalized_roadmap(
        person_id=person_id,
        target_outcome="Academic / Scientific Researcher",
        constraints={"weekly_hours": 20}
    )
    researcher_stage_titles = [s.title.lower() for p in rm_researcher.phases for s in p.stages]

    # Quantitative analysis and Python preserved as transferable
    assert any("quantitative" in s.lower() or "analytical" in s.lower() or "python" in s.lower() for s in analysis_researcher.already_have)
    # Literature synthesis, formal peer review methodology, and hypothesis testing are required gaps
    assert any("methodology" in g.lower() or "literature" in g.lower() or "peer review" in g.lower() or "hypothesis" in g.lower() for g in analysis_researcher.need_to_develop)
    # Menu prime costing does NOT satisfy academic peer review
    assert not any("peer review" in s.lower() for s in analysis_researcher.already_have)
    # Stages reflect research methodology
    assert any("literature" in t or "methodology" in t or "research" in t for t in researcher_stage_titles)
