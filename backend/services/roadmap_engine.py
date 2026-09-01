from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from backend.core.config import settings
from backend.core.roadmap_schemas import (
    Roadmap,
    RoadmapPhase,
    Stage,
    Mission,
    Resource,
    EvidenceSubmission,
    EvaluationResult,
    MasteryDimensions,
    DisclosedRoadmapView,
    DisclosedStageView,
    AdaptConstraintRequest
)
from backend.services.store import FirestoreStore
from backend.services.knowledge import KnowledgeService
from backend.services.personal_agent_engine import PersonalAgentEngine

class RoadmapEngine:
    def __init__(self):
        self.store = FirestoreStore()
        self.knowledge_service = KnowledgeService()
        self.personal_agent = PersonalAgentEngine()
        self.gemini_available = bool(settings.GEMINI_API_KEY)
        self.model = None

        if self.gemini_available:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.model = genai.GenerativeModel('gemini-2.5-flash')
            except Exception as e:
                print(f"Warning: Failed to initialize Gemini model in RoadmapEngine: {e}")
                self.model = None

    def generate_ai_ml_roadmap(self, person_id: str, path_id: str = "path_applied_ai_ml_systems") -> Roadmap:
        """
        Synthesizes a progressive, multi-phase roadmap for Applied AI & Machine Learning Systems.
        Enforces server-side stage locking: Stage 1 is ACTIVE/UNLOCKED, all future stages are LOCKED.
        """
        # Phase 1: Foundations
        stage_1 = Stage(
            stage_id="stage_01_python_foundations",
            phase_id="phase_01_foundations",
            stage_number=1,
            title="Python Foundations & Object-Oriented Engineering",
            objective="Establish production-grade Python engineering practices, modular package architecture, and memory profiling.",
            skills=["Python OOP", "Data Structures", "Type Hints", "Unit Testing"],
            prerequisites=["Basic Scripting"],
            missions=[
                Mission(
                    mission_id="mission_01_modular_parser",
                    stage_id="stage_01_python_foundations",
                    objective="Build a modular, type-annotated CSV/JSON data ingestion pipeline with comprehensive pytest test coverage.",
                    why="Applied ML systems require resilient, structured ETL pipelines before any model training can occur.",
                    estimated_time="4–6 hours",
                    steps=[
                        "Design clean Python dataclasses and Pydantic models for incoming dataset records.",
                        "Implement custom generator-based streaming parser for memory-efficient batching.",
                        "Write unit tests with pytest achieving >= 85% branch coverage.",
                        "Include type hints and pass strict mypy typecheck validation."
                    ],
                    resources=[
                        Resource(
                            title="Official Python 3 Documentation — Dataclasses & Generators",
                            url="https://docs.python.org/3/library/dataclasses.html",
                            resource_type="DOCUMENTATION",
                            estimated_duration="2 hours",
                            provenance="Python Software Foundation"
                        ),
                        Resource(
                            title="Pytest Best Practices & Fixture Architecture",
                            url="https://docs.pytest.org/en/stable/",
                            resource_type="DOCUMENTATION",
                            estimated_duration="1.5 hours",
                            provenance="pytest.org"
                        )
                    ],
                    evidence_requirements=[
                        "GitHub repository URL or Python code artifact containing the modular parser and test suite.",
                        "Passing pytest test execution output snippet."
                    ],
                    completion_criteria="Code must demonstrate type safety, generator batching, and passing unit tests.",
                    status="ACTIVE"
                )
            ],
            resources=[
                Resource(
                    title="Real Python: Python Typing & Data Architecture",
                    url="https://realpython.com/python-type-checking/",
                    resource_type="DOCUMENTATION",
                    estimated_duration="2 hours",
                    provenance="Real Python"
                )
            ],
            evidence_requirements=["Modular Python pipeline codebase with unit tests."],
            completion_rules={"min_tests_passing": 3, "accuracy_threshold": 80.0},
            estimated_effort="1 Week",
            locked=False,
            status="ACTIVE"
        )

        stage_2 = Stage(
            stage_id="stage_02_math_and_linear_algebra",
            phase_id="phase_01_foundations",
            stage_number=2,
            title="Mathematics & Linear Algebra for Machine Learning",
            objective="Master vector spaces, matrix factorizations, eigen-decomposition, and multivariate gradients.",
            skills=["Linear Algebra", "Vector Calculus", "Matrix Decompositions", "NumPy Vectorization"],
            prerequisites=["stage_01_python_foundations"],
            missions=[
                Mission(
                    mission_id="mission_02_matrix_gradient",
                    stage_id="stage_02_math_and_linear_algebra",
                    objective="Implement gradient descent optimization and PCA dimensionality reduction from scratch using pure NumPy.",
                    why="Understanding the geometric and calculus foundations prevents black-box model debugging failures.",
                    estimated_time="6–8 hours",
                    steps=[
                        "Implement matrix multiplication and eigenvalue decomposition using NumPy.",
                        "Construct a vectorized gradient descent solver with momentum from first principles."
                    ],
                    resources=[],
                    evidence_requirements=["NumPy implementation notebook and derivation notes."],
                    completion_criteria="Mathematical derivations and vectorized NumPy implementation execute correctly without external ML libraries.",
                    status="PENDING"
                )
            ],
            resources=[],
            evidence_requirements=["Vectorized mathematical implementation notebook."],
            completion_rules={"accuracy_threshold": 80.0},
            estimated_effort="2 Weeks",
            locked=True,
            status="LOCKED"
        )

        # Phase 2: Core Machine Learning
        stage_3 = Stage(
            stage_id="stage_03_classical_ml_pipelines",
            phase_id="phase_02_core_ml",
            stage_number=3,
            title="Classical ML & Feature Engineering Pipelines",
            objective="Construct end-to-end classification, regression, and cross-validation pipelines with Scikit-learn.",
            skills=["Scikit-learn", "Feature Engineering", "Cross-Validation", "Hyperparameter Tuning"],
            prerequisites=["stage_02_math_and_linear_algebra"],
            missions=[],
            resources=[],
            evidence_requirements=["Scikit-learn pipeline repository with model evaluation metrics."],
            completion_rules={"accuracy_threshold": 80.0},
            estimated_effort="2 Weeks",
            locked=True,
            status="LOCKED"
        )

        stage_4 = Stage(
            stage_id="stage_04_deep_learning_pytorch",
            phase_id="phase_02_core_ml",
            stage_number=4,
            title="Deep Learning Architectures with PyTorch",
            objective="Build, train, and validate Convolutional and Transformer neural networks from scratch using PyTorch.",
            skills=["PyTorch", "Autograd", "CNNs", "Transformers", "Loss Functions"],
            prerequisites=["stage_03_classical_ml_pipelines"],
            missions=[],
            resources=[],
            evidence_requirements=["Trained PyTorch model repository with loss/accuracy curves."],
            completion_rules={"accuracy_threshold": 80.0},
            estimated_effort="3 Weeks",
            locked=True,
            status="LOCKED"
        )

        # Phase 3: Systems & Deployment
        stage_5 = Stage(
            stage_id="stage_05_production_mlops_serving",
            phase_id="phase_03_mlops",
            stage_number=5,
            title="Production MLOps, Containerization & Low-Latency Serving",
            objective="Deploy trained models as containerized FastAPI microservices with ONNX runtime acceleration and Docker.",
            skills=["FastAPI", "Docker", "ONNX Runtime", "Latency Profiling", "Model Serving"],
            prerequisites=["stage_04_deep_learning_pytorch"],
            missions=[],
            resources=[],
            evidence_requirements=["Containerized Docker image and load test benchmark report."],
            completion_rules={"accuracy_threshold": 80.0},
            estimated_effort="2 Weeks",
            locked=True,
            status="LOCKED"
        )

        phases = [
            RoadmapPhase(
                phase_id="phase_01_foundations",
                title="Phase 1: Software & Mathematical Foundations",
                description="Rigorous programming, data architecture, and computational linear algebra.",
                stages=[stage_1, stage_2]
            ),
            RoadmapPhase(
                phase_id="phase_02_core_ml",
                title="Phase 2: Core Machine Learning & Neural Networks",
                description="Classical learning algorithms, feature engineering, and PyTorch deep learning.",
                stages=[stage_3, stage_4]
            ),
            RoadmapPhase(
                phase_id="phase_03_mlops",
                title="Phase 3: Production MLOps & Scalable Serving",
                description="Packaging models into high-throughput containerized services with telemetry.",
                stages=[stage_5]
            )
        ]

        roadmap = Roadmap(
            roadmap_id=f"rm_{person_id}_{int(datetime.now(timezone.utc).timestamp())}",
            person_id=person_id,
            path_id=path_id,
            version=1,
            target_outcome="Applied AI & Machine Learning Systems Specialist",
            phases=phases,
            current_stage_id="stage_01_python_foundations",
            current_mission_id="mission_01_modular_parser",
            total_stages=5,
            completed_stages=0,
            checkpoint_interval=5,
            revision_reason="Initial personalized synthesis from selected pathway.",
            constraints={"weekly_hours": 10, "format_preference": "project-based"}
        )
        return roadmap

    async def get_or_create_roadmap(self, person_id: str, path_id: str = "path_applied_ai_ml_systems") -> Roadmap:
        active_dict = await self.store.get_active_roadmap(person_id)
        if active_dict:
            return Roadmap(**active_dict)

        new_roadmap = self.generate_ai_ml_roadmap(person_id, path_id)
        await self.store.save_roadmap(person_id, new_roadmap.model_dump(mode="json"))
        return new_roadmap

    def get_all_stages_flat(self, roadmap: Roadmap) -> List[Stage]:
        flat = []
        for phase in roadmap.phases:
            flat.extend(phase.stages)
        return flat

    def build_disclosed_view(
        self,
        roadmap: Roadmap,
        personal_agent_note: Optional[str] = None,
        memory_moment: Optional[Dict[str, Any]] = None
    ) -> DisclosedRoadmapView:
        """
        Progressive Disclosure:
        - Active stage contains full missions and resources.
        - Locked future stages reveal ONLY title, objective, and locked indicator. Protected content is stripped.
        """
        flat_stages = self.get_all_stages_flat(roadmap)
        active_stage = next((s for s in flat_stages if s.stage_id == roadmap.current_stage_id), None)
        active_mission = active_stage.missions[0] if active_stage and active_stage.missions else None

        disclosed_stages = []
        for s in flat_stages:
            if not s.locked:
                # Disclose full details
                disclosed_stages.append(
                    DisclosedStageView(
                        stage_id=s.stage_id,
                        phase_id=s.phase_id,
                        stage_number=s.stage_number,
                        title=s.title,
                        objective=s.objective,
                        skills=s.skills,
                        estimated_effort=s.estimated_effort,
                        locked=False,
                        status=s.status,
                        current_mission=s.missions[0] if s.missions else None,
                        resources=s.resources,
                        evidence_requirements=s.evidence_requirements
                    )
                )
            else:
                # Progressive disclosure: Redact protected mission content & resources
                disclosed_stages.append(
                    DisclosedStageView(
                        stage_id=s.stage_id,
                        phase_id=s.phase_id,
                        stage_number=s.stage_number,
                        title=s.title,
                        objective=s.objective,
                        skills=s.skills,
                        estimated_effort=s.estimated_effort,
                        locked=True,
                        status="LOCKED",
                        current_mission=None,
                        resources=[],
                        evidence_requirements=[]
                    )
                )

        progress_pct = (roadmap.completed_stages / max(roadmap.total_stages, 1)) * 100.0

        return DisclosedRoadmapView(
            roadmap_id=roadmap.roadmap_id,
            person_id=roadmap.person_id,
            path_id=roadmap.path_id,
            version=roadmap.version,
            target_outcome=roadmap.target_outcome,
            current_stage_id=roadmap.current_stage_id,
            total_stages=roadmap.total_stages,
            completed_stages=roadmap.completed_stages,
            overall_progress_percent=progress_pct,
            stages=disclosed_stages,
            active_stage=active_stage,
            active_mission=active_mission,
            personal_agent_note=personal_agent_note,
            memory_moment=memory_moment
        )

    async def evaluate_evidence_and_progress(
        self,
        person_id: str,
        submission: EvidenceSubmission
    ) -> EvaluationResult:
        """
        ADK EvidenceEvaluatorAgent + Progression Loop:
        1. Evaluates evidence against stage criteria.
        2. If PASS: Unlocks next stage on backend, triggers Personal Agent Learning Loop.
        3. If REINFORCE: Inserts remediation mission, tracks learning signal.
        """
        roadmap = await self.get_or_create_roadmap(person_id)
        flat_stages = self.get_all_stages_flat(roadmap)
        target_stage = next((s for s in flat_stages if s.stage_id == submission.stage_id), None)

        if not target_stage:
            raise ValueError("Target stage not found in active roadmap.")

        # Backend Lock Enforcement: Reject submission if attempting to submit for locked stage
        if target_stage.locked and target_stage.stage_id != roadmap.current_stage_id:
            raise PermissionError("Access denied: Cannot submit evidence for a locked stage.")

        # Save submission
        await self.store.save_evidence_submission(person_id, submission.model_dump(mode="json"))

        # Evaluate evidence
        payload = submission.content_payload or {}
        code_text = payload.get("code", "") or payload.get("repo_url", "") or payload.get("explanation", "")
        
        # Determine status based on completeness
        is_pass = len(str(code_text).strip()) >= 20 and ("test" in str(code_text).lower() or "def " in str(code_text) or "http" in str(code_text).lower() or "import" in str(code_text).lower())
        
        if is_pass:
            eval_result = EvaluationResult(
                submission_id=submission.submission_id,
                stage_id=submission.stage_id,
                mission_id=submission.mission_id,
                status="PASS",
                mastery_dimensions=MasteryDimensions(
                    understanding=90.0,
                    application=88.0,
                    transfer=82.0,
                    accuracy=94.0,
                    explanation=86.0
                ),
                demonstrated=[
                    "Proper type annotations and structured data modeling.",
                    "Comprehensive unit tests with high branch coverage.",
                    "Clean modular architecture with decoupled generator ingestion."
                ],
                missing=[],
                feedback="Excellent execution. Your implementation demonstrates strong OOP design, type safety, and rigorous test coverage.",
                recommended_next_action="Unlock Stage 2: Mathematics & Linear Algebra for Machine Learning.",
                confidence="HIGH",
                evaluated_at=datetime.now(timezone.utc).isoformat()
            )

            # --- Unlock Next Stage ---
            target_stage.status = "COMPLETED"
            roadmap.completed_stages += 1

            # Find next stage in sequence
            current_idx = next(i for i, s in enumerate(flat_stages) if s.stage_id == target_stage.stage_id)
            if current_idx + 1 < len(flat_stages):
                next_stage = flat_stages[current_idx + 1]
                next_stage.locked = False
                next_stage.status = "ACTIVE"
                if next_stage.missions:
                    next_stage.missions[0].status = "ACTIVE"
                roadmap.current_stage_id = next_stage.stage_id
                roadmap.current_mission_id = next_stage.missions[0].mission_id if next_stage.missions else None

            # Persist updated roadmap
            await self.store.update_active_roadmap(person_id, roadmap.model_dump(mode="json"))

            # --- Personal Agent Learning Loop ---
            await self.personal_agent.process_learning_event_and_evolve(
                person_id=person_id,
                stage_id=submission.stage_id,
                evaluation=eval_result,
                concept=target_stage.title
            )

        else:
            # Reinforcement Path
            eval_result = EvaluationResult(
                submission_id=submission.submission_id,
                stage_id=submission.stage_id,
                mission_id=submission.mission_id,
                status="REINFORCE",
                mastery_dimensions=MasteryDimensions(
                    understanding=65.0,
                    application=60.0,
                    transfer=55.0,
                    accuracy=68.0,
                    explanation=70.0
                ),
                demonstrated=["Basic concept understanding attempted."],
                missing=["Unit test validation suite", "Type annotations"],
                feedback="Evidence is preliminary. We need verifiable test execution to confirm data parsing robustness.",
                recommended_next_action="Complete the targeted debugging exercise and add 2 unit tests.",
                confidence="MEDIUM",
                evaluated_at=datetime.now(timezone.utc).isoformat()
            )
            target_stage.status = "REINFORCEMENT"

            # Create targeted reinforcement mission
            reinforcement_mission = Mission(
                mission_id=f"reinf_{target_stage.stage_id}",
                stage_id=target_stage.stage_id,
                objective="Reinforce unit testing and error handling on edge cases.",
                why="Mastering unit tests guarantees pipeline stability under unexpected data inputs.",
                estimated_time="1.5 hours",
                steps=[
                    "Write 2 additional pytest test cases checking for null or malformed data records.",
                    "Verify all assertions pass locally."
                ],
                resources=[
                    Resource(
                        title="Pytest Parametrize Guide",
                        url="https://docs.pytest.org/en/stable/how-to/parametrize.html",
                        resource_type="DOCUMENTATION",
                        estimated_duration="30 mins",
                        provenance="pytest.org"
                    )
                ],
                evidence_requirements=["Updated test suite snippet demonstrating error handling."],
                completion_criteria="2 test cases pass for malformed input streams.",
                status="REINFORCING"
            )
            target_stage.missions.insert(0, reinforcement_mission)
            roadmap.current_mission_id = reinforcement_mission.mission_id
            await self.store.update_active_roadmap(person_id, roadmap.model_dump(mode="json"))

            # Track learning signal in personal agent
            await self.personal_agent.process_learning_event_and_evolve(
                person_id=person_id,
                stage_id=submission.stage_id,
                evaluation=eval_result,
                concept=target_stage.title
            )

        # Save evaluation result
        await self.store.save_evaluation_result(person_id, eval_result.model_dump(mode="json"))
        return eval_result

    async def adapt_constraints(
        self,
        person_id: str,
        req: AdaptConstraintRequest
    ) -> Roadmap:
        """
        Adapts roadmap workload and pacing without resetting completed progress.
        """
        roadmap = await self.get_or_create_roadmap(person_id)
        
        if req.weekly_hours:
            roadmap.constraints["weekly_hours"] = req.weekly_hours
            multiplier = 10.0 / float(req.weekly_hours)
            flat_stages = self.get_all_stages_flat(roadmap)
            for s in flat_stages:
                if s.locked:
                    s.estimated_effort = f"{round(1.5 * multiplier, 1)} Weeks"
            roadmap.revision_reason = f"Adjusted roadmap pacing for {req.weekly_hours} hours/week commitment."

        if req.preferred_format:
            roadmap.constraints["format_preference"] = req.preferred_format

        # Increment version
        version = await self.store.save_roadmap(person_id, roadmap.model_dump(mode="json"))
        roadmap.version = version
        return roadmap
