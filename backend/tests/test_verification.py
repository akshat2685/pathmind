"""
Tests for the user verification step (sign in -> name -> aspiration ->
status card -> VERIFICATION -> test -> personalized path).

Covers the pure functions (requirements catalog, submission validation,
deterministic evaluation) and the VerificationService orchestration with a
fake store — no database, no AI, no network.
"""
import pytest

from backend.services.verification_service import (
    USER_TYPES,
    VerificationService,
    evaluate_checks,
    get_requirements,
    validate_submission,
)


class FakeStore:
    """Duck-typed stand-in for PmStore's verification methods."""

    def __init__(self):
        self.rows = {}
        self._seq = 0

    async def save_verification(self, person_id, record):
        self._seq += 1
        row = {"id": f"verif-{self._seq}", "person_id": person_id, **record}
        self.rows[row["id"]] = row
        return row

    async def get_verification(self, person_id):
        for row in self.rows.values():
            if row["person_id"] == person_id:
                return row
        return None

    async def get_verification_by_id(self, verification_id):
        return self.rows.get(verification_id)

    async def update_verification_status(self, verification_id, status, reasons):
        row = self.rows[verification_id]
        row["status"] = status
        data = dict(row.get("verification_data") or {})
        data["evaluation_reasons"] = list(reasons)
        row["verification_data"] = data
        return row


@pytest.fixture
def service():
    return VerificationService(store=FakeStore())


# ---------------------------------------------------------------------------
# Requirements catalog
# ---------------------------------------------------------------------------
def test_all_user_types_have_requirements():
    for ut in USER_TYPES:
        spec = get_requirements(ut)
        assert spec["user_type"] == ut
        assert spec["fields"], f"{ut} has no fields"
        for f in spec["fields"]:
            assert {"name", "label", "type", "required", "help"} <= set(f.keys())


def test_unknown_user_type_rejected():
    with pytest.raises(ValueError):
        get_requirements("astronaut")


def test_salary_and_revenue_never_required():
    prof_fields = {f["name"]: f for f in get_requirements("professional")["fields"]}
    assert prof_fields["salary_range"]["required"] is False
    biz_fields = {f["name"]: f for f in get_requirements("business")["fields"]}
    assert biz_fields["revenue_range"]["required"] is False
    for ut in USER_TYPES:
        for f in get_requirements(ut)["fields"]:
            if f["type"] == "file":
                assert f["required"] is False, f"{ut}.{f['name']} file must be optional"


# ---------------------------------------------------------------------------
# Submission validation
# ---------------------------------------------------------------------------
def test_valid_school_submission():
    errors = validate_submission("school", {
        "class_grade": "10", "board": "CBSE", "last_marks_pct": 87,
    })
    assert errors == []


def test_missing_required_field_reported():
    errors = validate_submission("school", {"class_grade": "10"})
    assert any("Board" in e for e in errors)
    assert any("marks" in e.lower() for e in errors)


def test_number_type_enforced():
    errors = validate_submission("college", {
        "degree": "B.Tech", "branch": "CS", "current_semester": "third",
        "latest_sgpa": 8.2,
    })
    assert any("semester" in e.lower() for e in errors)


def test_select_options_enforced():
    errors = validate_submission("lifelong", {
        "areas_of_interest": "photography", "self_assessed_level": "guru",
    })
    assert len(errors) == 1


# ---------------------------------------------------------------------------
# Deterministic evaluation (no AI, only submitted values)
# ---------------------------------------------------------------------------
def test_school_verified_within_range():
    status, reasons = evaluate_checks("school", {
        "class_grade": "10", "board": "CBSE", "last_marks_pct": 87,
    })
    assert status == "VERIFIED"


def test_school_rejected_impossible_marks():
    status, reasons = evaluate_checks("school", {
        "class_grade": "10", "board": "CBSE", "last_marks_pct": 150,
    })
    assert status == "REJECTED"
    assert any("impossible" in r for r in reasons)


def test_school_review_exact_100():
    status, reasons = evaluate_checks("school", {
        "class_grade": "10", "board": "CBSE", "last_marks_pct": 100,
    })
    assert status == "NEEDS_REVIEW"


def test_college_semester_bounds():
    ok, _ = evaluate_checks("college", {
        "degree": "B.Tech", "branch": "CS", "current_semester": 4, "latest_sgpa": 8.2,
    })
    assert ok == "VERIFIED"
    bad, reasons = evaluate_checks("college", {
        "degree": "B.Tech", "branch": "CS", "current_semester": 0, "latest_sgpa": 8.2,
    })
    assert bad == "REJECTED"
    weird, _ = evaluate_checks("college", {
        "degree": "B.Tech", "branch": "CS", "current_semester": 10, "latest_sgpa": 8.2,
    })
    assert weird == "NEEDS_REVIEW"


def test_college_gpa_bounds():
    status, reasons = evaluate_checks("college", {
        "degree": "B.Tech", "branch": "CS", "current_semester": 4, "latest_sgpa": 11,
    })
    assert status == "REJECTED"


def test_professional_experience_bounds():
    ok, _ = evaluate_checks("professional", {
        "current_role": "Dev", "years_experience": 3,
    })
    assert ok == "VERIFIED"
    bad, _ = evaluate_checks("professional", {
        "current_role": "Dev", "years_experience": -2,
    })
    assert bad == "REJECTED"


def test_switcher_identical_fields_flagged():
    status, reasons = evaluate_checks("switcher", {
        "current_field": "accounting", "target_field": "Accounting",
        "relevant_experience": "none yet",
    })
    assert status == "NEEDS_REVIEW"


def test_lifelong_verified():
    status, _ = evaluate_checks("lifelong", {
        "areas_of_interest": "photography", "self_assessed_level": "Complete beginner",
    })
    assert status == "VERIFIED"


# ---------------------------------------------------------------------------
# Service orchestration
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_submit_auto_evaluates_to_verified(service):
    record = await service.submit_verification(
        "person-1", "school",
        {"class_grade": "10", "board": "CBSE", "last_marks_pct": 87},
    )
    assert record["status"] == "VERIFIED"
    assert record["user_type"] == "school"
    assert record["person_id"] == "person-1"


@pytest.mark.asyncio
async def test_submit_invalid_raises_before_store(service):
    with pytest.raises(ValueError):
        await service.submit_verification("person-2", "school", {"class_grade": "10"})
    assert await service.get_status("person-2") is None


@pytest.mark.asyncio
async def test_submit_unknown_type_rejected(service):
    with pytest.raises(ValueError):
        await service.submit_verification("person-3", "astronaut", {})


@pytest.mark.asyncio
async def test_submit_rejected_on_impossible_values(service):
    record = await service.submit_verification(
        "person-4", "professional",
        {"current_role": "Dev", "years_experience": -5},
    )
    assert record["status"] == "REJECTED"
    reasons = record["verification_data"]["evaluation_reasons"]
    assert any("negative" in r.lower() for r in reasons)


@pytest.mark.asyncio
async def test_status_returns_current_record(service):
    await service.submit_verification(
        "person-5", "lifelong",
        {"areas_of_interest": "baking", "self_assessed_level": "Some exposure"},
    )
    status = await service.get_status("person-5")
    assert status["status"] == "VERIFIED"


@pytest.mark.asyncio
async def test_status_none_when_never_submitted(service):
    assert await service.get_status("nobody") is None


@pytest.mark.asyncio
async def test_evaluate_unknown_id_raises(service):
    with pytest.raises(ValueError):
        await service.evaluate_verification("nope")
