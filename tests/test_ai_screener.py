"""
Test Suite for Phase 3: AI Evaluation Engine
Validates Pydantic schema enforcement and tests live Gemini structured evaluation.
"""

import unittest
from pathlib import Path
from pydantic import ValidationError

import utils
from models import CandidateEvaluation, RecommendationLevel
from screener import evaluate_candidate, evaluate_candidate_batch, get_gemini_client

SAMPLE_JD = """Role: Senior Full-Stack AI Engineer
Requirements:
- 4+ years of professional software engineering experience.
- Strong proficiency in Python, FastAPI, and PostgreSQL.
- Hands-on experience with LLM orchestration and Google GenAI SDK (Gemini).
- Responsive frontend skills with Streamlit or React.
- Containerization with Docker."""


class TestCandidateEvaluationSchema(unittest.TestCase):
    """Unit tests for Pydantic domain models."""

    def test_valid_candidate_evaluation(self):
        eval_data = {
            "candidate_name": "Jordan Lee",
            "match_score": 82,
            "recommendation": "Consider",
            "matching_skills": ["Python", "Docker", "PostgreSQL"],
            "missing_skills": ["Google GenAI SDK"],
            "brief_justification": "Solid background in Python and Docker. Lacks production Gemini experience.",
            "estimated_experience_years": 4.0,
        }
        obj = CandidateEvaluation(**eval_data)
        self.assertEqual(obj.match_score, 82)
        self.assertEqual(obj.recommendation, RecommendationLevel.CONSIDER)
        self.assertEqual(len(obj.matching_skills), 3)

    def test_invalid_score_boundary_rejected(self):
        """Scores above 100 or below 0 must be rejected by Pydantic validation."""
        with self.assertRaises(ValidationError):
            CandidateEvaluation(
                candidate_name="Invalid Test",
                match_score=105,  # Invalid: > 100
                recommendation=RecommendationLevel.STRONG_HIRE,
                matching_skills=[],
                missing_skills=[],
                brief_justification="Test",
            )

        with self.assertRaises(ValidationError):
            CandidateEvaluation(
                candidate_name="Negative Test",
                match_score=-10,  # Invalid: < 0
                recommendation=RecommendationLevel.REJECT,
                matching_skills=[],
                missing_skills=[],
                brief_justification="Test",
            )

    def test_missing_required_fields_rejected(self):
        """Missing required fields must trigger ValidationError."""
        with self.assertRaises(ValidationError):
            CandidateEvaluation(
                candidate_name="Missing Fields Test",
                # match_score missing
                recommendation=RecommendationLevel.REJECT,
                brief_justification="Test",
            )


class TestLiveAIEvaluation(unittest.TestCase):
    """Live integration tests with the Gemini API using synthetic sample resumes."""

    @classmethod
    def setUpClass(cls):
        cls.client = get_gemini_client()
        cls.samples_dir = Path("sample_resumes")

        alex_pdf = cls.samples_dir / "Alex_Rivera_Senior_AI_Engineer.pdf"
        taylor_pdf = cls.samples_dir / "Taylor_Smith_Junior_Analyst.pdf"

        cls.alex_text = utils.extract_text_from_pdf(alex_pdf).text
        cls.taylor_text = utils.extract_text_from_pdf(taylor_pdf).text

    def test_alex_rivera_strong_match(self):
        """Senior AI Engineer must score high on Senior Full-Stack AI Engineer role."""
        evaluation = evaluate_candidate(
            job_description=SAMPLE_JD,
            resume_text=self.alex_text,
            candidate_name="Alex Rivera",
            client=self.client,
        )

        self.assertIsInstance(evaluation, CandidateEvaluation)
        self.assertGreaterEqual(evaluation.match_score, 75, f"Expected high score, got {evaluation.match_score}")
        self.assertTrue(len(evaluation.matching_skills) > 0)
        self.assertTrue(len(evaluation.brief_justification) > 50)
        print(f"\n[Test Result] Alex Rivera Score: {evaluation.match_score}/100 ({evaluation.recommendation.value})")

    def test_taylor_smith_low_match(self):
        """Junior Analyst must score low on Senior Full-Stack AI Engineer role."""
        evaluation = evaluate_candidate(
            job_description=SAMPLE_JD,
            resume_text=self.taylor_text,
            candidate_name="Taylor Smith",
            client=self.client,
        )

        self.assertIsInstance(evaluation, CandidateEvaluation)
        self.assertLessEqual(evaluation.match_score, 60, f"Expected low score, got {evaluation.match_score}")
        self.assertEqual(evaluation.recommendation, RecommendationLevel.REJECT)
        self.assertTrue(len(evaluation.missing_skills) > 0)
        print(f"[Test Result] Taylor Smith Score: {evaluation.match_score}/100 ({evaluation.recommendation.value})")


if __name__ == "__main__":
    unittest.main()
