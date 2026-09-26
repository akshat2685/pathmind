"""
Verified Curriculum & Knowledge Registry for PATHMIND College Engineering MVP.
Fetches authoritative curricula, verified source records, and authentic resources
directly from the Supabase relational database.
"""

from typing import List, Dict, Any, Optional
from backend.core.college_schemas import (
    UniversityRecord,
    CurriculumRecord,
    SubjectRecord,
    CurriculumUnit,
    EngineeringBranch,
    VerificationStatus,
    ResourceRecord,
    PYQSetRecord,
    PYQQuestionRecord
)
from backend.services.supabase_adapter import get_supabase_adapter

async def get_all_universities() -> List[UniversityRecord]:
    adapter = get_supabase_adapter()
    if not adapter.client:
        return []
    res = adapter.client.table("universities").select("*").execute()
    return [UniversityRecord(**row) for row in (res.data or [])]

async def search_universities(query: str) -> List[UniversityRecord]:
    adapter = get_supabase_adapter()
    if not adapter.client:
        return []
        
    q = query.strip().lower()
    if not q:
        return await get_all_universities()
        
    res = adapter.client.table("universities").select("*").ilike("normalized_name", f"%{q}%").execute()
    return [UniversityRecord(**row) for row in (res.data or [])]

async def get_university_by_id(univ_id: str) -> Optional[UniversityRecord]:
    try:
        adapter = get_supabase_adapter()
        if not adapter.client:
            return None

        res = adapter.client.table("universities").select("*").eq("university_id", univ_id).execute()
        if res.data:
            return UniversityRecord(**res.data[0])
        return None
    except Exception:
        # Never 500 the caller on a provider hiccup; "unknown" is honest.
        return None

async def get_curriculum(university_id: str, branch: EngineeringBranch, semester: int) -> Optional[CurriculumRecord]:
    try:
        return await _get_curriculum_inner(university_id, branch, semester)
    except Exception:
        # A provider hiccup must read as "no verified curriculum", never a 500.
        return None


async def _get_curriculum_inner(university_id: str, branch: EngineeringBranch, semester: int) -> Optional[CurriculumRecord]:
    adapter = get_supabase_adapter()
    if not adapter.client:
        return None

    # GENERAL_OTHER is a graceful fallback per PRD §3: never a refusal, but
    # zero fake engineering data — an honest empty curriculum.
    if branch == EngineeringBranch.GENERAL_OTHER:
        return CurriculumRecord(
            curriculum_id=f"curriculum_general_other_{university_id}_s{semester}",
            university_id=university_id,
            program_id=None,
            semester=semester,
            verification_status=VerificationStatus.UNVERIFIABLE,
            branch=branch.value,
            subjects=[],
        )

    # Find program by branch/university
    # Then find curriculum
    prog_res = adapter.client.table("programs").select("program_id").eq("university_id", university_id).eq("branch", branch.value).execute()
    if not prog_res.data:
        return None
    
    prog_id = prog_res.data[0]["program_id"]
    
    curr_res = adapter.client.table("curricula").select("*").eq("university_id", university_id).eq("program_id", prog_id).eq("semester", semester).execute()
    if not curr_res.data:
        return None
        
    curr_dict = curr_res.data[0]
    
    # Fetch subjects
    cs_res = adapter.client.table("curriculum_subjects").select("subject_id").eq("curriculum_id", curr_dict["curriculum_id"]).execute()
    
    subjects = []
    if cs_res.data:
        sub_ids = [r["subject_id"] for r in cs_res.data]
        # Since Python client doesn't support easy `in` filter without specific syntax, we can query them:
        if sub_ids:
            subs_res = adapter.client.table("subjects").select("*").in_("subject_id", sub_ids).execute()
            for s_row in (subs_res.data or []):
                # Fetch units for subject + curriculum
                units_res = adapter.client.table("curriculum_units").select("*").eq("curriculum_id", curr_dict["curriculum_id"]).eq("subject_id", s_row["subject_id"]).order("unit").execute()
                s_row["units"] = [CurriculumUnit(**u) for u in (units_res.data or [])]
                subjects.append(SubjectRecord(**s_row))
                
    curr_dict["subjects"] = subjects
    curr_dict["branch"] = branch.value
    return CurriculumRecord(**curr_dict)

async def get_pyqs_for_subject(university_id: Optional[str], subject_id: str) -> Optional[PYQSetRecord]:
    adapter = get_supabase_adapter()
    if not adapter.client:
        return None

    query = adapter.client.table("pyq_sets").select("*").eq("subject_id", subject_id)
    if university_id:
        query = query.eq("university_id", university_id)
    res = query.order("exam_year", desc=True).limit(1).execute()
    if not res.data:
        return None
        
    pyq_dict = res.data[0]
    q_res = adapter.client.table("pyq_questions").select("*").eq("pyq_set_id", pyq_dict["pyq_set_id"]).execute()
    pyq_dict["questions"] = [PYQQuestionRecord(**q) for q in (q_res.data or [])]
    return PYQSetRecord(**pyq_dict)

async def get_resources_for_subject(subject_id: str) -> List[ResourceRecord]:
    """Verified learning resources linked to a subject (learning_resources)."""
    adapter = get_supabase_adapter()
    if not adapter.client:
        return []
    res = (adapter.client.table("learning_resources").select("*")
           .eq("subject_id", subject_id).execute())
    records = []
    for row in (res.data or []):
        try:
            records.append(ResourceRecord(**row))
        except Exception:
            continue
    return records
