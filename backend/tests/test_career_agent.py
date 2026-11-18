from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.agents.career_agent import CareerAgent, ToolLoopError
from app.main import create_app
from app.schemas.match import JobMatchResult


def _function_call(name: str, **kwargs: object) -> SimpleNamespace:
    return SimpleNamespace(name=name, args=kwargs)


def _tools_response(*calls: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(function_calls=list(calls), text="")


def _text_response(text: str) -> SimpleNamespace:
    return SimpleNamespace(function_calls=[], text=text, candidates=[])


def test_search_jobs_execution() -> None:
    mock_client = Mock()
    mock_client.models.generate_content.side_effect = [
        _tools_response(_function_call("search_jobs", query="python")),
        _text_response("I found several Python roles."),
    ]

    with patch("app.agents.career_agent.genai.Client", return_value=mock_client):
        agent = CareerAgent(session_id="session-1")
        result = agent.chat("session-1", "Find python jobs")

    assert result["response"] == "I found several Python roles."
    assert result["trace"][0]["tool"] == "search_jobs"
    assert result["trace"][0]["result"]["results"][0]["title"] == "Senior Python Engineer"


def test_get_candidate_skills_execution() -> None:
    mock_client = Mock()
    mock_client.models.generate_content.side_effect = [
        _tools_response(_function_call("get_candidate_skills")),
        _text_response("Here are your skills."),
    ]

    with patch("app.agents.career_agent.genai.Client", return_value=mock_client):
        agent = CareerAgent(session_id="session-2")
        agent.profile_store.set_profile("session-2", skills=["python", "sql", "fastapi"])
        result = agent.chat("session-2", "What skills do I have?")

    assert result["trace"][0]["result"]["skills"] == ["python", "sql", "fastapi"]
    assert result["response"] == "Here are your skills."


def test_explain_match_execution() -> None:
    mock_client = Mock()
    mock_client.models.generate_content.side_effect = [
        _tools_response(_function_call("explain_match", job_id="job-101")),
        _text_response("Here is your match summary."),
    ]

    matching_service = Mock()
    matching_service.match_job.return_value = JobMatchResult(
        job_id="job-101",
        match_score=91,
        matched_skills=["python", "fastapi"],
        missing_skills=["aws"],
        reason="Strong fit for the role with one missing deployment skill.",
    )

    with patch("app.agents.career_agent.genai.Client", return_value=mock_client):
        agent = CareerAgent(session_id="session-3", matching_service=matching_service)
        agent.profile_store.set_profile("session-3", skills=["python", "fastapi", "sql"])
        result = agent.chat("session-3", "Explain job-101")

    assert result["trace"][0]["tool"] == "explain_match"
    assert result["trace"][0]["result"]["job_id"] == "job-101"
    assert result["trace"][0]["result"]["match_score"] == 91


def test_multi_tool_sequence() -> None:
    mock_client = Mock()
    mock_client.models.generate_content.side_effect = [
        _tools_response(
            _function_call("search_jobs", query="python"),
            _function_call("get_candidate_skills"),
        ),
        _text_response("Combined summary ready."),
    ]

    with patch("app.agents.career_agent.genai.Client", return_value=mock_client):
        agent = CareerAgent(session_id="session-4")
        agent.profile_store.set_profile("session-4", skills=["python", "fastapi"])
        result = agent.chat("session-4", "Find python roles and compare with my profile")

    assert len(result["trace"]) == 2
    assert {entry["tool"] for entry in result["trace"]} == {"search_jobs", "get_candidate_skills"}
    assert result["response"] == "Combined summary ready."


def test_max_tool_round_protection() -> None:
    mock_client = Mock()
    mock_client.models.generate_content.side_effect = [
        _tools_response(_function_call("search_jobs", query="python")),
        _tools_response(_function_call("search_jobs", query="python")),
        _tools_response(_function_call("search_jobs", query="python")),
        _tools_response(_function_call("search_jobs", query="python")),
        _tools_response(_function_call("search_jobs", query="python")),
    ]

    with patch("app.agents.career_agent.genai.Client", return_value=mock_client):
        agent = CareerAgent(session_id="session-5")
        with pytest.raises(ToolLoopError, match="Maximum tool round limit reached"):
            agent.chat("session-5", "Look up jobs repeatedly")


def test_tools_selected_by_gemini_not_keywords() -> None:
    mock_client = Mock()
    mock_client.models.generate_content.side_effect = [
        _tools_response(_function_call("explain_match", job_id="job-202")),
        _text_response("The match is strong."),
    ]

    matching_service = Mock()
    matching_service.match_job.return_value = JobMatchResult(
        job_id="job-202",
        match_score=84,
        matched_skills=["python", "sql"],
        missing_skills=["analytics"],
        reason="You are a strong fit for the role.",
    )

    with patch("app.agents.career_agent.genai.Client", return_value=mock_client):
        agent = CareerAgent(session_id="session-6", matching_service=matching_service)
        agent.profile_store.set_profile("session-6", skills=["python", "sql"])
        response = agent.chat("session-6", "Can you help with a general question?")

    assert response["trace"][0]["tool"] == "explain_match"
    assert response["response"] == "The match is strong."


def test_api_route_accepts_agent_chat() -> None:
    mock_client = Mock()
    mock_client.models.generate_content.side_effect = [
        _tools_response(_function_call("get_candidate_skills")),
        _text_response("Skills retrieved."),
    ]

    with patch("app.agents.career_agent.genai.Client", return_value=mock_client):
        client = TestClient(create_app())
        response = client.post("/api/agent/chat", json={"session_id": "session-7", "message": "List my strengths"})

    assert response.status_code == 200
    assert response.json()["response"] == "Skills retrieved."
