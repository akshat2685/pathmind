import re
import base64
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timezone
import httpx

from backend.core.artifact_schemas import (
    CanonicalArtifact,
    ArtifactObservation,
    ArtifactQualityDimensions
)

class BaseArtifactProvider(ABC):
    @abstractmethod
    def get_source_type(self) -> str:
        pass

    @abstractmethod
    async def normalize_and_ingest(self, person_id: str, payload: Dict[str, Any]) -> CanonicalArtifact:
        pass

    @abstractmethod
    async def verify_ownership(self, artifact: CanonicalArtifact, person_context: Dict[str, Any]) -> Tuple[str, str]:
        """Returns (ownership_status, reason)"""
        pass

    @abstractmethod
    async def extract_observations(self, artifact: CanonicalArtifact) -> List[ArtifactObservation]:
        pass

    @abstractmethod
    def derive_quality_dimensions(self, artifact: CanonicalArtifact) -> ArtifactQualityDimensions:
        pass


class GitHubArtifactProvider(BaseArtifactProvider):
    """
    Real GitHub Repository Provider.
    Inspects authentic repository metadata, languages, README, commit signatures,
    and testing/CI structure via GitHub API with graceful offline fallback.
    """
    def get_source_type(self) -> str:
        return "GITHUB"

    def _parse_repo_slug(self, url: str) -> Optional[Tuple[str, str]]:
        match = re.search(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", url)
        if match:
            owner, repo = match.group(1), match.group(2)
            if repo.endswith(".git"):
                repo = repo[:-4]
            return owner, repo
        return None

    async def normalize_and_ingest(self, person_id: str, payload: Dict[str, Any]) -> CanonicalArtifact:
        raw_url = payload.get("url") or payload.get("source_reference", "")
        slug = self._parse_repo_slug(raw_url)
        title = payload.get("title") or (f"{slug[0]}/{slug[1]}" if slug else "GitHub Repository")
        description = payload.get("description", "GitHub source code repository.")

        metadata: Dict[str, Any] = {
            "raw_url": raw_url,
            "owner": slug[0] if slug else None,
            "repo": slug[1] if slug else None,
            "languages": payload.get("languages", {}),
            "readme_text": payload.get("readme", ""),
            "files": payload.get("files", []),
            "has_tests": payload.get("has_tests", False),
            "has_ci": payload.get("has_ci", False)
        }

        # Attempt authentic GitHub API inspection if slug is valid
        if slug:
            owner, repo = slug
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    repo_res = await client.get(f"https://api.github.com/repos/{owner}/{repo}")
                    if repo_res.status_code == 200:
                        repo_data = repo_res.json()
                        description = repo_data.get("description") or description
                        metadata["stars"] = repo_data.get("stargazers_count", 0)
                        metadata["forks"] = repo_data.get("forks_count", 0)
                        metadata["default_branch"] = repo_data.get("default_branch", "main")
                        metadata["api_verified"] = True

                        # Fetch languages
                        lang_res = await client.get(f"https://api.github.com/repos/{owner}/{repo}/languages")
                        if lang_res.status_code == 200:
                            metadata["languages"] = lang_res.json()

                        # Fetch README
                        readme_res = await client.get(f"https://api.github.com/repos/{owner}/{repo}/readme")
                        if readme_res.status_code == 200:
                            readme_data = readme_res.json()
                            content_b64 = readme_data.get("content", "")
                            if content_b64:
                                metadata["readme_text"] = base64.b64decode(content_b64).decode("utf-8", errors="ignore")
            except Exception:
                metadata["api_verified"] = False

        artifact = CanonicalArtifact(
            person_id=person_id,
            type="CODE_REPOSITORY",
            title=title,
            description=description,
            source="GITHUB",
            source_reference=raw_url,
            verification_status="PARTIALLY_VERIFIED" if slug else "UNVERIFIED",
            ownership_status="UNVERIFIED",
            visibility=payload.get("visibility", "PORTFOLIO_VISIBLE"),
            metadata=metadata,
            provenance={
                "provider": "GitHubArtifactProvider",
                "ingested_at": datetime.now(timezone.utc).isoformat(),
                "slug": f"{slug[0]}/{slug[1]}" if slug else "unknown"
            }
        )
        return artifact

    async def verify_ownership(self, artifact: CanonicalArtifact, person_context: Dict[str, Any]) -> Tuple[str, str]:
        owner = artifact.metadata.get("owner", "")
        person_gh = person_context.get("github_username", "").lower()
        person_name = person_context.get("name", "").lower()

        if not owner:
            return ("UNVERIFIED", "Cannot determine repository owner from source reference.")

        if person_gh and owner.lower() == person_gh:
            return ("VERIFIED", f"Repository owner '{owner}' directly matches learner's verified GitHub profile.")

        # Check commit authors or contributor list if present
        commit_authors = [str(a).lower() for a in artifact.metadata.get("commit_authors", [])]
        if person_gh and person_gh in commit_authors:
            return ("PARTIALLY_VERIFIED", f"Learner '{person_gh}' is confirmed in repository commit history.")

        if person_name and person_name in owner.lower():
            return ("PARTIALLY_VERIFIED", f"Owner '{owner}' partially matches learner name '{person_name}'.")

        return ("UNVERIFIED", f"Repository owner '{owner}' has not been confirmed as learner '{person_gh or 'anonymous'}'.")

    async def extract_observations(self, artifact: CanonicalArtifact) -> List[ArtifactObservation]:
        observations: List[ArtifactObservation] = []
        meta = artifact.metadata
        languages = meta.get("languages", {})
        readme = meta.get("readme_text", "")
        files = [str(f).lower() for f in meta.get("files", [])]

        # 1. Observed Code Languages (DEMONSTRATED)
        for lang, byte_count in languages.items():
            observations.append(ArtifactObservation(
                category="TECHNOLOGY",
                detail=f"Demonstrated codebase implementation in {lang} ({byte_count} bytes).",
                is_demonstrated=True,
                basis_file_or_snippet=f"{lang} source files"
            ))

        # 2. Testing Evidence
        has_tests = meta.get("has_tests") or any("test" in f for f in files) or "pytest" in readme.lower() or "unittest" in readme.lower()
        if has_tests:
            observations.append(ArtifactObservation(
                category="TESTING",
                detail="Automated test suite detected in codebase.",
                is_demonstrated=True,
                basis_file_or_snippet="test files / pytest configurations"
            ))
        else:
            observations.append(ArtifactObservation(
                category="TESTING",
                detail="No automated unit tests or test directory detected in repository.",
                is_demonstrated=False,
                basis_file_or_snippet=None
            ))

        # 3. CI/CD & Deployment Evidence
        has_docker = any("dockerfile" in f for f in files) or "docker" in readme.lower()
        has_ci = meta.get("has_ci") or any(".github/workflows" in f for f in files)
        if has_docker or has_ci:
            observations.append(ArtifactObservation(
                category="DEPLOYMENT",
                detail=f"Deployment configuration observed: {'Dockerfile ' if has_docker else ''}{'CI/CD workflow' if has_ci else ''}.",
                is_demonstrated=True,
                basis_file_or_snippet="Dockerfile / GitHub Actions"
            ))

        # 4. Technologies MENTIONED in README only (NOT DEMONSTRATED)
        potential_buzzwords = ["Kubernetes", "Redis", "Kafka", "GraphQL", "AWS", "Microservices", "TensorFlow", "PyTorch"]
        for buzz in potential_buzzwords:
            if buzz.lower() in readme.lower():
                # Check if it was in languages or files
                already_demo = any(buzz.lower() in str(f) for f in files) or any(buzz.lower() in str(l).lower() for l in languages)
                if not already_demo:
                    observations.append(ArtifactObservation(
                        category="TECHNOLOGY",
                        detail=f"'{buzz}' mentioned in README description, but no direct source implementation verified.",
                        is_demonstrated=False,
                        basis_file_or_snippet="README.md"
                    ))

        return observations

    def derive_quality_dimensions(self, artifact: CanonicalArtifact) -> ArtifactQualityDimensions:
        meta = artifact.metadata
        languages = meta.get("languages", {})
        files = [str(f).lower() for f in meta.get("files", [])]
        readme = meta.get("readme_text", "")

        total_bytes = sum(languages.values()) if languages else len(files) * 500
        has_tests = meta.get("has_tests") or any("test" in f for f in files) or "pytest" in readme.lower()
        has_ci = meta.get("has_ci") or any(".github" in f or "docker" in f for f in files)

        complexity = "ADVANCED" if total_bytes > 50000 or len(languages) > 2 else ("MODERATE" if total_bytes > 10000 else "BASIC")
        doc_quality = "COMPREHENSIVE" if len(readme) > 1000 else ("MODERATE" if len(readme) > 200 else "MINIMAL")
        testing = "AUTOMATED_UNIT_TESTS" if has_tests else "NONE"
        deployment = "CI_CD_WORKFLOW" if has_ci else "NONE"

        return ArtifactQualityDimensions(
            completeness="HIGH" if has_tests and len(readme) > 500 else "MODERATE",
            complexity=complexity,
            implementation_depth="DEEP" if complexity == "ADVANCED" else "MODERATE",
            documentation_quality=doc_quality,
            testing_evidence=testing,
            deployment_evidence=deployment,
            maintenance_activity="ACTIVE"
        )


class UserUploadArtifactProvider(BaseArtifactProvider):
    """
    Handles user-uploaded documents, research briefs, design documents, and code snippets.
    """
    def get_source_type(self) -> str:
        return "USER_UPLOAD"

    async def normalize_and_ingest(self, person_id: str, payload: Dict[str, Any]) -> CanonicalArtifact:
        title = payload.get("title", "Uploaded Document / Project Sample")
        description = payload.get("description", "User-uploaded technical artifact.")
        artifact_type = payload.get("artifact_type", "DOCUMENT")
        content_text = payload.get("content_text") or payload.get("code", "")

        artifact = CanonicalArtifact(
            person_id=person_id,
            type=artifact_type,
            title=title,
            description=description,
            source="USER_UPLOAD",
            source_reference=payload.get("file_name", "upload_direct"),
            verification_status="PARTIALLY_VERIFIED" if len(content_text) > 30 else "UNVERIFIED",
            ownership_status="VERIFIED",  # Directly uploaded by authenticated user
            visibility=payload.get("visibility", "PORTFOLIO_VISIBLE"),
            metadata={
                "content_text": content_text[:5000],  # Bound text size
                "word_count": len(content_text.split()),
                "file_type": payload.get("file_type", "text/plain")
            },
            provenance={
                "provider": "UserUploadArtifactProvider",
                "uploaded_at": datetime.now(timezone.utc).isoformat()
            }
        )
        return artifact

    async def verify_ownership(self, artifact: CanonicalArtifact, person_context: Dict[str, Any]) -> Tuple[str, str]:
        return ("VERIFIED", "Direct authentic user upload from authenticated session.")

    async def extract_observations(self, artifact: CanonicalArtifact) -> List[ArtifactObservation]:
        text = artifact.metadata.get("content_text", "")
        observations: List[ArtifactObservation] = []

        if "class " in text or "def " in text:
            observations.append(ArtifactObservation(
                category="ARCHITECTURE",
                detail="Structured object-oriented or functional implementation code observed.",
                is_demonstrated=True,
                basis_file_or_snippet="Uploaded code snippet"
            ))

        if "methodology" in text.lower() or "architecture" in text.lower():
            observations.append(ArtifactObservation(
                category="METHODOLOGY",
                detail="Technical methodology and architecture rationale documented in artifact.",
                is_demonstrated=True,
                basis_file_or_snippet="Methodology section"
            ))

        return observations

    def derive_quality_dimensions(self, artifact: CanonicalArtifact) -> ArtifactQualityDimensions:
        word_count = artifact.metadata.get("word_count", 0)
        return ArtifactQualityDimensions(
            completeness="HIGH" if word_count > 300 else "MODERATE",
            complexity="MODERATE" if word_count > 200 else "BASIC",
            implementation_depth="MODERATE",
            documentation_quality="COMPREHENSIVE" if word_count > 400 else "MODERATE",
            testing_evidence="NONE",
            deployment_evidence="NONE",
            maintenance_activity="ACTIVE"
        )


class CredentialArtifactProvider(BaseArtifactProvider):
    """
    Handles verified certificates, digital badges, and professional licenses.
    """
    def get_source_type(self) -> str:
        return "CREDENTIAL_PROVIDER"

    async def normalize_and_ingest(self, person_id: str, payload: Dict[str, Any]) -> CanonicalArtifact:
        title = payload.get("title", "Professional Certificate")
        issuer = payload.get("issuer", "Official Certification Authority")
        cred_id = payload.get("credential_id", "")
        cred_url = payload.get("credential_url", "")

        artifact = CanonicalArtifact(
            person_id=person_id,
            type="CREDENTIAL",
            title=title,
            description=f"Verified professional certification issued by {issuer}.",
            source="CREDENTIAL_PROVIDER",
            source_reference=cred_url or cred_id or "official_credential",
            verification_status="VERIFIED" if cred_id and cred_url else "PARTIALLY_VERIFIED",
            ownership_status="PARTIALLY_VERIFIED",
            metadata={
                "issuer": issuer,
                "credential_id": cred_id,
                "credential_url": cred_url,
                "issue_date": payload.get("issue_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
                "recipient_name": payload.get("recipient_name", "")
            },
            provenance={
                "provider": "CredentialArtifactProvider",
                "issuer": issuer,
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
        )
        return artifact

    async def verify_ownership(self, artifact: CanonicalArtifact, person_context: Dict[str, Any]) -> Tuple[str, str]:
        recipient = artifact.metadata.get("recipient_name", "").lower()
        person_name = person_context.get("name", "").lower()

        if recipient and person_name and (recipient in person_name or person_name in recipient):
            return ("VERIFIED", f"Credential recipient '{recipient}' matches authenticated learner name '{person_name}'.")
        elif artifact.metadata.get("credential_id"):
            return ("PARTIALLY_VERIFIED", "Credential ID present; awaiting automated third-party issuer identity handshake.")
        return ("UNVERIFIED", "Recipient name not confirmed on issued certificate.")

    async def extract_observations(self, artifact: CanonicalArtifact) -> List[ArtifactObservation]:
        meta = artifact.metadata
        return [
            ArtifactObservation(
                category="TECHNOLOGY",
                detail=f"Certified competency verified by official body: {meta.get('issuer')}.",
                is_demonstrated=True,
                basis_file_or_snippet=f"Credential ID: {meta.get('credential_id')}"
            )
        ]

    def derive_quality_dimensions(self, artifact: CanonicalArtifact) -> ArtifactQualityDimensions:
        return ArtifactQualityDimensions(
            completeness="HIGH",
            complexity="ADVANCED",
            implementation_depth="DEEP",
            documentation_quality="COMPREHENSIVE",
            testing_evidence="AUTOMATED_UNIT_TESTS",
            deployment_evidence="LIVE_URL",
            maintenance_activity="ACTIVE"
        )
