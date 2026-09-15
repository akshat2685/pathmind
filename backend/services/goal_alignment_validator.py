"""
GoalAlignmentValidator — Fail-Closed Domain Alignment Guard.

Ensures that every downstream output (assessment, path, roadmap, readiness report)
is aligned to the user's canonical goal. If ANY output contains a mismatched domain
or goal_id, the validator raises GOAL_ALIGNMENT_ERROR.

No downstream component may silently replace the user's declared goal.
"""
from typing import Dict, Any, List, Optional


# Software/tech keywords that should NOT appear in non-tech goal outputs
_TECH_CONTAMINATION_KEYWORDS = [
    "python", "javascript", "typescript", "react", "github", "git",
    "machine learning", "artificial intelligence", "deep learning",
    "neural network", "tensorflow", "pytorch", "kubernetes", "docker",
    "microservices", "api", "sql", "database indexing", "software engineer",
    "data engineer", "ml engineer", "ai engineer", "fullstack", "backend",
    "frontend", "devops", "cloud computing", "aws", "gcp", "azure",
    "leetcode", "data structures", "algorithms", "monolith",
    "applied ai", "robotics", "compiler", "codebase"
]


class GoalAlignmentError(Exception):
    """Raised when downstream output does not match the canonical goal."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


class GoalAlignmentValidator:
    """
    Validates that generated outputs (assessments, paths, roadmaps) are semantically
    aligned with the user's canonical goal.

    Two validation modes:
    1. Structural: goal_id and domain must match.
    2. Semantic: content must not contain cross-domain contamination keywords.
    """

    @staticmethod
    def validate_goal_id_match(
        canonical_goal_id: str,
        output_goal_id: str,
        output_type: str = "output"
    ) -> None:
        """Validate that the output references the correct goal_id."""
        if canonical_goal_id != output_goal_id:
            raise GoalAlignmentError(
                f"GOAL_ALIGNMENT_ERROR: {output_type} references goal_id='{output_goal_id}' "
                f"but canonical goal is '{canonical_goal_id}'.",
                details={
                    "expected_goal_id": canonical_goal_id,
                    "actual_goal_id": output_goal_id,
                    "output_type": output_type
                }
            )

    @staticmethod
    def validate_domain_match(
        canonical_domain: str,
        output_domain: str,
        output_type: str = "output"
    ) -> None:
        """Validate that the output domain matches the canonical goal domain."""
        if canonical_domain.lower().strip() != output_domain.lower().strip():
            raise GoalAlignmentError(
                f"GOAL_ALIGNMENT_ERROR: {output_type} has domain='{output_domain}' "
                f"but canonical goal domain is '{canonical_domain}'.",
                details={
                    "expected_domain": canonical_domain,
                    "actual_domain": output_domain,
                    "output_type": output_type
                }
            )

    @staticmethod
    def validate_no_cross_domain_contamination(
        canonical_domain: str,
        content_to_check: str,
        output_type: str = "output"
    ) -> List[str]:
        """
        Semantic validation: checks that the content does not contain tech/software
        keywords when the canonical goal domain is NOT technology-related.

        Returns a list of contamination keywords found (empty if clean).
        """
        # If the domain IS technology, no contamination check needed
        tech_domains = [
            "technology", "software", "engineering", "computer science",
            "artificial intelligence", "data science", "it", "information technology"
        ]
        domain_lower = canonical_domain.lower().strip()
        if any(td in domain_lower for td in tech_domains):
            return []

        # Check for tech contamination in non-tech domains
        content_lower = content_to_check.lower()
        found = []
        for keyword in _TECH_CONTAMINATION_KEYWORDS:
            if keyword in content_lower:
                found.append(keyword)

        return found

    @staticmethod
    def validate_output(
        canonical_goal: Dict[str, Any],
        output_data: Dict[str, Any],
        output_type: str = "output",
        strict: bool = True
    ) -> Dict[str, Any]:
        """
        Full validation pipeline:
        1. Check goal_id match (if present in output)
        2. Check domain match (if present in output)
        3. Semantic contamination check on serialized content

        Returns a validation report dict.
        """
        report = {
            "output_type": output_type,
            "goal_id_match": True,
            "domain_match": True,
            "contamination_keywords": [],
            "passed": True,
            "errors": []
        }

        canonical_goal_id = canonical_goal.get("id", "")
        canonical_domain = canonical_goal.get("domain", "")

        # 1. Goal ID check
        output_goal_id = output_data.get("goal_id", output_data.get("id", ""))
        if output_goal_id and canonical_goal_id and output_goal_id != canonical_goal_id:
            report["goal_id_match"] = False
            report["passed"] = False
            report["errors"].append(
                f"goal_id mismatch: expected '{canonical_goal_id}', got '{output_goal_id}'"
            )

        # 2. Domain check
        output_domain = output_data.get("domain", output_data.get("target_industry", ""))
        if output_domain and canonical_domain:
            if output_domain.lower().strip() != canonical_domain.lower().strip():
                report["domain_match"] = False
                report["passed"] = False
                report["errors"].append(
                    f"domain mismatch: expected '{canonical_domain}', got '{output_domain}'"
                )

        # 3. Semantic contamination
        import json
        content_str = json.dumps(output_data, default=str)
        contamination = GoalAlignmentValidator.validate_no_cross_domain_contamination(
            canonical_domain, content_str, output_type
        )
        if contamination:
            report["contamination_keywords"] = contamination
            report["passed"] = False
            report["errors"].append(
                f"Cross-domain contamination detected: {contamination}"
            )

        if strict and not report["passed"]:
            raise GoalAlignmentError(
                f"GOAL_ALIGNMENT_ERROR in {output_type}: {'; '.join(report['errors'])}",
                details=report
            )

        return report
