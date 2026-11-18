import json
from typing import Any

from google import genai
from pydantic import ValidationError

from app.config import settings
from app.schemas.match import JobMatchResult


class JobMatchValidationError(ValueError):
    """Raised when Gemini structured output cannot be validated."""


class MatchingService:
    def __init__(self) -> None:
        self.client = genai.Client(api_key=settings.gemini_api_key) if settings.gemini_api_key else genai.Client(api_key="test-api-key")

    def _build_prompt(self, candidate_skills: list[str], job_description: str, job_id: str, validation_error: str | None = None) -> str:
        instructions = (
            "You are a job-matching assistant. Return valid JSON only. "
            "Use this exact schema: {\n"
            '  "job_id": "string",\n'
            '  "match_score": 0-100 integer,\n'
            '  "matched_skills": ["string"],\n'
            '  "missing_skills": ["string"],\n'
            '  "reason": "string"\n'
            "}\n"
            "Do not include markdown fences or extra fields."
        )

        if validation_error:
            instructions += f"\nCorrect the previous invalid JSON using this validation error: {validation_error}"

        return (
            f"{instructions}\n\n"
            f"Candidate skills: {candidate_skills}\n"
            f"Job ID: {job_id}\n"
            f"Job description: {job_description}"
        )

    def _parse_payload(self, raw_text: str) -> dict[str, Any]:
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise JobMatchValidationError(f"Gemini response was not valid JSON: {exc}") from exc

        if not isinstance(parsed, dict):
            raise JobMatchValidationError("Gemini response was not a JSON object.")

        return parsed

    def _validate_result(self, payload: dict[str, Any]) -> JobMatchResult:
        try:
            return JobMatchResult.model_validate(payload)
        except ValidationError as exc:
            raise JobMatchValidationError(f"Validation failed: {exc}") from exc

    def match_job(self, candidate_skills: list[str], job_description: str, job_id: str) -> JobMatchResult:
        attempts = 2
        validation_error: str | None = None

        for attempt in range(attempts):
            prompt = self._build_prompt(candidate_skills, job_description, job_id, validation_error)
            response = self.client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
            )

            try:
                payload = self._parse_payload(response.text)
                result = self._validate_result(payload)
                return result
            except JobMatchValidationError as exc:
                if attempt == 1:
                    raise JobMatchValidationError(f"Validation failed on both attempts: {exc}") from exc
                validation_error = str(exc)

        raise JobMatchValidationError("Validation failed on both attempts without a usable response.")
