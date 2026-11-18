
from __future__ import annotations

import time
from typing import Any

from google import genai
from google.genai import types

from app.config import settings
from app.memory.redis_memory import RedisMemory, RedisMemoryError
from app.services.matching_service import MatchingService
from app.tools.job_tools import (
    CandidateProfileStore,
    InMemoryJobRepository,
    explain_match,
    get_candidate_skills,
    search_jobs,
    validate_tool_arguments,
)


class ToolExecutionError(RuntimeError):
    pass


class ToolLoopError(RuntimeError):
    pass


class CareerAgent:
    MAX_TOOL_ROUNDS = 5
    MAX_RETRIES = 3

    def __init__(
        self,
        *,
        session_id: str,
        client: Any | None = None,
        profile_store: CandidateProfileStore | None = None,
        job_repository: InMemoryJobRepository | None = None,
        matching_service: MatchingService | None = None,
        memory: RedisMemory | None = None,
    ) -> None:
        self.session_id = session_id
        self.profile_store = profile_store or CandidateProfileStore()
        self.job_repository = job_repository or InMemoryJobRepository()
        self.matching_service = matching_service or MatchingService()

        api_key = settings.gemini_api_key or "test-api-key"
        self.client = client or genai.Client(api_key=api_key)

        self.memory = memory or RedisMemory()
        self._fallback_history: list[dict[str, Any]] = []

    def _generate_with_retry(self, messages: list[Any]) -> Any:
        """Generate Gemini content with bounded retries for transient errors."""

        retryable_status_codes = {429, 500, 502, 503, 504}

        for attempt in range(self.MAX_RETRIES):
            try:
                return self.client.models.generate_content(
                    model=settings.gemini_model,
                    contents=messages,
                    config=self._tool_config(),
                )

            except Exception as exc:
                status_code = (
                    getattr(exc, "code", None)
                    or getattr(exc, "status_code", None)
                )

                if status_code not in retryable_status_codes:
                    raise

                if attempt == self.MAX_RETRIES - 1:
                    raise ToolExecutionError(
                        "Gemini is temporarily unavailable after multiple "
                        "attempts. Please try again shortly."
                    ) from exc

                delay = 2 ** attempt
                time.sleep(delay)

        raise ToolExecutionError("Gemini request failed.")

    def _function_declarations(self) -> list[types.FunctionDeclaration]:
        return [
            types.FunctionDeclaration(
                name="search_jobs",
                description=(
                    "Search the indexed job database for relevant jobs. "
                    "Return job IDs, titles, companies and descriptions."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "query": types.Schema(
                            type=types.Type.STRING,
                            description="Search query for jobs.",
                        )
                    },
                    required=["query"],
                ),
            ),
            types.FunctionDeclaration(
                name="get_candidate_skills",
                description=(
                    "Return the current candidate's skills from the "
                    "stored profile for the active session."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={},
                ),
            ),
            types.FunctionDeclaration(
                name="explain_match",
                description=(
                    "Explain why a specific job matches or does not "
                    "match the candidate."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "job_id": types.Schema(
                            type=types.Type.STRING,
                            description="Job ID to explain.",
                        )
                    },
                    required=["job_id"],
                ),
            ),
        ]

    def _tool_config(self) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            tools=[
                types.Tool(
                    function_declarations=self._function_declarations()
                )
            ]
        )

    def _extract_function_calls(
        self,
        response: Any,
    ) -> list[dict[str, Any]]:

        if hasattr(response, "function_calls"):
            calls = getattr(response, "function_calls")

            if calls:
                normalized: list[dict[str, Any]] = []

                for item in calls:
                    if isinstance(item, dict):
                        name = item.get("name")
                        args = item.get("args") or {}
                    else:
                        name = getattr(item, "name", None)
                        args = getattr(item, "args", None) or {}

                    normalized.append({
                        "name": name,
                        "args": args,
                    })

                return normalized

        candidates = getattr(response, "candidates", None)

        if candidates:
            for candidate in candidates:
                content = getattr(candidate, "content", None)

                if content is None:
                    continue

                parts = getattr(content, "parts", None) or []

                for part in parts:
                    if getattr(part, "function_call", None):
                        fc = part.function_call

                        return [{
                            "name": getattr(fc, "name", None),
                            "args": getattr(fc, "args", None) or {},
                        }]

        data = getattr(response, "data", None)

        if isinstance(data, dict) and "function_calls" in data:
            return data["function_calls"]

        return []

    def _extract_text(self, response: Any) -> str:

        if hasattr(response, "text") and response.text:
            return str(response.text)

        candidates = getattr(response, "candidates", None)

        if candidates:
            for candidate in candidates:
                content = getattr(candidate, "content", None)

                if content is None:
                    continue

                parts = getattr(content, "parts", None) or []

                for part in parts:
                    text_value = getattr(part, "text", None)

                    if text_value:
                        return str(text_value)

        return "No response generated by Gemini."

    def _execute_tool(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
    ) -> dict[str, Any]:

        try:
            validated = validate_tool_arguments(
                tool_name,
                tool_args,
            )
        except ValueError as exc:
            raise ToolExecutionError(str(exc)) from exc

        if tool_name == "search_jobs":
            return {
                "results": search_jobs(
                    validated["query"],
                    repository=self.job_repository,
                )
            }

        if tool_name == "get_candidate_skills":
            profile_skills = get_candidate_skills(
                self.session_id,
                profile_store=self.profile_store,
            )

            return {"skills": profile_skills}

        if tool_name == "explain_match":
            result = explain_match(
                validated["job_id"],
                session_id=self.session_id,
                profile_store=self.profile_store,
                repository=self.job_repository,
                matching_service=self.matching_service,
            )

            return result

        raise ToolExecutionError(f"Unknown tool: {tool_name}")

    def _load_memory_context(
        self,
        session_id: str,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:

        try:
            history = self.memory.get_history(session_id)
            profile = self.memory.get_candidate_profile(session_id)

        except RedisMemoryError:
            history = list(self._fallback_history)
            profile = {}

        if not history and self._fallback_history:
            history = list(self._fallback_history)

        return history, profile

    def _save_memory_event(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> None:

        try:
            self.memory.save_message(
                session_id,
                role,
                content,
            )

        except RedisMemoryError:
            self._fallback_history.append({
                "role": role,
                "content": content,
                "timestamp": "fallback",
            })

    def _save_profile_memory(
        self,
        session_id: str,
        profile: dict[str, Any],
    ) -> None:

        try:
            self.memory.save_candidate_profile(
                session_id,
                profile,
            )

        except RedisMemoryError:
            pass

    def chat(
        self,
        session_id: str,
        message: str,
    ) -> dict[str, Any]:

        if not session_id:
            raise ToolExecutionError("session_id is required")

        if not message or not message.strip():
            raise ToolExecutionError("message is required")

        self.session_id = session_id

        memory_history, candidate_profile = (
            self._load_memory_context(session_id)
        )

        self._save_memory_event(
            session_id,
            "user",
            message,
        )

        if candidate_profile:
            self.profile_store.set_profile(
                session_id,
                skills=candidate_profile.get("skills", []),
                preferences=candidate_profile.get("preferences", {}),
            )

        history_text = "\n".join(
            f"{entry.get('role', 'unknown')}: "
            f"{entry.get('content', '')}"
            for entry in memory_history
        )

        profile_text = (
            f"Candidate profile: "
            f"skills={candidate_profile.get('skills', [])}, "
            f"preferences={candidate_profile.get('preferences', {})}"
            if candidate_profile
            else "Candidate profile: no saved profile available."
        )

        messages: list[Any] = [
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            f"Previous conversation:\n{history_text}\n\n"
                            f"{profile_text}\n\n"
                            f"Current user message:\n{message}"
                        )
                    }
                ],
            }
        ]

        trace: list[dict[str, Any]] = []
        final_response = ""

        for round_index in range(self.MAX_TOOL_ROUNDS):

            response = self._generate_with_retry(messages)

            function_calls = self._extract_function_calls(response)

            if not function_calls:
                final_response = self._extract_text(response)
                break

            tool_results: list[dict[str, Any]] = []

            for call in function_calls:
                tool_name = call.get("name")
                tool_args = call.get("args") or {}

                if not tool_name:
                    raise ToolExecutionError(
                        "Gemini returned a function call without a tool name."
                    )

                try:
                    result = self._execute_tool(
                        tool_name,
                        tool_args,
                    )

                except ToolExecutionError as exc:
                    raise ToolExecutionError(
                        f"Tool execution failed for {tool_name}: {exc}"
                    ) from exc

                trace.append({
                    "tool": tool_name,
                    "arguments": tool_args,
                    "result": result,
                })

                self._save_memory_event(
                    session_id,
                    "tool",
                    f"{tool_name}: {tool_args}",
                )

                self._save_memory_event(
                    session_id,
                    "tool_result",
                    str(result),
                )

                tool_results.append({
                    "role": "function",
                    "parts": [
                        {
                            "function_response": {
                                "name": tool_name,
                                "response": result,
                            }
                        }
                    ],
                })

            messages.extend(tool_results)

        else:
            raise ToolLoopError(
                "Maximum tool round limit reached; tool loop aborted."
            )

        self._save_memory_event(
            session_id,
            "assistant",
            final_response,
        )

        self._save_profile_memory(
            session_id,
            self.profile_store.get_profile(session_id),
        )

        return {
            "response": final_response,
            "trace": trace,
        }
