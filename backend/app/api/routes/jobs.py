from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.memory.redis_memory import RedisMemory
from app.retrieval.reranker import CrossEncoderReranker
from app.retrieval.vector_store import VectorStore
from app.services.personalization_service import PersonalizationService

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class JobUpsertRequest(BaseModel):
    job_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    company: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    location: str = Field(default="")
    remote: bool = Field(default=False)
    experience_level: str = Field(default="")
    required_skills: list[str] = Field(default_factory=list)
    salary: str = Field(default="")
    role: str = Field(default="")


@router.get("/recommendations")
def get_recommendations(
    session_id: str = Query(...),
    query: str = Query(...),
    top_k: int = Query(5),
) -> dict[str, Any]:
    memory = RedisMemory()
    try:
        profile = memory.get_candidate_profile(session_id)
    except Exception as exc:  # pragma: no cover - exercised through tests with mocks
        raise HTTPException(status_code=503, detail=f"Redis unavailable: {exc}") from exc

    vector_store = VectorStore()
    initial_results = vector_store.search(query, top_k=max(top_k, 1))
    reranker = CrossEncoderReranker()
    reranked = reranker.rerank(query, initial_results)
    personalization_service = PersonalizationService()
    personalized = personalization_service.personalize(profile, reranked)

    return {
        "session_id": session_id,
        "query": query,
        "original_ranking": initial_results,
        "reranked_ranking": reranked,
        "final_personalized_ranking": personalized,
    }


@router.post("/upsert")
def upsert_job(payload: JobUpsertRequest) -> dict[str, Any]:
    vector_store = VectorStore()
    job = payload.model_dump()
    vector_store.upsert_job(job)
    return {"status": "ok", "job_id": job["job_id"]}


@router.get("/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    vector_store = VectorStore()
    job = vector_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
