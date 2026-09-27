"""
Pydantic Domain Models for AI Resume Screening
Schema definitions used as response_schema for Gemini API structured output.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class RecommendationLevel(str, Enum):
    """Ruthless hiring decision classification."""

    STRONG_HIRE = "Strong Hire"
    CONSIDER = "Consider"
    REJECT = "Reject"


class CandidateEvaluation(BaseModel):
    """Structured evaluation schema returned by the Gemini AI evaluation engine."""

    candidate_name: str = Field(
        ...,
        description="Full legal or professional name of the candidate as identified from their resume.",
    )
    match_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Strict numerical match score between 0 and 100 assessing technical capability and experience fit.",
    )
    recommendation: RecommendationLevel = Field(
        ...,
        description="Definitive recruiter recommendation: 'Strong Hire' (>=85), 'Consider' (65-84), or 'Reject' (<65).",
    )
    matching_skills: List[str] = Field(
        default_factory=list,
        description="Specific technical skills, technologies, and qualifications explicitly verified in both the resume and the Job Description.",
    )
    missing_skills: List[str] = Field(
        default_factory=list,
        description="Mandatory or highly prioritized skills requested in the Job Description that the candidate does not demonstrate.",
    )
    brief_justification: str = Field(
        ...,
        description="Concise, analytical recruiter justification detailing evidence of competence, critical gaps, and reasoning behind the match score.",
    )
    estimated_experience_years: Optional[float] = Field(
        default=None,
        description="Estimated total years of relevant professional experience derived from candidate employment dates.",
    )


class BatchScreeningSummary(BaseModel):
    """Aggregated screening metrics across a batch of evaluated candidates."""

    total_candidates: int = Field(..., description="Total candidates evaluated in batch.")
    screened_count: int = Field(..., description="Successfully screened candidates.")
    top_score: Optional[int] = Field(default=None, description="Highest score achieved in batch.")
    average_score: Optional[float] = Field(default=None, description="Average match score.")
    evaluations: List[CandidateEvaluation] = Field(
        default_factory=list,
        description="List of individual candidate evaluations ordered by rank.",
    )
