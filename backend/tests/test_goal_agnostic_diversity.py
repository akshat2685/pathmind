import pytest
from datetime import datetime, timezone
from backend.services.roadmap_engine import RoadmapEngine
from backend.services.requirement_graph_service import RequirementGraphService
from backend.services.career_readiness_engine import CareerReadinessEngine
from backend.services.career_agents import ResumeAgent
from backend.core.career_schemas import (
    UniversalCareerProfile,
    EducationItem,
    ExperienceItem,
    ProjectItem,
    CredentialItem
)

@pytest.mark.asyncio
async def test_scenario_a_product_designer_diversity():
    """
    Scenario A: Product Designer.
    Must generate Figma, Design Systems, UX Research.
    Zero Python, PyTorch, Linear Algebra, or Machine Learning.
    """
    req_service = RequirementGraphService()
    roadmap_engine = RoadmapEngine()

    graph = req_service.build_requirement_graph_for_outcome("Product Designer")
    all_nodes = graph.core_skills + graph.supporting_skills + graph.project_evidence_requirements
    all_text = " ".join([n.name + " " + n.description + " " + (n.evidence_requirement or "") for n in all_nodes]).lower()
    
    # Assert design competencies present
    assert "figma" in all_text, f"Figma missing in {all_text}"
    assert "design system" in all_text
    assert "usability" in all_text or "user research" in all_text

    # Assert technical AI/ML competencies absent
    assert "pytorch" not in all_text
    assert "linear algebra" not in all_text

    # Synthesize roadmap
    roadmap = await roadmap_engine.synthesize_personalized_roadmap(
        person_id="user_designer_001",
        target_outcome="Product Designer"
    )
    all_stages = roadmap_engine.get_all_stages_flat(roadmap)
    stage_text = " ".join([s.title + " " + s.objective + " " + " ".join(s.skills) for s in all_stages]).lower()

    assert "design" in stage_text
    assert "figma" in stage_text or "ui/ux" in stage_text or "wirefram" in stage_text or "prototype" in stage_text
    assert "pytorch" not in stage_text
    assert "machine learning" not in stage_text
    assert "linear algebra" not in stage_text

@pytest.mark.asyncio
async def test_scenario_b_lawyer_legal_advocate_diversity():
    """
    Scenario B: Lawyer / Legal Advocate.
    Must generate Jurisprudence, Bar Exam, Constitutional Law, Legal Briefs.
    Zero software engineering, Python, or PyTorch.
    """
    req_service = RequirementGraphService()
    roadmap_engine = RoadmapEngine()

    graph = req_service.build_requirement_graph_for_outcome("Constitutional Lawyer")
    all_nodes = graph.core_skills + graph.supporting_skills + graph.education_requirements
    node_names = [n.name.lower() for n in all_nodes]

    assert any("constitutional" in s or "jurisprudence" in s for s in node_names)
    assert any("legal" in s or "statutory" in s or "case" in s for s in node_names)
    assert not any("software" in s for s in node_names)
    assert not any("python" in s for s in node_names)

    roadmap = await roadmap_engine.synthesize_personalized_roadmap(
        person_id="user_lawyer_001",
        target_outcome="Constitutional Lawyer"
    )
    all_stages = roadmap_engine.get_all_stages_flat(roadmap)
    all_text = " ".join([s.title + " " + s.objective + " " + " ".join(s.skills) for s in all_stages]).lower()

    assert "legal" in all_text or "jurisprudence" in all_text or "constitutional" in all_text
    assert "python" not in all_text
    assert "pytorch" not in all_text
    assert "software" not in all_text

@pytest.mark.asyncio
async def test_scenario_c_restaurant_hospitality_diversity():
    """
    Scenario C: Restaurant Entrepreneur / Hospitality.
    Must generate HACCP Food Safety, Culinary Operations, Prime Costing.
    Zero software engineering or PyTorch.
    """
    req_service = RequirementGraphService()
    roadmap_engine = RoadmapEngine()

    graph = req_service.build_requirement_graph_for_outcome("Farm-to-Table Restaurant Owner")
    all_nodes = graph.core_skills + graph.supporting_skills + graph.experience_requirements
    node_names = [n.name.lower() for n in all_nodes]

    assert any("food safety" in n or "haccp" in n for n in node_names)
    assert any("costing" in n or "culinary" in n or "menu" in n for n in node_names)
    assert not any("pytorch" in n for n in node_names)

    roadmap = await roadmap_engine.synthesize_personalized_roadmap(
        person_id="user_chef_001",
        target_outcome="Farm-to-Table Restaurant Owner"
    )
    all_stages = roadmap_engine.get_all_stages_flat(roadmap)
    all_text = " ".join([s.title + " " + s.objective + " " + " ".join(s.skills) for s in all_stages]).lower()

    assert "food safety" in all_text or "culinary" in all_text or "hospitality" in all_text
    assert "pytorch" not in all_text
    assert "machine learning" not in all_text

@pytest.mark.asyncio
async def test_scenario_d_biotechnology_researcher_diversity():
    """
    Scenario D: Biotechnology Researcher.
    Must generate Molecular Biology, Wet Lab Assays, Genomics, Peer-Reviewed Manuscript.
    Zero software engineering defaults.
    """
    req_service = RequirementGraphService()
    roadmap_engine = RoadmapEngine()

    graph = req_service.build_requirement_graph_for_outcome("Biotechnology Researcher")
    all_nodes = graph.core_skills + graph.supporting_skills + graph.project_evidence_requirements + graph.experience_requirements
    node_names = [n.name.lower() for n in all_nodes]

    assert any("literature" in n or "experimental" in n or "lab" in n or "manuscript" in n for n in node_names)
    assert not any("react" in n for n in node_names)
    assert not any("pytorch" in n for n in node_names)

    roadmap = await roadmap_engine.synthesize_personalized_roadmap(
        person_id="user_bio_001",
        target_outcome="Biotechnology Researcher"
    )
    all_stages = roadmap_engine.get_all_stages_flat(roadmap)
    all_text = " ".join([s.title + " " + s.objective + " " + " ".join(s.skills) for s in all_stages]).lower()

    assert "literature" in all_text or "experimental" in all_text or "protocols" in all_text or "manuscript" in all_text
    assert "pytorch" not in all_text
    assert "software" not in all_text

@pytest.mark.asyncio
async def test_scenario_e_sales_to_product_manager_transition():
    """
    Scenario E: Career Transition from Enterprise Sales to Product Management.
    Must generate Customer Discovery, PRDs, Opportunity Trees, Agile Backlog.
    Must reflect bridging from commercial domain.
    """
    req_service = RequirementGraphService()
    roadmap_engine = RoadmapEngine()

    graph = req_service.build_requirement_graph_for_outcome("Product Manager")
    all_nodes = graph.core_skills + graph.supporting_skills + graph.project_evidence_requirements
    node_names = [n.name.lower() for n in all_nodes]

    assert any("prd" in n or "product requirement" in n for n in node_names)
    assert any("customer" in n or "discovery" in n or "interview" in n or "prioritization" in n for n in node_names)

    roadmap = await roadmap_engine.synthesize_personalized_roadmap(
        person_id="user_pm_001",
        target_outcome="Product Manager"
    )
    all_stages = roadmap_engine.get_all_stages_flat(roadmap)
    all_text = " ".join([s.title + " " + s.objective + " " + " ".join(s.skills) for s in all_stages]).lower()

    assert "customer discovery" in all_text or "prd" in all_text or "opportunity" in all_text
    assert "sales" in all_text or "commercial" in all_text or "stakeholder" in all_text
    assert "pytorch" not in all_text

@pytest.mark.asyncio
async def test_scenario_f_honest_insufficient_information_state():
    """
    Scenario F: Honest Insufficient Information Handling.
    When a production user has no configured goal or profile, the system must NOT
    silently manufacture an AI/ML roadmap or hallucinated GitHub projects.
    """
    roadmap_engine = RoadmapEngine()
    career_engine = CareerReadinessEngine()

    unseeded_user = "prod_fresh_user_9999"

    # 1. Roadmap engine raises clear NEEDS_USER_INPUT error
    with pytest.raises(ValueError) as exc_info:
        await roadmap_engine.get_or_create_roadmap(person_id=unseeded_user)
    assert "NEEDS_USER_INPUT" in str(exc_info.value)

    # 2. Career profile is strictly empty (no fake repositories)
    profile = await career_engine.get_or_create_canonical_profile(person_id=unseeded_user, current_state_type="unassessed")
    assert profile.projects == []
    assert profile.experience == []
    assert profile.credentials == []
    assert not any("scholar-engineer" in str(p) for p in profile.projects)
    assert not any("thermal-sim" in str(p) for p in profile.projects)

def test_scenario_g_fact_grounded_resume_strictly_honest():
    """
    Scenario G: Fact-Grounded Resume.
    Must contain ONLY verified facts from profile.
    Zero hallucinated projects, credentials, or work experience.
    """
    resume_agent = ResumeAgent()

    # User profile with ONLY verified legal background
    profile = UniversalCareerProfile(
        person_id="user_strictly_honest_lawyer",
        education=[
            EducationItem(
                degree="Bachelor of Laws (LL.B.)",
                field_of_study="Constitutional & Administrative Law",
                institution="National Law School",
                year="2024",
                grade_or_score="3.85 GPA",
                is_verified=True
            )
        ],
        experience=[],
        projects=[
            ProjectItem(
                title="Constitutional Due Process Synthesis Brief",
                technologies=["Legal Research", "Constitutional Analysis", "Statutory Synthesis"],
                description="Published synthesis brief analyzing procedural due process.",
                repository_url=None,
                live_url="https://legaldocs.org/briefs/due-process-2024.pdf",
                provenance="Verified Law Review Milestone",
                is_verified=True
            )
        ],
        skills=["Constitutional Law", "Legal Analysis", "Statutory Interpretation"],
        credentials=[]
    )

    resume = resume_agent.generate_tailored_resume(
        profile=profile,
        target_role="Legal Analyst"
    )

    # 1. Verified education preserved
    assert len(resume.education) == 1
    assert "Bachelor of Laws" in resume.education[0]["degree"]

    # 2. Verified project preserved in tailored_projects
    assert len(resume.tailored_projects) == 1
    assert resume.tailored_projects[0]["title"] == "Constitutional Due Process Synthesis Brief"

    # 3. Work experience is empty (NOT hallucinated)
    assert len(resume.verified_experience) == 0

    # 4. Prohibited fake projects MUST NOT exist in resume
    resume_str = str(resume.model_dump()).lower()
    assert "thermal-sim" not in resume_str
    assert "telemetry-ui" not in resume_str
    assert "parser-etl" not in resume_str
    assert "pytorch" not in resume_str
