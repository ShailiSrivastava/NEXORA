import json
from unittest.mock import Mock

import pytest

from app.memory.redis_memory import RedisMemory, RedisMemoryError


class FakeRedisClient:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def get(self, key: str):
        return self.store.get(key)

    def set(self, key: str, value: str, ex: int | None = None):
        self.store[key] = value
        return True

    def delete(self, key: str):
        return 1 if self.store.pop(key, None) is not None else 0


def test_save_and_retrieve_conversation_history() -> None:
    client = FakeRedisClient()
    memory = RedisMemory(client=client, ttl_seconds=60)

    memory.save_message("session-a", "user", "Hi")
    memory.save_message("session-a", "assistant", "Hello")

    history = memory.get_history("session-a")
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


def test_separate_histories_for_different_sessions() -> None:
    client = FakeRedisClient()
    memory = RedisMemory(client=client, ttl_seconds=60)

    memory.save_message("session-a", "user", "A")
    memory.save_message("session-b", "user", "B")

    assert memory.get_history("session-a")[0]["content"] == "A"
    assert memory.get_history("session-b")[0]["content"] == "B"


def test_save_and_retrieve_candidate_profile() -> None:
    client = FakeRedisClient()
    memory = RedisMemory(client=client, ttl_seconds=60)

    profile = {"skills": ["python", "fastapi"], "preferences": {"remote": True}}
    memory.save_candidate_profile("session-a", profile)

    assert memory.get_candidate_profile("session-a") == profile


def test_ttl_configuration() -> None:
    client = FakeRedisClient()
    memory = RedisMemory(client=client, ttl_seconds=120)
    assert memory.ttl_seconds == 120


def test_memory_persists_between_chat_requests() -> None:
    client = FakeRedisClient()
    memory = RedisMemory(client=client, ttl_seconds=60)

    memory.save_message("session-1", "user", "I like remote jobs")
    memory.save_candidate_profile("session-1", {"skills": ["python"], "preferences": {"remote": True}})

    assert memory.get_history("session-1")[-1]["content"] == "I like remote jobs"
    assert memory.get_candidate_profile("session-1")["preferences"]["remote"] is True


def test_agent_receives_previous_context() -> None:
    client = FakeRedisClient()
    memory = RedisMemory(client=client, ttl_seconds=60)
    memory.save_message("session-2", "user", "I prefer remote work")
    memory.save_candidate_profile("session-2", {"skills": ["python"], "preferences": {"remote": True}})

    history = memory.get_history("session-2")
    profile = memory.get_candidate_profile("session-2")

    assert history[0]["content"] == "I prefer remote work"
    assert profile["preferences"]["remote"] is True


def test_clear_session() -> None:
    client = FakeRedisClient()
    memory = RedisMemory(client=client, ttl_seconds=60)

    memory.save_message("session-3", "user", "clear me")
    memory.save_candidate_profile("session-3", {"skills": ["python"]})

    assert memory.clear_session("session-3") is True
    assert memory.get_history("session-3") == []
    assert memory.get_candidate_profile("session-3") == {}


def test_redis_unavailable_behavior() -> None:
    class BrokenRedis:
        def get(self, *_args, **_kwargs):
            raise RuntimeError("down")

        def set(self, *_args, **_kwargs):
            raise RuntimeError("down")

        def delete(self, *_args, **_kwargs):
            raise RuntimeError("down")

    memory = RedisMemory(client=BrokenRedis(), ttl_seconds=60)

    with pytest.raises(RedisMemoryError):
        memory.get_history("session-x")

    with pytest.raises(RedisMemoryError):
        memory.save_message("session-x", "user", "hello")
