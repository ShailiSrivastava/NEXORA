from __future__ import annotations

from typing import Any


class PersonalizationService:
    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = {
            "matched_skills": 0.5,
            "experience": 0.2,
            "remote": 0.15,
            "location": 0.1,
            "role": 0.05,
            **(weights or {}),
        }

    def compute_personalized_score(self, candidate_profile: dict[str, Any], job: dict[str, Any]) -> float:
        score = 0.0
        candidate_skills = set((candidate_profile.get("skills") or []))
        job_skills = set((job.get("required_skills") or []))
        matched = len(candidate_skills & job_skills)
        score += matched * self.weights["matched_skills"]

        experience = candidate_profile.get("experience_level") or ""
        if experience and job.get("experience_level") and experience.lower() in str(job.get("experience_level", "")).lower():
            score += self.weights["experience"]

        pref_remote = bool(candidate_profile.get("preferences", {}).get("remote"))
        if pref_remote and bool(job.get("remote")):
            score += self.weights["remote"]

        candidate_location = str(candidate_profile.get("location") or "").lower()
        job_location = str(job.get("location") or "").lower()
        if candidate_location and job_location and candidate_location == job_location:
            score += self.weights["location"]

        preferred_role = str(candidate_profile.get("preferred_role") or "").lower()
        job_role = str(job.get("role") or "").lower()
        if preferred_role and job_role and preferred_role in job_role:
            score += self.weights["role"]

        return round(score, 4)

    def personalize(self, candidate_profile: dict[str, Any], jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        personalized: list[dict[str, Any]] = []
        for job in jobs:
            personal_boost = self.compute_personalized_score(candidate_profile, job)
            job_copy = dict(job)
            job_copy["personalization_boost"] = personal_boost
            job_copy["final_score"] = float(job.get("rerank_score", job.get("score", 0.0))) + personal_boost
            job_copy["explanation"] = self._build_explanation(candidate_profile, job, personal_boost)
            personalized.append(job_copy)
        return sorted(personalized, key=lambda item: float(item["final_score"]), reverse=True)

    @staticmethod
    def _build_explanation(candidate_profile: dict[str, Any], job: dict[str, Any], boost: float) -> str:
        reasons: list[str] = []
        candidate_skills = set((candidate_profile.get("skills") or []))
        matched = sorted(candidate_skills & set(job.get("required_skills", [])))
        if matched:
            reasons.append(f"matched skills: {', '.join(matched)}")
        if candidate_profile.get("preferences", {}).get("remote") and job.get("remote"):
            reasons.append("remote preference matches")
        if str(candidate_profile.get("location") or "").lower() == str(job.get("location") or "").lower():
            reasons.append("location matches")
        if boost <= 0:
            return "No personalization boost applied; profile does not align strongly with this role."
        return f"Personalization boost applied because: {', '.join(reasons) if reasons else 'profile aligns with the role'}"
