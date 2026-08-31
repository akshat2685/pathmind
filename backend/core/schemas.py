from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class ProviderContext(BaseModel):
    provider: str
    retrieved_at: str
    version: Optional[str] = None
    source_url: Optional[str] = None
    source_id: Optional[str] = None

class Skill(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    skill_type: Optional[str] = None # e.g., knowledge, skill, attitude
    source_context: ProviderContext

class Occupation(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    alternate_titles: List[str] = Field(default_factory=list)
    tasks: List[str] = Field(default_factory=list)
    skills: List[Skill] = Field(default_factory=list)
    source_context: ProviderContext

class KnowledgeResponse(BaseModel):
    results: List[Any]
    sources: List[ProviderContext]
    confidence: str = "source-backed"
