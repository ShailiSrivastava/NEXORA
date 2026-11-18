from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field, ValidationError

from app.services.matching_service import MatchingService


class JobRepository(Protocol):
    def search_jobs(self, query: str) -> list[dict[str, Any]]:
        ...

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        ...


class SearchJobsArgs(BaseModel):
    query: str = Field(..., min_length=1)


class ExplainMatchArgs(BaseModel):
    job_id: str = Field(..., min_length=1)


class GetCandidateSkillsArgs(BaseModel):
    pass


class CandidateProfileStore:
    def __init__(self) -> None:
        self._profiles: dict[str, dict[str, Any]] = {}

    def get_profile(self, session_id: str) -> dict[str, Any]:
        return self._profiles.setdefault(session_id, {"skills": []})

    def set_profile(self, session_id: str, *, skills: list[str] | None = None, preferences: dict[str, Any] | None = None) -> dict[str, Any]:
        profile = self._profiles.setdefault(session_id, {"skills": [], "preferences": {}})
        if skills is not None:
            profile["skills"] = [skill.strip() for skill in skills if skill and skill.strip()]
        if preferences is not None:
            profile["preferences"] = preferences
        return profile

    def get_candidate_skills(self, session_id: str) -> list[str]:
        profile = self.get_profile(session_id)
        return list(profile.get("skills", []))


class InMemoryJobRepository:
    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {
            "job-101": {
                "job_id": "job-101",
                "title": "Senior Python Engineer",
                "company": "Northstar AI",
                "description": "Build backend APIs with Python, FastAPI, SQL, and cloud deployment experience.",
                "required_skills": ["python", "fastapi", "sql", "aws"],
            },
            "job-202": {
                "job_id": "job-202",
                "title": "Staff Data Analyst",
                "company": "Helio Labs",
                "description": "Analyze product metrics and prepare dashboards with Python, SQL, and stakeholder communication.",
                "required_skills": ["python", "sql", "analytics"],
            },
            "job-303": {
                "job_id": "job-303",
                "title": "Frontend Engineer",
                "company": "Velo Graph",
                "description": "Ship performant web features using TypeScript, React, and component-driven design systems.",
                "required_skills": ["typescript", "react", "ui"],
            },
        }

    def search_jobs(self, query: str) -> list[dict[str, Any]]:
        q = query.lower().strip()
        if not q:
            return []

        matches: list[dict[str, Any]] = []
        for job in self._jobs.values():
            haystack = " ".join(
                [
                    job.get("title", ""),
                    job.get("company", ""),
                    job.get("description", ""),
                    *job.get("required_skills", []),
                ]
            ).lower()
            if q in haystack:
                matches.append({
                    "job_id": job["job_id"],
                    "title": job["title"],
                    "company": job["company"],
                    "description": job["description"],
                })
        return matches

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        return self._jobs.get(job_id)


def search_jobs(query: str, *, repository: JobRepository | None = None) -> list[dict[str, Any]]:
    repo = repository or InMemoryJobRepository()
    validated = SearchJobsArgs.model_validate({"query": query})
    return repo.search_jobs(validated.query)


def get_candidate_skills(session_id: str, *, profile_store: CandidateProfileStore | None = None) -> list[str]:
    if not session_id:
        return []
    store = profile_store or CandidateProfileStore()
    return store.get_candidate_skills(session_id)


def explain_match(job_id: str, *, session_id: str, profile_store: CandidateProfileStore | None = None, repository: JobRepository | None = None, matching_service: MatchingService | None = None) -> dict[str, Any]:
    validated = ExplainMatchArgs.model_validate({"job_id": job_id})
    repo = repository or InMemoryJobRepository()
    profile_store = profile_store or CandidateProfileStore()
    job = repo.get_job(validated.job_id)
    if job is None:
        return {
            "job_id": validated.job_id,
            "match_score": 0,
            "matched_skills": [],
            "missing_skills": [],
            "reason": "Job not found in the repository.",
        }

    candidate_skills = profile_store.get_candidate_skills(session_id)
    service = matching_service or MatchingService()
    result = service.match_job(
        candidate_skills=candidate_skills,
        job_description=f"{job['title']} at {job['company']}: {job['description']}",
        job_id=validated.job_id,
    )
    return result.model_dump()


def validate_tool_arguments(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    validators = {
        "search_jobs": SearchJobsArgs,
        "get_candidate_skills": GetCandidateSkillsArgs,
        "explain_match": ExplainMatchArgs,
    }

    validator = validators.get(tool_name)
    if validator is None:
        raise ValueError(f"Unknown tool: {tool_name}")

    try:
        model = validator.model_validate(arguments or {})
    except ValidationError as exc:  # pragma: no cover - exercised through agent route tests
        raise ValueError(f"Invalid arguments for {tool_name}: {exc}") from exc

    return model.model_dump()
