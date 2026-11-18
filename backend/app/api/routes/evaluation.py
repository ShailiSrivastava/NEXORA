from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.evaluation.run_evaluation import run_evaluation

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


class EvaluationRequest(BaseModel):
    top_k: int = Field(default=5, ge=1, le=10)
    include_ragas: bool = Field(default=False)


@router.post("/run")
def run_evaluation_endpoint(payload: EvaluationRequest | None = None) -> dict[str, Any]:
    request = payload or EvaluationRequest()
    return run_evaluation(top_k=request.top_k, include_ragas=request.include_ragas)
