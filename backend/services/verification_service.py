"""
Verification service for the PATHMIND main product.

Flow position: sign in -> name -> aspiration -> status card -> VERIFICATION
-> test -> personalized path.

What this module does:
  * `get_requirements(user_type)` — the field catalog each user type must
    fill in. Pure data, no I/O.
  * `validate_submission(user_type, data)` — required-field + type checks.
    Pure, no I/O.
  * `evaluate_checks(user_type, data)` — deterministic plausibility checks
    on submitted values (ranges only). Pure, no I/O, NO AI, NO fabrication:
    it only validates what the learner actually submitted.
  * `VerificationService` — orchestrates submit -> store -> auto-evaluate.

HONESTY RULES:
  - Verification NEVER invents facts about the learner.
  - Salary/revenue ranges are ALWAYS optional (sensitive); they are never
    required and never affect the verdict.
  - Documents are optional supporting evidence; self-declared values drive
    the deterministic checks.
  - Verdicts are coarse: VERIFIED / NEEDS_REVIEW / REJECTED, with explicit
    machine-checkable reasons. No confidence theater.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# User types (must match the frontend status cards)
# ---------------------------------------------------------------------------
USER_TYPES = ("school", "college", "professional", "business", "switcher", "lifelong")

# Field spec keys: name, label, type (text|number|select|file), required,
# help, and optionally options (for select).
_REQUIREMENTS: Dict[str, Dict[str, Any]] = {
    "school": {
        "title": "School student verification",
        "description": (
            "Confirm your school details with your latest report card. "
            "Marks are required; uploading the marksheet itself is optional."
        ),
        "fields": [
            {
                "name": "class_grade",
                "label": "Current class",
                "type": "select",
                "required": True,
                "options": [str(i) for i in range(1, 13)],
                "help": "Which class are you studying in right now?",
            },
            {
                "name": "board",
                "label": "Board",
                "type": "select",
                "required": True,
                "options": ["CBSE", "ICSE", "State Board", "IB", "IGCSE", "NIOS", "Other"],
                "help": "Your school education board.",
            },
            {
                "name": "last_marks_pct",
                "label": "Last exam marks (%)",
                "type": "number",
                "required": True,
                "help": "Overall percentage in your most recent final exam.",
            },
            {
                "name": "school_name",
                "label": "School name",
                "type": "text",
                "required": False,
                "help": "Optional — helps personalize, never shared.",
            },
            {
                "name": "marksheet",
                "label": "Marksheet / report card",
                "type": "file",
                "required": False,
                "help": "Optional supporting document. Your typed marks above are what we check.",
            },
        ],
    },
    "college": {
        "title": "College student verification",
        "description": (
            "Confirm your degree and latest semester results. "
            "Result details are required; the document upload is optional."
        ),
        "fields": [
            {
                "name": "degree",
                "label": "Degree",
                "type": "text",
                "required": True,
                "help": "e.g. B.Tech, B.Sc, B.Com, BA, MBBS",
            },
            {
                "name": "branch",
                "label": "Branch / major",
                "type": "text",
                "required": True,
                "help": "e.g. Computer Science, Mechanical, Economics",
            },
            {
                "name": "current_semester",
                "label": "Current semester",
                "type": "number",
                "required": True,
                "help": "Which semester are you in right now? (1-12)",
            },
            {
                "name": "latest_sgpa",
                "label": "Latest SGPA (0-10)",
                "type": "number",
                "required": True,
                "help": "SGPA of your most recently completed semester.",
            },
            {
                "name": "cgpa",
                "label": "CGPA (0-10)",
                "type": "number",
                "required": False,
                "help": "Overall CGPA so far, if you know it.",
            },
            {
                "name": "college_name",
                "label": "College / university",
                "type": "text",
                "required": False,
                "help": "Optional — helps personalize, never shared.",
            },
            {
                "name": "result_doc",
                "label": "Semester result",
                "type": "file",
                "required": False,
                "help": "Optional supporting document. Your typed results above are what we check.",
            },
        ],
    },
    "professional": {
        "title": "Working professional verification",
        "description": (
            "Confirm your current role and experience. Salary details are "
            "strictly optional and never required."
        ),
        "fields": [
            {
                "name": "current_role",
                "label": "Current role",
                "type": "text",
                "required": True,
                "help": "Your job title, e.g. Frontend Developer, Accountant.",
            },
            {
                "name": "years_experience",
                "label": "Years of experience",
                "type": "number",
                "required": True,
                "help": "Total professional experience in years (decimals ok, e.g. 2.5).",
            },
            {
                "name": "industry",
                "label": "Industry",
                "type": "text",
                "required": False,
                "help": "e.g. IT services, healthcare, education.",
            },
            {
                "name": "company",
                "label": "Company",
                "type": "text",
                "required": False,
                "help": "Optional — never shared or contacted.",
            },
            {
                "name": "salary_range",
                "label": "Salary range (optional)",
                "type": "select",
                "required": False,
                "options": [
                    "Prefer not to say",
                    "Under 3 LPA",
                    "3-6 LPA",
                    "6-12 LPA",
                    "12-25 LPA",
                    "25+ LPA",
                ],
                "help": "Sensitive and optional — does not affect verification.",
            },
            {
                "name": "salary_slip",
                "label": "Salary slip",
                "type": "file",
                "required": False,
                "help": "Optional supporting document. Never required.",
            },
        ],
    },
    "business": {
        "title": "Business owner verification",
        "description": (
            "Tell us about your business. Revenue details are strictly "
            "optional and never required."
        ),
        "fields": [
            {
                "name": "business_type",
                "label": "Type of business",
                "type": "text",
                "required": True,
                "help": "e.g. retail shop, SaaS startup, restaurant, freelancing.",
            },
            {
                "name": "years_running",
                "label": "Years running",
                "type": "number",
                "required": True,
                "help": "How long has the business been operating?",
            },
            {
                "name": "your_role",
                "label": "Your role",
                "type": "select",
                "required": False,
                "options": ["Founder", "Co-founder", "Partner", "Owner", "Manager", "Other"],
                "help": "Your role in the business.",
            },
            {
                "name": "team_size",
                "label": "Team size",
                "type": "number",
                "required": False,
                "help": "Number of people working with you (0 if solo).",
            },
            {
                "name": "revenue_range",
                "label": "Revenue range (optional)",
                "type": "select",
                "required": False,
                "options": [
                    "Prefer not to say",
                    "Under 10L / year",
                    "10L - 50L / year",
                    "50L - 2Cr / year",
                    "2Cr+ / year",
                ],
                "help": "Sensitive and optional — does not affect verification.",
            },
        ],
    },
    "switcher": {
        "title": "Career switcher verification",
        "description": (
            "Tell us where you are now and where you want to go, plus any "
            "experience relevant to the target field."
        ),
        "fields": [
            {
                "name": "current_field",
                "label": "Current field",
                "type": "text",
                "required": True,
                "help": "The field you work (or study) in today.",
            },
            {
                "name": "target_field",
                "label": "Target field",
                "type": "text",
                "required": True,
                "help": "The field you want to switch into.",
            },
            {
                "name": "relevant_experience",
                "label": "Relevant experience",
                "type": "text",
                "required": True,
                "help": "Any courses, projects, freelance work, or self-study relevant to the target field.",
            },
            {
                "name": "years_in_current",
                "label": "Years in current field",
                "type": "number",
                "required": False,
                "help": "How long you have been in your current field.",
            },
        ],
    },
    "lifelong": {
        "title": "Lifelong learner verification",
        "description": (
            "Tell us what you want to learn and where you stand today. "
            "No documents needed — this is self-declared."
        ),
        "fields": [
            {
                "name": "areas_of_interest",
                "label": "Areas of interest",
                "type": "text",
                "required": True,
                "help": "What do you want to learn? e.g. photography, stock markets, baking.",
            },
            {
                "name": "self_assessed_level",
                "label": "Current level",
                "type": "select",
                "required": True,
                "options": ["Complete beginner", "Some exposure", "Intermediate", "Advanced"],
                "help": "Honest self-assessment — there are no wrong answers.",
            },
            {
                "name": "weekly_hours",
                "label": "Hours per week you can give",
                "type": "number",
                "required": False,
                "help": "Realistic weekly learning time.",
            },
        ],
    },
}


def get_requirements(user_type: str) -> Dict[str, Any]:
    """Return the verification field catalog for a user type. Pure."""
    key = (user_type or "").strip().lower()
    if key not in _REQUIREMENTS:
        raise ValueError(
            f"Unknown user_type '{user_type}'. Must be one of: {', '.join(USER_TYPES)}"
        )
    spec = _REQUIREMENTS[key]
    return {"user_type": key, **spec}


def validate_submission(user_type: str, data: Dict[str, Any]) -> List[str]:
    """
    Validate a verification submission against the field catalog.
    Returns a list of human-readable error strings (empty = valid). Pure.
    """
    spec = get_requirements(user_type)
    errors: List[str] = []
    data = data or {}
    for field in spec["fields"]:
        name = field["name"]
        value = data.get(name)
        is_empty = value is None or (isinstance(value, str) and not value.strip())
        if field["required"] and is_empty:
            errors.append(f"'{field['label']}' is required.")
            continue
        if is_empty:
            continue
        ftype = field["type"]
        if ftype == "number":
            try:
                float(value)
            except (TypeError, ValueError):
                errors.append(f"'{field['label']}' must be a number.")
        elif ftype == "select" and "options" in field:
            if str(value) not in [str(o) for o in field["options"]]:
                errors.append(
                    f"'{field['label']}' must be one of the provided options."
                )
    return errors


def _num(data: Dict[str, Any], name: str) -> Optional[float]:
    try:
        return float(data.get(name))
    except (TypeError, ValueError):
        return None


def evaluate_checks(user_type: str, data: Dict[str, Any]) -> Tuple[str, List[str]]:
    """
    Deterministic plausibility checks on SUBMITTED values only.
    Returns (status, reasons) where status is one of
    VERIFIED / NEEDS_REVIEW / REJECTED. Pure, no I/O, no AI.

    - VERIFIED: every required field present and every value within a
      plausible range.
    - NEEDS_REVIEW: values are possible but unusual (flagged for a human).
    - REJECTED: values are impossible or self-contradictory.
    """
    data = data or {}
    key = (user_type or "").strip().lower()
    reasons: List[str] = []
    review: List[str] = []

    # Required-field re-check (defense in depth; submit already validates).
    for field in _REQUIREMENTS.get(key, {}).get("fields", []):
        v = data.get(field["name"])
        if field["required"] and (v is None or (isinstance(v, str) and not v.strip())):
            reasons.append(f"Missing required field: {field['label']}.")

    if key == "school":
        marks = _num(data, "last_marks_pct")
        if marks is not None:
            if marks < 0 or marks > 100:
                reasons.append(f"Marks {marks}% is impossible (must be 0-100).")
            elif marks == 100:
                review.append("Marks of exactly 100% are rare — flagged for review.")
        grade = _num(data, "class_grade")
        if grade is not None and (grade < 1 or grade > 12):
            reasons.append(f"Class {grade} is outside 1-12.")

    elif key == "college":
        sem = _num(data, "current_semester")
        if sem is not None:
            if sem < 1 or int(sem) != sem:
                reasons.append("Semester must be a positive whole number.")
            elif sem > 12:
                reasons.append(f"Semester {int(sem)} exceeds any known program length.")
            elif sem > 8:
                review.append(
                    f"Semester {int(sem)} is unusual (most programs are <= 8) — flagged for review."
                )
        for fname, label in (("latest_sgpa", "SGPA"), ("cgpa", "CGPA")):
            gpa = _num(data, fname)
            if gpa is not None:
                if gpa < 0 or gpa > 10:
                    reasons.append(f"{label} {gpa} is impossible (must be 0-10).")
                elif gpa == 10:
                    review.append(f"{label} of exactly 10 is rare — flagged for review.")

    elif key == "professional":
        exp = _num(data, "years_experience")
        if exp is not None:
            if exp < 0:
                reasons.append("Years of experience cannot be negative.")
            elif exp > 50:
                reasons.append(f"{exp} years of experience is not plausible.")
            elif exp > 35:
                review.append(f"{exp} years of experience is unusual — flagged for review.")
        team = _num(data, "team_size")
        if team is not None and team < 0:
            reasons.append("Team size cannot be negative.")

    elif key == "business":
        yrs = _num(data, "years_running")
        if yrs is not None:
            if yrs < 0:
                reasons.append("Years running cannot be negative.")
            elif yrs > 80:
                reasons.append(f"{yrs} years running is not plausible.")
        team = _num(data, "team_size")
        if team is not None:
            if team < 0 or int(team) != team:
                reasons.append("Team size must be a non-negative whole number.")
            elif team > 100000:
                review.append(f"Team size {int(team)} is unusual — flagged for review.")

    elif key == "switcher":
        cur = str(data.get("current_field") or "").strip().lower()
        tgt = str(data.get("target_field") or "").strip().lower()
        if cur and tgt and cur == tgt:
            review.append(
                "Current field and target field are identical — flagged for review."
            )
        yrs = _num(data, "years_in_current")
        if yrs is not None and yrs < 0:
            reasons.append("Years in current field cannot be negative.")

    elif key == "lifelong":
        hrs = _num(data, "weekly_hours")
        if hrs is not None:
            if hrs < 0:
                reasons.append("Weekly hours cannot be negative.")
            elif hrs > 168:
                reasons.append("Weekly hours cannot exceed 168.")
            elif hrs > 60:
                review.append(f"{hrs} hours/week is unusually high — flagged for review.")

    if reasons:
        return "REJECTED", reasons
    if review:
        return "NEEDS_REVIEW", review
    return "VERIFIED", ["All submitted values are within plausible ranges."]


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class VerificationService:
    """
    Orchestrates verification submit -> store -> deterministic evaluation.

    `store` is duck-typed: it must provide save_verification(person_id, record),
    get_verification(person_id), get_verification_by_id(verification_id), and
    update_verification_status(verification_id, status, reasons).
    """

    def __init__(self, store):
        self.store = store

    async def submit_verification(
        self,
        person_id: str,
        user_type: str,
        data: Dict[str, Any],
        document_urls: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        key = (user_type or "").strip().lower()
        if key not in USER_TYPES:
            raise ValueError(
                f"Unknown user_type '{user_type}'. Must be one of: {', '.join(USER_TYPES)}"
            )
        errors = validate_submission(key, data or {})
        if errors:
            raise ValueError("Invalid submission: " + " ".join(errors))

        record = {
            "user_type": key,
            "verification_data": dict(data or {}),
            "document_urls": list(document_urls or []),
            "status": "PENDING",
            "verified_at": None,
            "created_at": _utcnow_iso(),
            "updated_at": _utcnow_iso(),
        }
        saved = await self.store.save_verification(person_id, record)
        # Auto-evaluate deterministically right after submit.
        return await self.evaluate_verification(saved["id"])

    async def evaluate_verification(self, verification_id: str) -> Dict[str, Any]:
        record = await self.store.get_verification_by_id(verification_id)
        if not record:
            raise ValueError(f"No verification found with id {verification_id}.")
        status, reasons = evaluate_checks(
            record.get("user_type", ""), record.get("verification_data") or {}
        )
        updated = await self.store.update_verification_status(
            verification_id, status, reasons
        )
        return updated

    async def get_status(self, person_id: str) -> Optional[Dict[str, Any]]:
        return await self.store.get_verification(person_id)
