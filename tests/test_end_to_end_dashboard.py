"""
End-to-End Test for Phase 4: Dashboard Integration
Simulates candidate pool loading, batch screening, Pandas leaderboard sorting, and CSV export.
"""

import unittest
from pathlib import Path
import pandas as pd

import utils
from screener import evaluate_candidate_batch, get_gemini_client

SAMPLE_JD = """Role: Senior Full-Stack AI Engineer
Requirements:
- 4+ years of professional software engineering experience.
- Strong proficiency in Python, FastAPI, and PostgreSQL.
- Hands-on experience with LLM orchestration and Google GenAI SDK (Gemini).
- Responsive frontend skills with Streamlit or React.
- Containerization with Docker."""


class TestEndToEndDashboardIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = get_gemini_client()
        cls.samples_dir = Path("sample_resumes")
        
        # Build candidate pool from sample resumes
        cls.candidate_pool = []
        for pdf_path in sorted(cls.samples_dir.glob("*.pdf")):
            parse_res = utils.extract_text_from_pdf(pdf_path)
            cls.candidate_pool.append({
                "id": pdf_path.stem,
                "name": pdf_path.stem.replace("_", " ").title(),
                "file_name": pdf_path.name,
                "parsed_text": parse_res.text,
                "role": "Applicant",
                "screened": False,
            })

    def test_end_to_end_batch_and_leaderboard(self):
        self.assertEqual(len(self.candidate_pool), 3)

        # 1. Run batch screening
        results = evaluate_candidate_batch(
            job_description=SAMPLE_JD,
            candidates=self.candidate_pool,
            client=self.client,
        )

        self.assertEqual(len(results), 3)

        # 2. Sort results descending by score
        sorted_results = sorted(results, key=lambda x: x["match_score"], reverse=True)

        # 3. Build Pandas DataFrame
        df = pd.DataFrame([
            {
                "Rank": f"#{idx}",
                "Candidate Name": cand["candidate_name"],
                "Match Score": cand["match_score"],
                "Hiring Verdict": cand["recommendation"],
                "Matching Skills": len(cand.get("matching_skills", [])),
                "Missing Skills": len(cand.get("missing_skills", [])),
                "Resume File": cand["file_name"],
            }
            for idx, cand in enumerate(sorted_results, start=1)
        ])

        # 4. Verify ranking ordering
        self.assertGreater(sorted_results[0]["match_score"], sorted_results[1]["match_score"])
        self.assertGreater(sorted_results[1]["match_score"], sorted_results[2]["match_score"])

        # Alex Rivera should be #1
        self.assertIn("Alex", sorted_results[0]["candidate_name"])
        # Taylor Smith should be last
        self.assertIn("Taylor", sorted_results[-1]["candidate_name"])

        # 5. Verify CSV export
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        self.assertTrue(len(csv_bytes) > 100)
        self.assertIn(b"Alex", csv_bytes)

        print("\n=== End-to-End Leaderboard Results ===")
        print(df.to_string(index=False))


if __name__ == "__main__":
    unittest.main()
