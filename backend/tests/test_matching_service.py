import json
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from app.schemas.match import JobMatchResult
from app.services.matching_service import JobMatchValidationError, MatchingService


VALID_RESULT = {
    "job_id": "job-123",
    "match_score": 92,
    "matched_skills": ["python", "fastapi", "sql"],
    "missing_skills": ["kubernetes"],
    "reason": "Strong overlap with the role requirements and one gap to close.",
}


def _mocked_response(payload: dict) -> Mock:
    result = Mock()
    result.text = json.dumps(payload)
    return result


def test_valid_response() -> None:
    mock_client = Mock()
    mock_client.models.generate_content.return_value = _mocked_response(VALID_RESULT)

    with patch("app.services.matching_service.genai.Client", return_value=mock_client):
        service = MatchingService()
        result = service.match_job(
            candidate_skills=["python", "fastapi", "sql"],
            job_description="Senior Python engineer with FastAPI and SQL experience; Kubernetes is a plus.",
            job_id="job-123",
        )

    assert result == JobMatchResult(**VALID_RESULT)


def test_invalid_score() -> None:
    with pytest.raises(ValidationError):
        JobMatchResult.model_validate(
            {
                "job_id": "job-123",
                "match_score": 150,
                "matched_skills": ["python"],
                "missing_skills": [],
                "reason": "Invalid score should fail validation.",
            }
        )


def test_missing_required_field() -> None:
    with pytest.raises(ValidationError):
        JobMatchResult.model_validate(
            {
                "match_score": 80,
                "matched_skills": ["python"],
                "missing_skills": [],
                "reason": "Missing job_id should fail validation.",
            }
        )


def test_first_attempt_invalid_second_attempt_valid() -> None:
    mock_client = Mock()
    mock_client.models.generate_content.side_effect = [
        _mocked_response({"job_id": "job-123", "match_score": 130, "matched_skills": ["python"], "missing_skills": [], "reason": "bad"}),
        _mocked_response(VALID_RESULT),
    ]

    with patch("app.services.matching_service.genai.Client", return_value=mock_client):
        service = MatchingService()
        result = service.match_job(
            candidate_skills=["python", "fastapi"],
            job_description="Python backend role using FastAPI",
            job_id="job-123",
        )

    assert result == JobMatchResult(**VALID_RESULT)
    assert mock_client.models.generate_content.call_count == 2


def test_both_attempts_invalid() -> None:
    mock_client = Mock()
    mock_client.models.generate_content.side_effect = [
        _mocked_response({"job_id": "job-123", "match_score": 120, "matched_skills": ["python"], "missing_skills": [], "reason": "bad"}),
        _mocked_response({"job_id": "job-123", "match_score": 1000, "matched_skills": ["python"], "missing_skills": [], "reason": "bad"}),
    ]

    with patch("app.services.matching_service.genai.Client", return_value=mock_client):
        service = MatchingService()

        with pytest.raises(JobMatchValidationError, match="Validation failed on both attempts"):
            service.match_job(
                candidate_skills=["python"],
                job_description="Python developer role",
                job_id="job-123",
            )

    assert mock_client.models.generate_content.call_count == 2
