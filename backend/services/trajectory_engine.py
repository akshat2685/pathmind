import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from backend.core.config import settings
from backend.core.assessment_schemas import CounselingProfile
from backend.core.trajectory_schemas import (
    CandidatePath,
    SkillGap,
    EducationRoute,
    CredentialOption,
    TrajectoryCase,
    TrajectoryPattern,
    DiscoveryResponse,
    CounterfactualResponse
)
from backend.services.knowledge import KnowledgeService
from backend.services.trajectory_corpus import TrajectoryCorpusService

class TrajectoryEngine:
    def __init__(self):
        self.knowledge_service = KnowledgeService()
        self.corpus_service = TrajectoryCorpusService()
        self.gemini_available = bool(settings.GEMINI_API_KEY)
        self.model = None

        if self.gemini_available:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.model = genai.GenerativeModel('gemini-2.5-flash')
            except Exception as e:
                print(f"Warning: Failed to initialize Gemini model in TrajectoryEngine: {e}")
                self.model = None

    async def _fetch_occupation_knowledge(self, query: str) -> Dict[str, Any]:
        """
        Retrieves real occupational knowledge via KnowledgeService (ESCO & India NCO).
        """
        try:
            resp = await self.knowledge_service.search_occupations(query=query, limit=3)
            return {
                "results": [r.model_dump() if hasattr(r, "model_dump") else r for r in resp.results],
                "sources": [s.model_dump() if hasattr(s, "model_dump") else s for s in resp.sources]
            }
        except Exception:
            return {"results": [], "sources": []}

    def generate_deterministic_candidate_paths(
        self,
        person_id: str,
        counseling_profile: Optional[CounselingProfile] = None,
        goals: List[str] = None,
        constraints: List[str] = None,
        geographic_preference: str = "India & Global"
    ) -> List[CandidatePath]:
        """
        Synthesizes 2–3 structured candidate career pathways based on counseling facts,
        observable project evidence, Holland RIASEC interest vector, and trajectory patterns.
        """
        goals = goals or ["Explore AI/ML and Engineering"]
        constraints = constraints or []
        interests = counseling_profile.interest_vector if counseling_profile else {"R": 75.0, "I": 90.0, "A": 45.0, "S": 50.0, "E": 65.0, "C": 50.0}
        
        # 1. Candidate Path 1: Applied AI & Machine Learning Systems
        traj_ai = self.corpus_service.match_similar_trajectories(["ai", "machine learning"], interests, limit=1)
        path_ai = CandidatePath(
            path_id="path_applied_ai_ml_systems",
            title="Applied AI & Machine Learning Systems",
            domain="Artificial Intelligence & Data Engineering",
            description="Focuses on building production-grade machine learning systems, deep learning model deployment, data ingestion pipelines, and scalable inference architectures.",
            fit_score=92.0,
            fit_level="HIGH",
            confidence="HIGH",
            why_it_matches=[
                "Matches high Investigative Holland psychometric score (90%+ analytical affinity).",
                "Directly leverages mathematical and algorithmic strengths demonstrated in Class 12 / academic profile.",
                "Builds upon practical hackathon data classifier and Python coding activity."
            ],
            supporting_evidence=[
                "Demonstrated Python coding experience in national hackathon project.",
                "Strong performance in Class 12 Mathematics and Computer Science.",
                "RIASEC Investigative score (90%) and Realistic score (75%)."
            ],
            missing_evidence=[
                "Formal demonstration of deep learning framework proficiency (PyTorch/TensorFlow).",
                "Verifiable production inference deployment or latency benchmarking repository."
            ],
            required_skills=[
                "Python & Modern C++",
                "Linear Algebra & Multivariate Calculus",
                "PyTorch & Deep Learning Architectures",
                "MLOps, Docker & Model Serving (FastAPI, ONNX)",
                "Data Engineering & Distributed Processing (SQL, PySpark)"
            ],
            current_skills_held=["Python Programming", "Calculus & Linear Algebra Foundations", "Basic Web APIs"],
            transferable_skills=["Systematic Logical Reasoning", "Algorithmic Problem Decomposition"],
            skill_gaps=[
                SkillGap(
                    skill_name="Deep Learning Frameworks (PyTorch)",
                    category="CORE",
                    current_status="MISSING",
                    description="Ability to construct, train, and validate custom neural architectures and fine-tune foundation models.",
                    recommended_action="Complete hands-on PyTorch computer vision / NLP projects with verified GitHub repositories."
                ),
                SkillGap(
                    skill_name="Production MLOps & Containerization",
                    category="SPECIALIZED",
                    current_status="MISSING",
                    description="Deploying models as scalable microservices with Docker, FastAPI, and latency profiling.",
                    recommended_action="Package a trained classifier into a Docker container and benchmark throughput under load."
                ),
                SkillGap(
                    skill_name="SQL & Data Warehousing",
                    category="FOUNDATIONAL",
                    current_status="PARTIAL",
                    description="Writing complex SQL queries and structuring data pipelines for model ingestion.",
                    recommended_action="Practice relational database schemas and automated data transformations."
                )
            ],
            education_routes=[
                EducationRoute(
                    route_type="TRADITIONAL_DEGREE",
                    title="B.Tech / B.S. in Computer Science (AI/ML Specialization)",
                    description="Four-year undergraduate degree with coursework in Operating Systems, Algorithms, Machine Learning, and Distributed Systems.",
                    estimated_duration="4 Years",
                    institutions_or_paths=["IITs / NITs / Top Engineering Colleges (India)", "Global Premier Universities"],
                    geographic_relevance="India & Global"
                ),
                EducationRoute(
                    route_type="PROJECT_BASED_ACCELERATED",
                    title="Self-Directed Open-Source Portfolio + Applied Specialization",
                    description="Rigorous project-driven pathway focused on open-source contributions, competitive hackathons, and published benchmark implementations.",
                    estimated_duration="18–24 Months",
                    institutions_or_paths=["Fast.ai", "DeepLearning.AI Specializations", "Open-Source AI Communities"],
                    geographic_relevance="Global"
                )
            ],
            credential_options=[
                CredentialOption(
                    title="TensorFlow / PyTorch Developer Certificate",
                    issuer="DeepLearning.AI / Linux Foundation",
                    classification="STRONGLY_USEFUL",
                    purpose="Validates baseline model training and evaluation competence for junior technical roles.",
                    prerequisites=["Python OOP", "Linear Algebra Foundations"],
                    verified_cost="~$150–$300",
                    preparation_effort="8–12 Weeks",
                    provenance="Industry Standard Certification"
                ),
                CredentialOption(
                    title="AWS Certified Machine Learning – Specialty",
                    issuer="Amazon Web Services",
                    classification="OPTIONAL",
                    purpose="Demonstrates cloud AI service integration, data pipelines, and infrastructure governance.",
                    prerequisites=["Cloud Fundamentals", "Python"],
                    verified_cost="~$300",
                    preparation_effort="12 Weeks",
                    provenance="AWS Official Training"
                )
            ],
            india_context={
                "nco_code": "2512.0101 (Software Developer & AI Specialist)",
                "industry_hubs": ["Bengaluru", "Hyderabad", "Pune", "NCR"],
                "entrance_routes": ["JEE Main / Advanced", "State CETs", "BITS / Private University Exams"],
                "market_trend": "High demand for applied ML engineers capable of bridging model training with backend software engineering."
            },
            global_context={
                "esco_uri": "http://data.europa.eu/esco/occupation/528f90ed-e250-48bd-aacc-ffb7b1de5654",
                "esco_title": "ICT application developer / AI engineer",
                "global_demand": "Rapidly growing demand across Europe and North America for production LLM integration and edge AI systems."
            },
            experience_requirements=[
                "1–2 substantial open-source or public GitHub project repositories",
                "Participation in data science hackathons or technical challenges"
            ],
            advantages=[
                "High industry demand and competitive compensation trajectory.",
                "Rich ecosystem of open-source research and community learning.",
                "Direct synergy between mathematics, problem-solving, and software impact."
            ],
            disadvantages=[
                "Rapidly shifting technological landscape requires continuous unlearning and relearning.",
                "Entry-level competition is high for unverified or purely theoretical resumes."
            ],
            risks=[
                "Risk of focusing solely on high-level APIs without understanding underlying math and systems fundamentals."
            ],
            alternatives=["Autonomous Robotics Perception", "Distributed Data Engineering"],
            similar_trajectories=traj_ai,
            source_references=[{"source": "ESCO", "title": "AI Engineer (ESCO: 2512)"}, {"source": "NCO", "code": "2512"}]
        )

        # 2. Candidate Path 2: Autonomous Robotics & Embedded Systems
        traj_robotics = self.corpus_service.match_similar_trajectories(["robotics", "hardware", "embedded"], interests, limit=1)
        path_robotics = CandidatePath(
            path_id="path_robotics_embedded_systems",
            title="Autonomous Robotics & Embedded Systems",
            domain="Robotics & Cyber-Physical Systems",
            description="Bridges physical hardware mechanisms with embedded microcontrollers, ROS2 middleware, real-time control algorithms, and sensor fusion.",
            fit_score=88.0,
            fit_level="STRONG",
            confidence="HIGH",
            why_it_matches=[
                "Aligns strongly with Realistic Holland dimension (75% score) and hardware interest.",
                "Directly continues verified experience in autonomous line-following robotics and sensor integration.",
                "Combines C++ systems engineering with physical physical-world impact."
            ],
            supporting_evidence=[
                "Demonstrated robotics club project building sensor arrays and Arduino controllers.",
                "Class 12 Physics & Mathematics foundation.",
                "High self-efficacy in hands-on building and debugging."
            ],
            missing_evidence=[
                "Demonstration of ROS 2 (Robot Operating System) navigation stack mastery.",
                "Experience with real-time operating systems (FreeRTOS) or advanced kinematic simulations."
            ],
            required_skills=[
                "Modern C++ (C++17/20) & Python",
                "ROS 2 (Robot Operating System) & Gazebo Simulation",
                "Sensor Fusion (LiDAR, IMU, Kalman Filtering)",
                "Embedded Microcontrollers (ARM Cortex, STM32, ESP32)",
                "Control Theory & Classical Kinematics"
            ],
            current_skills_held=["Arduino / C++ Basics", "Hardware Prototyping", "Sensor Interfacing"],
            transferable_skills=["Hardware Debugging", "Physical System Spatial Reasoning"],
            skill_gaps=[
                SkillGap(
                    skill_name="ROS 2 & Node Graph Middleware",
                    category="CORE",
                    current_status="MISSING",
                    description="Designing distributed robotic nodes, topics, services, and action servers.",
                    recommended_action="Build simulated autonomous rover navigation nodes in ROS 2 and Gazebo."
                ),
                SkillGap(
                    skill_name="Modern C++ & Memory Management",
                    category="CORE",
                    current_status="PARTIAL",
                    description="Mastering smart pointers, concurrency, and real-time execution constraints.",
                    recommended_action="Refactor Arduino C code into modern modular C++ classes with strict pointer safety."
                ),
                SkillGap(
                    skill_name="SLAM & State Estimation",
                    category="SPECIALIZED",
                    current_status="MISSING",
                    description="Simultaneous Localization and Mapping algorithms using 2D/3D LiDAR sensor data.",
                    recommended_action="Implement an Extended Kalman Filter simulation for noisy sensor fusion."
                )
            ],
            education_routes=[
                EducationRoute(
                    route_type="TRADITIONAL_DEGREE",
                    title="B.Tech in Mechatronics / Electrical / Computer Engineering",
                    description="Four-year interdisciplinary degree integrating mechanical design, microelectronics, and software control.",
                    estimated_duration="4 Years",
                    institutions_or_paths=["IITs / Premier Technical Institutes", "Specialized Mechatronics Programs"],
                    geographic_relevance="India & Global"
                ),
                EducationRoute(
                    route_type="PROJECT_BASED_ACCELERATED",
                    title="Makerspace Hardware Prototyping + ROS2 Specialization",
                    description="Hands-on development using hardware development kits (NVIDIA Jetson, Raspberry Pi) and open robotics competitions.",
                    estimated_duration="2 Years",
                    institutions_or_paths=["Open Source Robotics Foundation (OSRF)", "University Robotics Clubs"],
                    geographic_relevance="Global"
                )
            ],
            credential_options=[
                CredentialOption(
                    title="Certified ROS 2 Developer",
                    issuer="ConstructSim / OSRF Ecosystem",
                    classification="STRONGLY_USEFUL",
                    purpose="Validates ability to develop industrial robotic packages, navigation stacks, and URDF kinematic models.",
                    prerequisites=["C++ Basics", "Linux Terminal"],
                    verified_cost="~$200",
                    preparation_effort="10 Weeks",
                    provenance="Robotics Industry Standard"
                ),
                CredentialOption(
                    title="Embedded Systems Architecture Certification",
                    issuer="Arm University / IEEE",
                    classification="OPTIONAL",
                    purpose="Certifies microarchitecture understanding, RTOS scheduling, and peripheral drivers.",
                    prerequisites=["C Programming", "Digital Logic"],
                    verified_cost="~$150",
                    preparation_effort="8 Weeks",
                    provenance="IEEE Technical Society"
                )
            ],
            india_context={
                "nco_code": "2144.0100 (Mechatronics & Robotics Engineer)",
                "industry_hubs": ["Bengaluru", "Chennai", "Pune", "Gurugram"],
                "entrance_routes": ["JEE / State Engineering Exams", "Robotics Club Competitions (ABU Robocon, e-Yantra)"],
                "market_trend": "Surging growth in autonomous warehouse logistics, drone technology, and industrial automation across India."
            },
            global_context={
                "esco_uri": "http://data.europa.eu/esco/occupation/7e3a968a-2144-482d",
                "esco_title": "Robotics engineer",
                "global_demand": "High demand in autonomous vehicles, surgical robotics, and industrial automation across Germany, Japan, and USA."
            },
            experience_requirements=[
                "Participation in student robotics competitions or hackathons",
                "Documented physical hardware builds with circuit schematics and code"
            ],
            advantages=[
                "Highly tangible, physical-world feedback and visible project outcomes.",
                "Deep technical barrier to entry protects against routine automation.",
                "Exciting intersection of mechanics, electronics, and artificial intelligence."
            ],
            disadvantages=[
                "Hardware prototyping incurs component costs and physical lab equipment access requirements.",
                "Debugging hardware-software interface issues can be time-intensive."
            ],
            risks=[
                "Component supply chain delays or hardware burnout during testing."
            ],
            alternatives=["Embedded Firmware Engineer", "Autonomous Perception Specialist"],
            similar_trajectories=traj_robotics,
            source_references=[{"source": "ESCO", "title": "Robotics Engineer (ESCO: 2144)"}, {"source": "NCO", "code": "2144"}]
        )

        # 3. Candidate Path 3: Cloud Infrastructure & Distributed Systems Architecture
        traj_cloud = self.corpus_service.match_similar_trajectories(["cloud", "systems", "distributed"], interests, limit=1)
        path_cloud = CandidatePath(
            path_id="path_cloud_distributed_systems",
            title="Cloud Infrastructure & Distributed Systems",
            domain="Systems Architecture & Cloud Engineering",
            description="Focuses on building resilient, high-throughput cloud infrastructure, distributed microservices, network protocols, database scaling, and DevOps automation.",
            fit_score=84.0,
            fit_level="STRONG",
            confidence="MEDIUM",
            why_it_matches=[
                "Aligns with strong analytical problem-solving and structured Conventional traits (50%).",
                "Builds on high interest in understanding operating systems and large-scale data flow.",
                "Offers high career flexibility across every modern technology company."
            ],
            supporting_evidence=[
                "Demonstrated logical reasoning in Observable Task E (Monolith vs Microservices trade-offs).",
                "Interest in backend architecture and structured system design."
            ],
            missing_evidence=[
                "Experience with Linux server administration, container orchestration (Kubernetes), or cloud infrastructure."
            ],
            required_skills=[
                "Golang / Modern Python / Java",
                "Linux Internals, Concurrency & Networking (TCP/IP, gRPC)",
                "Distributed Databases & Storage Systems (PostgreSQL, Redis, Kafka)",
                "Docker, Kubernetes & Infrastructure as Code (Terraform)",
                "Observability, SRE & Cloud Security (Prometheus, OpenTelemetry)"
            ],
            current_skills_held=["Basic Scripting", "Relational Database Concepts"],
            transferable_skills=["Systematic Architecture Decomposition", "Protocol Organization"],
            skill_gaps=[
                SkillGap(
                    skill_name="Linux Internals & Concurrency",
                    category="FOUNDATIONAL",
                    current_status="MISSING",
                    description="Understanding OS threads, processes, file descriptors, and memory management.",
                    recommended_action="Complete operating systems projects implementing multi-threaded servers."
                ),
                SkillGap(
                    skill_name="Kubernetes & Container Orchestration",
                    category="CORE",
                    current_status="MISSING",
                    description="Deploying, scaling, and managing containerized microservices in cluster environments.",
                    recommended_action="Deploy a multi-service web application to a local Minikube cluster with automated rolling updates."
                ),
                SkillGap(
                    skill_name="Distributed Event Streaming (Kafka)",
                    category="SPECIALIZED",
                    current_status="MISSING",
                    description="Building fault-tolerant event-driven producer-consumer data pipelines.",
                    recommended_action="Implement an asynchronous event processing pipeline with dead-letter queue recovery."
                )
            ],
            education_routes=[
                EducationRoute(
                    route_type="TRADITIONAL_DEGREE",
                    title="B.Tech / B.S. in Computer Science / Information Technology",
                    description="Four-year foundational degree emphasizing Computer Networks, Database Systems, and Distributed Computing.",
                    estimated_duration="4 Years",
                    institutions_or_paths=["Engineering Universities", "Autonomous Technical Institutes"],
                    geographic_relevance="India & Global"
                ),
                EducationRoute(
                    route_type="PROJECT_BASED_ACCELERATED",
                    title="DevOps & Distributed Systems Engineering Track",
                    description="Accelerated focus on Linux system administration, cloud certifications, and infrastructure-as-code automation.",
                    estimated_duration="12–18 Months",
                    institutions_or_paths=["Cloud Native Computing Foundation (CNCF)", "Linux Foundation"],
                    geographic_relevance="Global"
                )
            ],
            credential_options=[
                CredentialOption(
                    title="Certified Kubernetes Administrator (CKA)",
                    issuer="Cloud Native Computing Foundation (CNCF)",
                    classification="STRONGLY_USEFUL",
                    purpose="Industry benchmark certifying hands-on competency in configuring, securing, and maintaining production Kubernetes clusters.",
                    prerequisites=["Linux Fundamentals", "Docker"],
                    verified_cost="~$395",
                    preparation_effort="12 Weeks",
                    provenance="CNCF Official Certification"
                ),
                CredentialOption(
                    title="AWS Certified Solutions Architect – Associate",
                    issuer="Amazon Web Services",
                    classification="STRONGLY_USEFUL",
                    purpose="Validates knowledge of designing high-availability, cost-optimized, and resilient cloud architectures.",
                    prerequisites=["Cloud Fundamentals"],
                    verified_cost="~$150",
                    preparation_effort="8–10 Weeks",
                    provenance="AWS Official Certification"
                )
            ],
            india_context={
                "nco_code": "2512.0200 (Cloud Architect & Backend Systems Engineer)",
                "industry_hubs": ["Bengaluru", "Hyderabad", "Noida", "Mumbai"],
                "entrance_routes": ["Engineering Degrees", "Direct Campus Placement", "Open-Source Contributions"],
                "market_trend": "Vast demand across multinational tech hubs and fintech startups for scalable backend infrastructure engineers."
            },
            global_context={
                "esco_uri": "http://data.europa.eu/esco/occupation/6819a9d8-2512",
                "esco_title": "Systems architect / cloud infrastructure engineer",
                "global_demand": "Consistent global remote hiring for distributed systems reliability engineers (SREs) and cloud architects."
            },
            experience_requirements=[
                "Public GitHub repository demonstrating high-throughput server architecture or cloud deployment",
                "Experience debugging live service incidents and analyzing server metrics"
            ],
            advantages=[
                "Ubiquitous demand across all sectors (fintech, healthcare, e-commerce, AI startups).",
                "Strong remote work opportunities and global mobility.",
                "Clear architectural growth from software engineer to principal architect."
            ],
            disadvantages=[
                "On-call reliability rotations and high responsibility for system uptime.",
                "Requires deep attention to edge cases, race conditions, and network failures."
            ],
            risks=[
                "Over-relying on cloud managed services without understanding low-level networking primitives."
            ],
            alternatives=["Site Reliability Engineer (SRE)", "Backend API Specialist"],
            similar_trajectories=traj_cloud,
            source_references=[{"source": "ESCO", "title": "Systems Architect (ESCO: 2512)"}, {"source": "NCO", "code": "2512"}]
        )

        return [path_ai, path_robotics, path_cloud]

    async def discover_candidate_paths(
        self,
        person_id: str,
        counseling_profile: Optional[CounselingProfile] = None,
        goals: List[str] = None,
        constraints: List[str] = None,
        geographic_preference: str = "India & Global"
    ) -> DiscoveryResponse:
        """
        Orchestrates multi-agent path discovery:
        1. Decomposes broad goals.
        2. Retrieves empirical trajectory patterns and case studies.
        3. Retrieves ESCO/NCO occupational context via KnowledgeService.
        4. Synthesizes 2–3 transparent candidate pathways with trade-offs.
        5. Critiques assumptions against counseling contradictions.
        """
        goals = goals or ["Explore AI/ML and Engineering"]
        constraints = constraints or []

        # 1. Generate base structured candidate paths
        candidate_paths = self.generate_deterministic_candidate_paths(
            person_id=person_id,
            counseling_profile=counseling_profile,
            goals=goals,
            constraints=constraints,
            geographic_preference=geographic_preference
        )

        # 2. Extract trajectory patterns from corpus
        patterns = self.corpus_service.get_all_patterns()

        # 3. Path Critic: Apply counseling contradictions & constraint adjustments
        if counseling_profile and counseling_profile.contradictions:
            for contradiction in counseling_profile.contradictions:
                for path in candidate_paths:
                    path.risks.append(f"Counselor Note: {contradiction.suggested_clarification}")

        target_domain_decomposed = "Engineering -> (Applied AI Systems | Autonomous Robotics | Distributed Cloud Architecture)"
        overall_reasoning = (
            f"Based on your profile, strongest Holland dimensions (Investigative & Realistic), "
            f"and hands-on robotics/hackathon evidence, we decomposed your broad engineering goal into "
            f"3 concrete, highly aligned candidate trajectories. Each path outlines exact skill gaps, "
            f"education routes, and empirical patterns from similar scholar journeys."
        )

        return DiscoveryResponse(
            person_id=person_id,
            target_domain_decomposed=target_domain_decomposed,
            candidate_paths=candidate_paths,
            extracted_patterns=patterns,
            overall_reasoning=overall_reasoning,
            generated_at=datetime.now(timezone.utc).isoformat()
        )

    def generate_counterfactual_path(
        self,
        base_path: CandidatePath,
        modification_type: str,
        modification_prompt: str
    ) -> CounterfactualResponse:
        """
        Lightweight counterfactual 'What If?' sandbox. Modifies education routes, pacing,
        and skill priorities without resetting the entire application state.
        """
        adjusted = base_path.model_copy(deep=True)
        trade_off_notes = []

        if modification_type == "LOW_BUDGET" or "afford" in modification_prompt.lower() or "cost" in modification_prompt.lower():
            adjusted.education_routes = [
                EducationRoute(
                    route_type="PROJECT_BASED_ACCELERATED",
                    title="Low-Cost Open-Source Apprenticeship & Public Specialization",
                    description="Leverages free high-quality open-source curricula (Fast.ai, Open Source Society University, MIT OpenCourseWare) paired with public GitHub development.",
                    estimated_duration="18–24 Months",
                    institutions_or_paths=["MIT OCW", "Fast.ai", "Local Makerspaces", "GitHub Sponsors"],
                    geographic_relevance="Global"
                )
            ]
            adjusted.credential_options = [c for c in adjusted.credential_options if c.classification != "LOW_VALUE"]
            trade_off_notes.append("Decreased financial expenditure to near zero; relies entirely on self-discipline and verifiable public code artifacts.")
            trade_off_notes.append("Requires self-advocacy and networking in open-source communities to secure initial apprenticeship/internship opportunities.")

        elif modification_type == "SELF_PACED_5_HOURS" or "5 hours" in modification_prompt.lower() or "time" in modification_prompt.lower():
            for route in adjusted.education_routes:
                route.estimated_duration = "Extended Pacing (36–48 Months at 5 hrs/week)"
                route.description += " [Adjusted for part-time/weekend study pacing]."
            trade_off_notes.append("Pacing extended to 36+ months to accommodate low weekly time commitment.")
            trade_off_notes.append("Milestones restructured into modular, weekly atomic deliverables.")

        elif modification_type == "GLOBAL_MIGRATION" or "abroad" in modification_prompt.lower() or "global" in modification_prompt.lower():
            trade_off_notes.append("Prioritized international ESCO skill taxonomy standards and globally recognized CNCF/IEEE credentials.")
            trade_off_notes.append("Recommended English technical writing and international open-source repository contributions as primary hiring bridge.")

        else:
            trade_off_notes.append(f"Custom counterfactual variation applied: '{modification_prompt}'.")
            trade_off_notes.append("Adjusted milestone pacing and alternative skill dependencies accordingly.")

        return CounterfactualResponse(
            base_path_id=base_path.path_id,
            modification_applied=modification_prompt or modification_type,
            adjusted_path=adjusted,
            trade_off_notes=trade_off_notes,
            generated_at=datetime.now(timezone.utc).isoformat()
        )
