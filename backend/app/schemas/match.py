from pydantic import BaseModel, Field, field_validator


class JobMatchResult(BaseModel):
    job_id: str = Field(..., min_length=1)
    match_score: int = Field(..., ge=0, le=100)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    reason: str = Field(..., min_length=1)

    @field_validator("matched_skills", "missing_skills")
    @classmethod
    def validate_skill_lists(cls, value: list[str]) -> list[str]:
        return [skill.strip() for skill in value if skill and skill.strip()]
