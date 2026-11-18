from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import redis

from app.config import settings


class RedisMemoryError(RuntimeError):
    pass


class RedisMemory:
    def __init__(self, client: Any | None = None, *, ttl_seconds: int | None = None) -> None:
        self.client = client or redis.Redis.from_url(settings.redis_url, decode_responses=True)
        self.ttl_seconds = ttl_seconds if ttl_seconds is not None else getattr(settings, "redis_ttl_seconds", 3600)

    def _session_key(self, session_id: str) -> str:
        return f"nexora:session:{session_id}"

    def _profile_key(self, session_id: str) -> str:
        return f"nexora:profile:{session_id}"

    def _safe_redis_call(self, func_name: str, *, operation: Any, default: Any = None) -> Any:
        try:
            return operation()
        except (redis.RedisError, RuntimeError, TypeError, ValueError) as exc:
            raise RedisMemoryError(f"Redis {func_name} failed: {exc}") from exc

    def save_message(self, session_id: str, role: str, content: str) -> dict[str, Any]:
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        history = self.get_history(session_id)
        history.append(message)
        self._safe_redis_call(
            "set",
            operation=lambda: self.client.set(self._session_key(session_id), json.dumps(history), ex=self.ttl_seconds),
        )
        return message

    def get_history(self, session_id: str) -> list[dict[str, Any]]:
        raw = self._safe_redis_call(
            "get",
            operation=lambda: self.client.get(self._session_key(session_id)),
            default=[],
        )
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []

    def save_candidate_profile(self, session_id: str, profile: dict[str, Any]) -> dict[str, Any]:
        payload = profile.copy()
        self._safe_redis_call(
            "set",
            operation=lambda: self.client.set(self._profile_key(session_id), json.dumps(payload), ex=self.ttl_seconds),
        )
        return payload

    def get_candidate_profile(self, session_id: str) -> dict[str, Any]:
        raw = self._safe_redis_call(
            "get",
            operation=lambda: self.client.get(self._profile_key(session_id)),
            default={},
        )
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def clear_session(self, session_id: str) -> bool:
        deleted = 0
        for key in (self._session_key(session_id), self._profile_key(session_id)):
            deleted += int(self._safe_redis_call("delete", operation=lambda: self.client.delete(key), default=0) or 0)
        return deleted > 0
