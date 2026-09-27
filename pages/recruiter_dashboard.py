"""
Recruiter Dashboard — AI Screening & Leaderboard
HR command center for evaluating candidate resumes against Job Descriptions.
Features top-row summary metrics, live progress tracking, a stylized Pandas leaderboard,
and rich candidate detail expanders.
API key is read securely from .env (no UI inputs).
"""

from datetime import datetime
import os
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import streamlit as st
from screener import evaluate_candidate_batch
from utils import extract_text_from_pdf

# Ensure environment variables are loaded
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

MAX_UPLOAD_SIZE_MB = 10
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

# Page Header
st.markdown('<div class="main-header">📊 Recruiter Command Center</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Review applicant resumes, define job requirements, and run AI-powered candidate ranking with ruthless recruiter precision.</div>',
    unsafe_allow_html=True,
)

# Environment / Security Status Banner
if not GEMINI_API_KEY:
    st.warning(
        "🔒 **Admin Notice:** `GEMINI_API_KEY` is not detected in your `.env` file. "
        "Please add `GEMINI_API_KEY=your_key` to `.env` to enable live LLM screening.",
        icon="⚠️",
    )

# --- Top Row Summary Metrics ---
total_applicants = len(st.session_state.candidate_pool)
screened_candidates = [c for c in st.session_state.candidate_pool if c.get("screened", False)]
screened_count = len(screened_candidates)

# Compute dynamic scores if results are available
results = st.session_state.analysis_results
if results:
    scores = [r["match_score"] for r in results]
    top_score = max(scores) if scores else None
    avg_score = round(sum(scores) / len(scores), 1) if scores else None
else:
    top_score = None
    avg_score = None

metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
metric_col1.metric("Total Applicants", f"{total_applicants}")
metric_col2.metric("Candidates Screened", f"{screened_count}")
metric_col3.metric("Top Match Score", f"{top_score}%" if top_score is not None else "—")
metric_col4.metric("Average Score", f"{avg_score}%" if avg_score is not None else "—")

st.markdown("---")

# --- Dual Section: Job Description & Candidate Pool ---
col_jd, col_pool = st.columns([1, 1], gap="large")

# Sample Job Description
SAMPLE_JD = """Role: Senior Full-Stack AI Engineer
Location: Remote

Responsibilities:
- Build, deploy, and scale web applications integrating Generative AI APIs (Gemini, OpenAI).
- Architect robust backends with Python, FastAPI, and PostgreSQL.
- Develop responsive frontends using modern frameworks (Streamlit, Next.js, or React).
- Implement structured output validation with Pydantic and prompt engineering pipelines.
- Integrate document processing (PDF parsing, OCR, vector search).

Requirements:
- 4+ years of professional software engineering experience.
- Strong proficiency in Python, modern JavaScript/TypeScript, and RESTful APIs.
- Hands-on experience with LLM orchestration frameworks and structured JSON output.
- Familiarity with cloud deployment (GCP, AWS) and containerization (Docker).
- Excellent technical communication and problem-solving skills."""


def load_sample_jd():
    st.session_state.job_description = SAMPLE_JD


def clear_jd():
    st.session_state.job_description = ""


def load_sample_resumes_to_pool():
    """Loads pre-generated sample resumes into the candidate pool for fast testing."""
    samples_dir = Path("sample_resumes")
    if not samples_dir.exists():
        st.warning("No sample_resumes folder found.")
        return

    added_count = 0
    for pdf_path in sorted(samples_dir.glob("*.pdf")):
        # Check if already added
        if any(c.get("file_name") == pdf_path.name for c in st.session_state.candidate_pool):
            continue

        parse_res = extract_text_from_pdf(pdf_path)
        if parse_res.success:
            name_guess = pdf_path.stem.replace("_", " ").title()
            st.session_state.candidate_pool.append(
                {
                    "id": f"sample-{len(st.session_state.candidate_pool) + 1:03d}",
                    "name": name_guess,
                    "email": f"{pdf_path.stem.lower()}@example.com",
                    "role": "Applicant",
                    "years_exp": 0,
                    "file_name": pdf_path.name,
                    "file_size_kb": round(len(pdf_path.read_bytes()) / 1024, 1),
                    "file_bytes": pdf_path.read_bytes(),
                    "parsed_text": parse_res.text,
                    "page_count": parse_res.page_count,
                    "word_count": parse_res.word_count,
                    "parse_status": "Clean",
                    "submitted_at": "Sample Resumes",
                    "screened": False,
                }
            )
            added_count += 1

    if added_count > 0:
        st.success(f"✅ Loaded {added_count} sample resume(s) into candidate pool.")


with col_jd:
    st.subheader("1. Job Description & Criteria")
    st.caption("Paste the target role description, required competencies, and experience levels.")

    jd_text = st.text_area(
        label="Job Description",
        value=st.session_state.job_description,
        height=320,
        placeholder="Paste complete Job Description here...",
        label_visibility="collapsed",
    )
    st.session_state.job_description = jd_text

    # Action buttons for JD
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        st.button("📋 Load Sample JD", on_click=load_sample_jd, use_container_width=True)
    with btn_col2:
        if st.session_state.job_description:
            st.button("🗑️ Clear JD", on_click=clear_jd, use_container_width=True)

    # Word & Char counts
    char_count = len(jd_text)
    word_count = len(jd_text.split()) if jd_text.strip() else 0
    st.caption(f"📊 Stats: **{word_count}** words | **{char_count}** characters")

with col_pool:
    st.subheader("2. Candidate Pool & Batch Upload")
    st.caption("Review submissions from the Candidate Portal or upload additional resumes directly.")

    # Direct recruiter batch uploader (also strictly limited to 10MB)
    direct_files = st.file_uploader(
        f"Batch Upload Resumes (PDF, max {MAX_UPLOAD_SIZE_MB}MB each)",
        type=["pdf"],
        accept_multiple_files=True,
        help=f"Upload candidate resumes. Strictly max {MAX_UPLOAD_SIZE_MB}MB per file.",
    )

    if direct_files:
        for f in direct_files:
            if f.size > MAX_UPLOAD_SIZE_BYTES:
                st.error(f"⚠️ '{f.name}' exceeds the {MAX_UPLOAD_SIZE_MB}MB limit and was skipped.")
                continue

            # Check if file already added
            already_added = any(c.get("file_name") == f.name for c in st.session_state.candidate_pool)
            if not already_added:
                parse_res = extract_text_from_pdf(f)
                if not parse_res.success:
                    st.error(f"⚠️ Could not parse '{f.name}': {parse_res.error}")
                    continue

                if parse_res.is_scanned:
                    st.warning(f"⚠️ '{f.name}': Low text density detected ({parse_res.char_count} chars).")

                st.session_state.candidate_pool.append(
                    {
                        "id": f"batch-{len(st.session_state.candidate_pool) + 1:03d}",
                        "name": f.name.replace(".pdf", "").replace("_", " ").title(),
                        "email": "batch.upload@company.internal",
                        "role": "Direct Batch Upload",
                        "years_exp": 0,
                        "file_name": f.name,
                        "file_size_kb": round(f.size / 1024, 1),
                        "file_bytes": f.getvalue(),
                        "parsed_text": parse_res.text,
                        "page_count": parse_res.page_count,
                        "word_count": parse_res.word_count,
                        "parse_status": "Clean" if not parse_res.is_scanned else "Warning: Low Text",
                        "submitted_at": "Recruiter Batch",
                        "screened": False,
                    }
                )

    # Sample resumes helper button
    pool_btn1, pool_btn2 = st.columns(2)
    with pool_btn1:
        st.button("📁 Load 3 Sample Resumes", on_click=load_sample_resumes_to_pool, use_container_width=True)
    with pool_btn2:
        if st.session_state.candidate_pool:
            if st.button("🗑️ Clear Pool", use_container_width=True):
                st.session_state.candidate_pool = []
                st.session_state.analysis_results = []
                st.rerun()

    # Display current candidate pool count & list
    if st.session_state.candidate_pool:
        st.success(f"📂 **{len(st.session_state.candidate_pool)}** candidate resume(s) in active screening pool")
        with st.expander("Inspect Candidate Pool & Extracted Text", expanded=False):
            for idx, cand in enumerate(st.session_state.candidate_pool, start=1):
                p_count = cand.get("page_count", "—")
                w_count = cand.get("word_count", "—")
                st.markdown(
                    f"**{idx}. {cand['name']}** &bull; `{cand['file_name']}` *({cand['file_size_kb']} KB)* "
                    f"&bull; 📑 **{p_count}** pages / **{w_count}** words"
                )
                if cand.get("parsed_text"):
                    with st.expander(f"👁️ Preview Extracted Text for {cand['name']}", expanded=False):
                        st.text_area(
                            f"Extracted Text: {cand['name']}",
                            value=cand["parsed_text"][:2000] + ("\n... [truncated]" if len(cand["parsed_text"]) > 2000 else ""),
                            height=160,
                            disabled=True,
                            key=f"preview_text_{cand['id']}",
                        )
    else:
        st.info("ℹ️ No resumes uploaded yet. Click **Load 3 Sample Resumes** above, upload PDFs, or direct applicants to the **Candidate Portal**.")

st.markdown("---")

# --- Screening Action Controls & Live Execution ---
st.subheader("3. AI Evaluation Pipeline")

exec_col1, exec_col2 = st.columns([1, 2])

with exec_col1:
    run_screening = st.button("🚀 Run AI Candidate Screening", type="primary", use_container_width=True)

with exec_col2:
    demo_preview = st.button("✨ Load Demo Preview Data", use_container_width=False)

if demo_preview:
    # Inject realistic demo results for recruiter inspection
    st.session_state.analysis_results = [
        {
            "candidate_name": "Elena Rostova",
            "role": "Senior Full-Stack AI Engineer",
            "file_name": "Elena_Rostova_Resume.pdf",
            "match_score": 94,
            "recommendation": "Strong Hire",
            "matching_skills": ["Python", "FastAPI", "Gemini API", "Streamlit", "Pydantic", "Docker", "GCP"],
            "missing_skills": ["PostgreSQL (light exposure)"],
            "justification": "Exceptional fit. Elena exhibits deep expertise orchestrating Gemini API with structured Pydantic outputs, building scalable FastAPI backends, and deploying responsive Streamlit interfaces. She exceeds the required 4+ years of professional experience.",
            "estimated_experience_years": 5.5,
        },
        {
            "candidate_name": "Marcus Vance",
            "role": "Full-Stack Developer",
            "file_name": "Marcus_Vance_Resume.pdf",
            "match_score": 78,
            "recommendation": "Consider",
            "matching_skills": ["Python", "React", "Docker", "RESTful APIs", "SQL"],
            "missing_skills": ["Direct Gemini / GenAI SDK experience", "Pydantic structured output"],
            "justification": "Strong conventional full-stack background with robust React and Python capabilities. Lacks demonstrated hands-on engineering with LLM prompt engineering pipelines and structured AI outputs, but shows strong transferable skills.",
            "estimated_experience_years": 3.5,
        },
        {
            "candidate_name": "Aiden Chen",
            "role": "Junior Data Analyst",
            "file_name": "Aiden_Chen_Resume.pdf",
            "match_score": 48,
            "recommendation": "Reject",
            "matching_skills": ["Python (Pandas)", "SQL"],
            "missing_skills": ["FastAPI", "Modern Frontend (Streamlit/React)", "GenAI APIs", "Docker", "4+ Years Exp"],
            "justification": "Does not meet minimum seniority requirements (1.5 years experience vs 4+ required). Resume is heavily data analysis focused with limited web architecture and generative AI pipeline exposure.",
            "estimated_experience_years": 1.5,
        },
    ]
    for c in st.session_state.candidate_pool:
        c["screened"] = True
    st.rerun()

if run_screening:
    errors = []
    if not GEMINI_API_KEY:
        errors.append("`GEMINI_API_KEY` is missing in `.env`. Please configure your key.")
    if not st.session_state.job_description or len(st.session_state.job_description.strip()) < 30:
        errors.append("Job Description must be at least 30 characters long.")
    if not st.session_state.candidate_pool:
        errors.append("Candidate pool is empty. Please upload resumes or load the 3 sample resumes.")

    # Check that at least one candidate has parsed text
    readable_candidates = [c for c in st.session_state.candidate_pool if c.get("parsed_text")]
    if not readable_candidates and st.session_state.candidate_pool:
        errors.append("None of the candidates in the pool have extractable text. Please ensure valid text PDFs.")

    if errors:
        for err in errors:
            st.error(f"⚠️ {err}")
    else:
        # Live AI Execution with real-time Streamlit progress container
        with st.status("🤖 Running AI Resume Screening Engine...", expanded=True) as status_box:
            progress_bar = st.progress(0.0)
            status_ticker = st.empty()

            def update_progress(curr: int, total: int, cand_name: str):
                progress_pct = curr / total
                progress_bar.progress(progress_pct)
                status_ticker.markdown(
                    f"⚡ **Screening [{curr}/{total}]:** Evaluating `{cand_name}` against Job Description..."
                )

            # Invoke backend AI evaluation engine
            evaluated_batch = evaluate_candidate_batch(
                job_description=st.session_state.job_description,
                candidates=st.session_state.candidate_pool,
                progress_callback=update_progress,
            )

            # Store in session state
            st.session_state.analysis_results = evaluated_batch

            # Mark all candidates in pool as screened
            for c in st.session_state.candidate_pool:
                c["screened"] = True

            status_box.update(
                label=f"✅ Screening Complete! Evaluated {len(evaluated_batch)} candidate(s).",
                state="complete",
                expanded=False,
            )

        st.rerun()

# --- Results Presentation: Stylized Pandas Leaderboard & Expanders ---
st.markdown("---")
st.subheader("🏆 Candidate Leaderboard & Evaluation")

if st.session_state.analysis_results:
    # Sort results by match_score descending (highest to lowest)
    sorted_results = sorted(st.session_state.analysis_results, key=lambda x: x["match_score"], reverse=True)

    # 1. Build stylized Pandas DataFrame
    df_data = []
    for rank, cand in enumerate(sorted_results, start=1):
        df_data.append(
            {
                "Rank": f"#{rank}",
                "Candidate Name": cand.get("candidate_name", "Unknown"),
                "Match Score": cand["match_score"] / 100.0,
                "Score (%)": f"{cand['match_score']}%",
                "Hiring Verdict": cand.get("recommendation", "N/A"),
                "Experience": f"{cand.get('estimated_experience_years', 'N/A')} yrs"
                if cand.get("estimated_experience_years") is not None
                else "N/A",
                "Matching Skills": len(cand.get("matching_skills", [])),
                "Missing Skills": len(cand.get("missing_skills", [])),
                "Resume File": cand.get("file_name", "Resume.pdf"),
            }
        )

    leaderboard_df = pd.DataFrame(df_data)

    st.markdown("#### 📈 Ranked Candidate Standings")
    st.caption("Candidates ranked strictly from highest to lowest match score based on technical competence and role alignment.")

    # Render Stylized DataFrame
    st.dataframe(
        leaderboard_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Rank": st.column_config.TextColumn("Rank", width="small"),
            "Candidate Name": st.column_config.TextColumn("Candidate Name", width="medium"),
            "Match Score": st.column_config.ProgressColumn(
                "Match Score",
                help="Overall technical competence and alignment match score (0 - 100%)",
                format="%.0f%%",
                min_value=0.0,
                max_value=1.0,
            ),
            "Hiring Verdict": st.column_config.TextColumn("Verdict", width="small"),
            "Matching Skills": st.column_config.NumberColumn("Verified Skills", help="Count of confirmed matching skills"),
            "Missing Skills": st.column_config.NumberColumn("Skill Gaps", help="Count of required skills absent"),
            "Experience": st.column_config.TextColumn("Est. Exp", width="small"),
            "Resume File": st.column_config.TextColumn("File", width="medium"),
        },
    )

    # CSV Download Button
    csv_bytes = leaderboard_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Export Leaderboard as CSV",
        data=csv_bytes,
        file_name=f"candidate_leaderboard_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=False,
    )

    st.markdown("---")
    st.markdown("#### 🔍 Candidate Deep-Dive & Justifications")
    st.caption("Click on any candidate card below to inspect verified matching skills, missing skills, and the ruthless recruiter justification.")

    # 2. Render Rich Candidate Expanders
    for rank, cand in enumerate(sorted_results, start=1):
        score = cand["match_score"]
        recommendation = cand.get("recommendation", "Consider")

        # Color coding badges
        if score >= 85:
            badge_color = "#166534"
            badge_bg = "#DCFCE7"
            badge_border = "#86EFAC"
        elif score >= 65:
            badge_color = "#854D0E"
            badge_bg = "#FEF9C3"
            badge_border = "#FDE047"
        else:
            badge_color = "#991B1B"
            badge_bg = "#FEE2E2"
            badge_border = "#FCA5A5"

        expander_title = (
            f"#{rank} | {cand['candidate_name']} — Match Score: {score}%  [{recommendation}]"
        )

        with st.expander(expander_title, expanded=(rank == 1)):
            c_header, c_score = st.columns([3, 1])

            with c_header:
                exp_text = f" &bull; ⏳ Est. Exp: **{cand['estimated_experience_years']} yrs**" if cand.get("estimated_experience_years") else ""
                st.markdown(
                    f"**Role:** {cand.get('role', 'Candidate')} &bull; 📄 `{cand.get('file_name', 'Resume.pdf')}`{exp_text}"
                )

            with c_score:
                st.markdown(
                    f"""
                    <div style="text-align: right;">
                        <span style="background-color: {badge_bg}; color: {badge_color}; border: 1px solid {badge_border}; font-weight: 700; padding: 0.35rem 0.85rem; border-radius: 9999px; font-size: 0.9rem;">
                            Score: {score}/100 &bull; {recommendation}
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Score Progress Bar
            st.progress(score / 100)

            # Skills Breakdown Columns
            col_match, col_missing = st.columns(2)

            with col_match:
                st.markdown("##### ✅ Matching Skills (Verified in Resume)")
                matching_skills = cand.get("matching_skills", [])
                if matching_skills:
                    pills = " ".join(
                        [
                            f'<span style="background-color: #DCFCE7; color: #166534; border: 1px solid #BBF7D0; padding: 0.25rem 0.6rem; border-radius: 6px; font-size: 0.85rem; font-weight: 600; margin-right: 6px; display: inline-block; margin-bottom: 6px;">✓ {skill}</span>'
                            for skill in matching_skills
                        ]
                    )
                    st.markdown(pills, unsafe_allow_html=True)
                else:
                    st.caption("No direct matching skills verified against Job Description.")

            with col_missing:
                st.markdown("##### ⚠️ Missing Skills & Requirements Gaps")
                missing_skills = cand.get("missing_skills", [])
                if missing_skills:
                    pills = " ".join(
                        [
                            f'<span style="background-color: #FEE2E2; color: #991B1B; border: 1px solid #FECACA; padding: 0.25rem 0.6rem; border-radius: 6px; font-size: 0.85rem; font-weight: 600; margin-right: 6px; display: inline-block; margin-bottom: 6px;">✕ {skill}</span>'
                            for skill in missing_skills
                        ]
                    )
                    st.markdown(pills, unsafe_allow_html=True)
                else:
                    st.caption("No critical requirement gaps identified.")

            st.markdown("##### 📝 Ruthless Recruiter Justification & Assessment")
            st.markdown(cand.get("justification", "No justification provided."))

else:
    st.markdown(
        """
        <div class="metric-card" style="text-align: center; padding: 2.5rem 1rem;">
            <h4 style="color: #64748B; margin-bottom: 0.5rem;">No Screened Candidates Yet</h4>
            <p style="color: #94A3B8; max-width: 550px; margin: 0 auto; font-size: 0.95rem;">
                Click <strong>Load 3 Sample Resumes</strong> or upload PDFs, load a Job Description, 
                and click <strong>🚀 Run AI Candidate Screening</strong> to generate a real-time ranked leaderboard.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
