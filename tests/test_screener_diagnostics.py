"""
Unit tests for Gemini API error diagnostics, fallback logic, and AFC configuration.
"""

import unittest
from unittest.mock import MagicMock, patch
from google.genai import errors, types
from pydantic import ValidationError

from models import CandidateEvaluation, RecommendationLevel
from screener import (
    _extract_safe_error_diagnostic,
    evaluate_candidate,
    evaluate_candidate_batch,
)

SAMPLE_JD = "Role: Software Engineer\nRequirements:\n- Python 3+ years\n- FastAPI\n- SQL"
SAMPLE_RESUME = "Jane Doe\nExperienced Python backend engineer with 4 years FastAPI and PostgreSQL."


class TestScreenerDiagnostics(unittest.TestCase):
    """Test error parsing, sanitization, and diagnostic reporting."""

    def test_sanitize_api_key_redaction(self):
        fake_key = "MOCK_KEY"
        err = Exception(f"Failed request with key={fake_key} and token {fake_key}")
        diag = _extract_safe_error_diagnostic(err, "gemini-3.8-flash")
        
        self.assertNotIn(fake_key, diag["safe_message"])
        self.assertIn("[REDACTED", diag["safe_message"])

    def test_quota_exhaustion_detection(self):
        raw_err = errors.ClientError(
            429,
            {
                "error": {
                    "code": 429,
                    "message": "Resource has been exhausted (e.g. check quota). Quota exceeded for metric: free_tier_requests",
                    "status": "RESOURCE_EXHAUSTED",
                }
            },
            None,
        )
        diag = _extract_safe_error_diagnostic(raw_err, "gemini-3.8-flash")
        self.assertTrue(diag["is_quota_exhausted"])
        self.assertEqual(diag["category"], "Quota Exhausted (429)")
        self.assertEqual(diag["status_code"], 429)

    def test_authentication_error_detection(self):
        raw_err = errors.ClientError(
            401,
            {
                "error": {
                    "code": 401,
                    "message": "Request had invalid authentication credentials.",
                    "status": "UNAUTHENTICATED",
                }
            },
            None,
        )
        diag = _extract_safe_error_diagnostic(raw_err, "gemini-3.8-flash")
        self.assertFalse(diag["is_quota_exhausted"])
        self.assertEqual(diag["category"], "Authentication / Permission Error")
        self.assertEqual(diag["status_code"], 401)

    def test_model_not_found_detection(self):
        raw_err = errors.ClientError(
            404,
            {
                "error": {
                    "code": 404,
                    "message": "Model gemini-2.5-flash is no longer available to new users.",
                    "status": "NOT_FOUND",
                }
            },
            None,
        )
        diag = _extract_safe_error_diagnostic(raw_err, "gemini-2.5-flash")
        self.assertEqual(diag["category"], "Model Unavailable / Not Found (404)")
        self.assertEqual(diag["status_code"], 404)

    def test_markdown_json_parsing_resilience(self):
        """Verify that markdown code fences around JSON are stripped cleanly."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.parsed = None
        mock_response.text = (
            "```json\n"
            "{\n"
            '  "candidate_name": "Resilient Candidate",\n'
            '  "match_score": 85,\n'
            '  "recommendation": "Strong Hire",\n'
            '  "matching_skills": ["Python", "FastAPI"],\n'
            '  "missing_skills": [],\n'
            '  "brief_justification": "Candidate demonstrated strong Python and FastAPI competencies throughout their work history.",\n'
            '  "estimated_experience_years": 4.0\n'
            "}\n"
            "```"
        )
        mock_client.models.generate_content.return_value = mock_response

        eval_res = evaluate_candidate(
            job_description=SAMPLE_JD,
            resume_text=SAMPLE_RESUME,
            candidate_name="Resilient Candidate",
            client=mock_client,
            preferred_model="mock-model",
        )

        self.assertEqual(eval_res.candidate_name, "Resilient Candidate")
        self.assertEqual(eval_res.match_score, 85)
        self.assertEqual(eval_res.recommendation, RecommendationLevel.STRONG_HIRE)

    def test_batch_evaluation_does_not_crash_on_single_candidate_failure(self):
        """One failed candidate evaluation must not crash the batch."""
        mock_client = MagicMock()

        # First call succeeds, second call fails with RuntimeError, third succeeds
        good_response = MagicMock()
        good_response.parsed = CandidateEvaluation(
            candidate_name="Success Candidate",
            match_score=80,
            recommendation=RecommendationLevel.CONSIDER,
            matching_skills=["Python"],
            missing_skills=[],
            brief_justification="Candidate possesses adequate skills.",
            estimated_experience_years=3.0,
        )

        def mock_generate_content(model, contents, config):
            if "Cand 2" in contents:
                raise RuntimeError("Simulated API failure on second candidate")
            return good_response

        mock_client.models.generate_content.side_effect = mock_generate_content

        candidates = [
            {"id": "1", "name": "Cand 1", "file_name": "c1.pdf", "parsed_text": SAMPLE_RESUME},
            {"id": "2", "name": "Cand 2", "file_name": "c2.pdf", "parsed_text": SAMPLE_RESUME},
            {"id": "3", "name": "Cand 3", "file_name": "c3.pdf", "parsed_text": SAMPLE_RESUME},
        ]

        results = evaluate_candidate_batch(
            job_description=SAMPLE_JD,
            candidates=candidates,
            client=mock_client,
            preferred_model="mock-model",
        )

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["status"], "Success")
        self.assertEqual(results[1]["status"], "Error")
        self.assertEqual(results[1]["match_score"], 0)
        self.assertIn("Automated evaluation failed", results[1]["justification"])
        self.assertEqual(results[2]["status"], "Success")

    def test_empty_resume_text_handled_gracefully(self):
        """Missing or unreadable resume text should be flagged as Failed without calling API."""
        mock_client = MagicMock()
        candidates = [
            {"id": "1", "name": "Unreadable Cand", "file_name": "blank.pdf", "parsed_text": ""},
        ]

        results = evaluate_candidate_batch(
            job_description=SAMPLE_JD,
            candidates=candidates,
            client=mock_client,
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "Failed")
        self.assertEqual(results[0]["match_score"], 0)
        self.assertEqual(results[0]["recommendation"], "Reject")
        self.assertIn("No readable text", results[0]["justification"])
        # API should not be called at all for empty text
        mock_client.models.generate_content.assert_not_called()


if __name__ == "__main__":
    unittest.main()
