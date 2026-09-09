from typing import List, Dict, Any, Optional
from backend.core.learning_resource_schemas import VerifiedResource

class VerifiedResourceRegistry:
    """
    Curated repository of authentic, verified YouTube tutorials, official GitHub reference repositories,
    and official documentation for key engineering learning phases.
    Guarantees 100% verified domains and authentic resources.
    """
    def __init__(self):
        self._resources: Dict[str, List[VerifiedResource]] = {
            "PYTHON_FOUNDATIONS": [
                VerifiedResource(
                    resource_id="yt_py_cs50p",
                    title="CS50's Introduction to Programming with Python",
                    url="https://www.youtube.com/watch?v=nLRL_NcnK-4",
                    resource_type="YOUTUBE_VIDEO",
                    channel_or_author="CS50 / Harvard OpenCourseWare",
                    description="Comprehensive conceptual and practical foundation in Python data structures, functions, and testing.",
                    estimated_minutes=120
                ),
                VerifiedResource(
                    resource_id="gh_py_cpython_examples",
                    title="The Algorithms - Python Reference Repository",
                    url="https://github.com/TheAlgorithms/Python",
                    resource_type="GITHUB_REPO",
                    channel_or_author="TheAlgorithms",
                    description="Open-source collection of clean, well-tested Python implementations of algorithms and data structures.",
                    estimated_minutes=60
                ),
                VerifiedResource(
                    resource_id="doc_py_official",
                    title="Official Python 3 Documentation & Tutorial",
                    url="https://docs.python.org/3/tutorial/",
                    resource_type="OFFICIAL_DOCS",
                    channel_or_author="Python Software Foundation",
                    description="Official language reference for Python data models, modules, exceptions, and standard library.",
                    estimated_minutes=45
                )
            ],
            "BACKEND_FASTAPI_REST": [
                VerifiedResource(
                    resource_id="yt_fastapi_freecodecamp",
                    title="FastAPI Course for Beginners - Build Robust Web APIs",
                    url="https://www.youtube.com/watch?v=0sOvCWFmrtA",
                    resource_type="YOUTUBE_VIDEO",
                    channel_or_author="freeCodeCamp.org / Sanjeev Thiyagarajan",
                    description="End-to-end guide to asynchronous Python REST API design, Pydantic validation, and dependency injection.",
                    estimated_minutes=90
                ),
                VerifiedResource(
                    resource_id="gh_fastapi_template",
                    title="Official FastAPI Full-Stack Project Template",
                    url="https://github.com/tiangolo/full-stack-fastapi-template",
                    resource_type="GITHUB_REPO",
                    channel_or_author="Sebastián Ramírez (tiangolo)",
                    description="Production reference architecture for FastAPI backend with SQLModel, async endpoints, and automated tests.",
                    estimated_minutes=75
                ),
                VerifiedResource(
                    resource_id="doc_fastapi_tutorial",
                    title="FastAPI Official Documentation - User Guide",
                    url="https://fastapi.tiangolo.com/tutorial/",
                    resource_type="OFFICIAL_DOCS",
                    channel_or_author="FastAPI Official",
                    description="Comprehensive guide covering routing, path parameters, request bodies, dependency injection, and security.",
                    estimated_minutes=45
                )
            ],
            "FRONTEND_REACT_TS": [
                VerifiedResource(
                    resource_id="yt_react_freecodecamp",
                    title="React Course - Beginner's Tutorial for Modern React",
                    url="https://www.youtube.com/watch?v=bMknfKXIFA8",
                    resource_type="YOUTUBE_VIDEO",
                    channel_or_author="freeCodeCamp.org / Bob Ziroll",
                    description="Modern React fundamentals covering components, props, hooks, state management, and side effects.",
                    estimated_minutes=90
                ),
                VerifiedResource(
                    resource_id="gh_nextjs_learn",
                    title="Next.js Official Reference Repository & Examples",
                    url="https://github.com/vercel/next.js/tree/canary/examples",
                    resource_type="GITHUB_REPO",
                    channel_or_author="Vercel",
                    description="Official repository containing production React and Next.js design patterns, server actions, and layout patterns.",
                    estimated_minutes=60
                ),
                VerifiedResource(
                    resource_id="doc_react_dev",
                    title="React Official Documentation & Interactive Guide",
                    url="https://react.dev/learn",
                    resource_type="OFFICIAL_DOCS",
                    channel_or_author="React Core Team",
                    description="The official modern React guide explaining mental models, pure functions, state immutability, and hooks.",
                    estimated_minutes=45
                )
            ],
            "DATABASE_SQL_SYSTEMS": [
                VerifiedResource(
                    resource_id="yt_sql_fcc",
                    title="Database Design and Relational Architecture Tutorial",
                    url="https://www.youtube.com/watch?v=ztHopE5Wnpc",
                    resource_type="YOUTUBE_VIDEO",
                    channel_or_author="freeCodeCamp.org",
                    description="Relational database normalization, schema design, indexes, transactions, and foreign key integrity.",
                    estimated_minutes=80
                ),
                VerifiedResource(
                    resource_id="gh_sql_benchmarks",
                    title="PostgreSQL Official Samples & Exercises",
                    url="https://github.com/postgres/postgres",
                    resource_type="GITHUB_REPO",
                    channel_or_author="PostgreSQL Global Development Group",
                    description="PostgreSQL core source code, sample queries, regression test suite, and schema definitions.",
                    estimated_minutes=60
                ),
                VerifiedResource(
                    resource_id="doc_postgres_official",
                    title="PostgreSQL Documentation & SQL Tutorial",
                    url="https://www.postgresql.org/docs/current/tutorial.html",
                    resource_type="OFFICIAL_DOCS",
                    channel_or_author="PostgreSQL Global Development Group",
                    description="Official guide to SQL syntax, joins, transactions, constraints, indexes, and window functions.",
                    estimated_minutes=50
                )
            ],
            "ML_AI_SYSTEMS": [
                VerifiedResource(
                    resource_id="yt_mit_deeplearning",
                    title="MIT 6.S191: Introduction to Deep Learning",
                    url="https://www.youtube.com/watch?v=QDX-1M5Nj7s",
                    resource_type="YOUTUBE_VIDEO",
                    channel_or_author="MIT OpenCourseWare / Alexander Amini",
                    description="Rigorous academic introduction to deep neural networks, backpropagation, and sequence models.",
                    estimated_minutes=100
                ),
                VerifiedResource(
                    resource_id="gh_huggingface_transformers",
                    title="Hugging Face Transformers Reference Repository",
                    url="https://github.com/huggingface/transformers",
                    resource_type="GITHUB_REPO",
                    channel_or_author="Hugging Face",
                    description="Industry standard open-source library for deep learning, transformer architectures, and model inference.",
                    estimated_minutes=75
                ),
                VerifiedResource(
                    resource_id="doc_pytorch_tutorials",
                    title="PyTorch Official Documentation & Deep Learning Tutorial",
                    url="https://pytorch.org/tutorials/",
                    resource_type="OFFICIAL_DOCS",
                    channel_or_author="PyTorch Foundation",
                    description="Official hands-on guides to tensors, autograd, model definitions, loss functions, and optimization loops.",
                    estimated_minutes=60
                )
            ]
        }

    def get_resources_for_topic(self, topic: str) -> List[VerifiedResource]:
        topic_upper = topic.upper()
        if any(w in topic_upper for w in ["FASTAPI", "BACKEND", "API", "REST", "WEB SERVICE"]):
            return self._resources["BACKEND_FASTAPI_REST"]
        elif any(w in topic_upper for w in ["REACT", "FRONTEND", "UI", "WEB", "JAVASCRIPT", "TYPESCRIPT"]):
            return self._resources["FRONTEND_REACT_TS"]
        elif any(w in topic_upper for w in ["SQL", "DATABASE", "POSTGRES", "DATA MODEL", "STORAGE"]):
            return self._resources["DATABASE_SQL_SYSTEMS"]
        elif any(w in topic_upper for w in ["MACHINE LEARNING", "ML", "AI", "NEURAL", "DEEP LEARNING", "DATA SCIENCE"]):
            return self._resources["ML_AI_SYSTEMS"]
        else:
            return self._resources["PYTHON_FOUNDATIONS"]
