from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents.career_agent import CareerAgent, ToolExecutionError, ToolLoopError
from app.memory.redis_memory import RedisMemory, RedisMemoryError

router = APIRouter(prefix="/api", tags=["agent"])


class AgentChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class AgentProfileRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    profile: dict = Field(default_factory=dict)


@router.post("/agent/chat")
def agent_chat(request: AgentChatRequest) -> dict:
    memory = RedisMemory()
    agent = CareerAgent(session_id=request.session_id, memory=memory)
    try:
        return agent.chat(request.session_id, request.message)
    except RedisMemoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ToolExecutionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ToolLoopError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc


@router.get("/agent/history/{session_id}")
def get_agent_history(session_id: str) -> dict:
    memory = RedisMemory()
    try:
        return {"session_id": session_id, "history": memory.get_history(session_id)}
    except RedisMemoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/agent/profile")
def save_agent_profile(request: AgentProfileRequest) -> dict:
    memory = RedisMemory()
    try:
        saved = memory.save_candidate_profile(request.session_id, request.profile)
        return {"session_id": request.session_id, "profile": saved}
    except RedisMemoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.delete("/agent/session/{session_id}")
def clear_session(session_id: str) -> dict:
    memory = RedisMemory()
    try:
        cleared = memory.clear_session(session_id)
        return {"session_id": session_id, "cleared": cleared}
    except RedisMemoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
