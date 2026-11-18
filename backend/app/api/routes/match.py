from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.matching_service import JobMatchValidationError, MatchingService

router = APIRouter(prefix="/api", tags=["matching"])


class MatchRequest(BaseModel):
    candidate_skills: list[str] = Field(..., min_length=1)
    job_description: str = Field(..., min_length=1)
    job_id: str = Field(..., min_length=1)


@router.post("/match")
def match_job(request: MatchRequest) -> dict:
    service = MatchingService()
    try:
        result = service.match_job(
            candidate_skills=request.candidate_skills,
            job_description=request.job_description,
            job_id=request.job_id,
        )
    except JobMatchValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return result.model_dump()
