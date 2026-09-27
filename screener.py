"""
AI Evaluation Engine — Gemini Structured Recruiter Evaluator
AI Resume Screening System — Phase 3
Uses Google GenAI SDK with Pydantic structured output models.
"""

import json
import logging
import os
import time
from typing import Callable, List, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from models import CandidateEvaluation, RecommendationLevel

# Load local environment
load_dotenv()
logger = logging.getLogger(__name__)

# Fallback sequence of Gemini models to withstand demand spikes (e.g. 503 UNAVAILABLE)
FALLBACK_MODELS = [
    "gemini-3.5-flash",
    "gemini-3.8-flash",
    "gemini-flash-latest",
]

# Ruthless Technical Recruiter System Prompt
RUTHLESS_RECRUITER_SYSTEM_INSTRUCTION = """You are an elite, highly discerning Executive Technical Recruiter and Engineering Hiring Bar-Raiser at a top-tier technology company.
Your mandate is to ruthlessly and objectively evaluate candidate resumes against a specific Job Description (JD).

Core Evaluation Principles:
1. STRICT TECHNICAL SCRUTINY:
   - Do NOT reward passive buzzword stuffing or isolated skills listed without employment context. Look for concrete proof of application: production systems, architectural decisions, technical ownership, and measurable deliverables.
   - If a technology is mentioned only in an arbitrary "Skills" list with no project or work context, do NOT consider it a verified matching skill.
2. SENIORITY & EXPERIENCE RIGOR:
   - Strictly verify seniority and total years of relevant professional experience. If the JD requires 4+ years of full-stack engineering and the candidate has only 1-2 years, penalize the score heavily.
   - Distinguish academic/student projects or coding bootcamps from professional, enterprise software engineering.
3. SCORING RUBRIC (0 to 100):
   - 90 - 100 [Strong Hire]: Rare exceptional match. Exceeds core requirements, proven deep production expertise in the target tech stack, strong deliverables, zero critical gaps.
   - 75 - 89 [Consider]: Solid technical match. Meets all primary core requirements with only minor, easily trainable gaps in secondary or preferred tools.
   - 55 - 74 [Consider with Reservations]: Marginal fit. Possesses adjacent or junior skills, but lacks depth in mandatory technologies or misses required years of experience.
   - 0 - 54 [Reject]: Significant mismatch. Missing fundamental core technologies, wrong domain, or insufficient seniority.
4. BLUNT, ANALYTICAL RECRUITER JUSTIFICATION:
   - Write a direct, analytical, 2-3 paragraph recruiter evaluation. State plainly what the candidate excels at, exactly where they fall short against the JD, and why they earned their score.
   - Avoid generic polite corporate praise. Be direct, actionable, and precise.

Output Schema:
You must strictly return a structured JSON object matching the requested CandidateEvaluation schema.
"""


def get_gemini_client(api_key: Optional[str] = None) -> genai.Client:
    """Initializes and returns a Google GenAI Client with validation."""
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError(
            "GEMINI_API_KEY is not configured. Please add your API key to .env or supply it as an argument."
        )
    return genai.Client(api_key=key)


def evaluate_candidate(
    job_description: str,
    resume_text: str,
    candidate_name: Optional[str] = None,
    client: Optional[genai.Client] = None,
    preferred_model: Optional[str] = None,
    max_retries: int = 3,
) -> CandidateEvaluation:
    """Evaluates a single candidate resume against a Job Description using Gemini structured outputs.

    Args:
        job_description: Target job specifications, requirements, and responsibilities.
        resume_text: Sanitized text extracted from the candidate's resume.
        candidate_name: Optional name hint or identifier.
        client: Optional pre-configured Google GenAI client.
        preferred_model: Preferred Gemini model identifier.
        max_retries: Maximum retry attempts for transient server throttling (503/429).

    Returns:
        CandidateEvaluation: Pydantic model with score, skills breakdown, and justification.
    """
    if not job_description or len(job_description.strip()) < 20:
        raise ValueError("Job Description is too short or empty for rigorous screening.")
    if not resume_text or len(resume_text.strip()) < 30:
        raise ValueError("Resume text contains insufficient content to evaluate.")

    ai_client = client or get_gemini_client()

    prompt_content = f"""Please evaluate the following candidate against the Job Description.

=== TARGET JOB DESCRIPTION ===
{job_description.strip()}

=== CANDIDATE RESUME ===
Candidate Name Hint: {candidate_name or "Extract candidate name from resume"}
Resume Content:
{resume_text.strip()}
"""

    models_to_try = []
    if preferred_model:
        models_to_try.append(preferred_model)
    for m in FALLBACK_MODELS:
        if m not in models_to_try:
            models_to_try.append(m)

    last_exception = None

    for model_name in models_to_try:
        for attempt in range(max_retries):
            try:
                config = types.GenerateContentConfig(
                    system_instruction=RUTHLESS_RECRUITER_SYSTEM_INSTRUCTION,
                    temperature=0.2,
                    response_mime_type="application/json",
                    response_schema=CandidateEvaluation,
                )

                response = ai_client.models.generate_content(
                    model=model_name,
                    contents=prompt_content,
                    config=config,
                )

                # Attempt direct parsed object or parse response text
                if hasattr(response, "parsed") and response.parsed:
                    if isinstance(response.parsed, CandidateEvaluation):
                        return response.parsed
                    elif isinstance(response.parsed, dict):
                        return CandidateEvaluation(**response.parsed)

                # Fallback to json parsing of text
                raw_json = json.loads(response.text)
                return CandidateEvaluation(**raw_json)

            except (errors.ServerError, errors.ClientError) as api_err:
                last_exception = api_err
                error_msg = str(api_err).lower()

                # Model discontinued or not found -> break attempt loop and switch to next model immediately
                if "404" in error_msg or "not_found" in error_msg or "no longer available" in error_msg:
                    logger.warning(f"Model {model_name} unavailable, switching to next fallback.")
                    break

                # Transient 503 or 429 -> apply exponential backoff
                if attempt < max_retries - 1 and ("503" in error_msg or "429" in error_msg or "unavailable" in error_msg):
                    backoff = (2 ** attempt) + 1
                    logger.info(f"Transient error on {model_name}. Retrying in {backoff}s...")
                    time.sleep(backoff)
                else:
                    break

            except Exception as ex:
                last_exception = ex
                logger.error(f"Unexpected error evaluating candidate with {model_name}: {ex}")
                break

    raise RuntimeError(
        f"Failed to evaluate candidate after trying models {models_to_try}. Last error: {last_exception}"
    )


def evaluate_candidate_batch(
    job_description: str,
    candidates: List[dict],
    client: Optional[genai.Client] = None,
    preferred_model: Optional[str] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> List[dict]:
    """Evaluates a batch of candidate profiles against a Job Description.

    Args:
        job_description: Target job specifications.
        candidates: List of candidate dictionaries with 'name', 'file_name', and 'parsed_text'.
        client: Optional pre-configured Google GenAI client.
        preferred_model: Model override.
        progress_callback: Optional callable func(current_idx, total_count, candidate_name).

    Returns:
        List[dict]: Formatted evaluation records ready for UI display and ranking.
    """
    ai_client = client or get_gemini_client()
    total = len(candidates)
    results = []

    for idx, cand in enumerate(candidates, start=1):
        cand_name = cand.get("name", f"Candidate {idx}")
        resume_text = cand.get("parsed_text", "")
        file_name = cand.get("file_name", "Resume.pdf")

        if progress_callback:
            progress_callback(idx, total, cand_name)

        if not resume_text:
            # Cannot evaluate candidate without parsed text
            results.append(
                {
                    "candidate_id": cand.get("id", f"c-{idx}"),
                    "candidate_name": cand_name,
                    "role": cand.get("role", "Applicant"),
                    "file_name": file_name,
                    "match_score": 0,
                    "recommendation": RecommendationLevel.REJECT.value,
                    "matching_skills": [],
                    "missing_skills": ["No readable text in resume"],
                    "justification": "Evaluation failed: No readable text could be extracted from this resume document.",
                    "status": "Failed",
                }
            )
            continue

        try:
            evaluation = evaluate_candidate(
                job_description=job_description,
                resume_text=resume_text,
                candidate_name=cand_name,
                client=ai_client,
                preferred_model=preferred_model,
            )

            results.append(
                {
                    "candidate_id": cand.get("id", f"c-{idx}"),
                    "candidate_name": evaluation.candidate_name or cand_name,
                    "role": cand.get("role", "Applicant"),
                    "file_name": file_name,
                    "match_score": evaluation.match_score,
                    "recommendation": evaluation.recommendation.value,
                    "matching_skills": evaluation.matching_skills,
                    "missing_skills": evaluation.missing_skills,
                    "justification": evaluation.brief_justification,
                    "estimated_experience_years": evaluation.estimated_experience_years,
                    "status": "Success",
                }
            )

        except Exception as e:
            logger.error(f"Error evaluating candidate {cand_name}: {e}")
            results.append(
                {
                    "candidate_id": cand.get("id", f"c-{idx}"),
                    "candidate_name": cand_name,
                    "role": cand.get("role", "Applicant"),
                    "file_name": file_name,
                    "match_score": 0,
                    "recommendation": RecommendationLevel.REJECT.value,
                    "matching_skills": [],
                    "missing_skills": ["Evaluation error"],
                    "justification": f"Automated evaluation encountered an unexpected error: {str(e)}",
                    "status": "Error",
                }
            )

    return results
