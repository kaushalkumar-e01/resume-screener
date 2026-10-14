"""Authenticated recruiter dashboard backed by SQLite persistence."""

import logging
from pathlib import Path
import uuid

import pandas as pd
import streamlit as st

from database import (
    add_screening,
    get_candidates,
    get_screening_results,
    get_stats,
    save_resume,
    delete_candidate,
    delete_all_candidates,
)
from screener import evaluate_candidate_batch
from utils import extract_text_from_pdf, get_setting, verify_recruiter_credentials

logger = logging.getLogger(__name__)

MAX_UPLOAD_SIZE_MB = 10
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

# Maximum consecutive failed login attempts before a temporary lockout (per session).
_MAX_LOGIN_ATTEMPTS = 5
_LOCKOUT_SECONDS = 300  # 5 minutes

SAMPLE_JD = """Role: Senior Full-Stack AI Engineer
Location: Remote

Responsibilities:
- Build, deploy, and scale web applications integrating Generative AI APIs.
- Architect robust backends with Python, FastAPI, and PostgreSQL.
- Develop responsive frontends using Streamlit, Next.js, or React.
- Implement structured output validation with Pydantic and prompt engineering pipelines.
- Integrate document processing such as PDF parsing and vector search.

Requirements:
- 4+ years of professional software engineering experience.
- Strong proficiency in Python, modern JavaScript/TypeScript, and RESTful APIs.
- Hands-on experience with LLM orchestration frameworks and structured JSON output.
- Familiarity with cloud deployment and containerization.
- Excellent technical communication and problem-solving skills."""


def _is_locked_out() -> bool:
    """Return True if the current session is under a login lockout."""
    import time
    lockout_until = st.session_state.get("login_lockout_until", 0)
    return time.time() < lockout_until


def _record_failed_attempt() -> None:
    """Increment the failed-login counter and apply a lockout when threshold is exceeded."""
    import time
    attempts = st.session_state.get("login_failed_attempts", 0) + 1
    st.session_state.login_failed_attempts = attempts
    if attempts >= _MAX_LOGIN_ATTEMPTS:
        st.session_state.login_lockout_until = time.time() + _LOCKOUT_SECONDS
        logger.warning("Recruiter login locked out after %d failed attempts.", attempts)


def _reset_login_counter() -> None:
    st.session_state.login_failed_attempts = 0
    st.session_state.pop("login_lockout_until", None)


def _login() -> bool:
    """Render the recruiter login form. Returns True only when authenticated."""
    if st.session_state.get("recruiter_authenticated"):
        return True

    st.markdown(
        '<div class="section-title" style="text-align:center;">🔐 Recruiter Sign In</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Authorized recruiter access only. "
        "Credentials are loaded from Streamlit Secrets or environment variables.",
        help="Do not hardcode credentials in source code.",
    )

    if _is_locked_out():
        import time
        remaining = int(st.session_state.get("login_lockout_until", 0) - time.time())
        st.error(
            f"🔒 Too many failed login attempts. Please wait {remaining // 60}m {remaining % 60}s before trying again."
        )
        return False

    _, center, _ = st.columns([1, 1.4, 1])
    with center:
        with st.form("recruiter_login", clear_on_submit=True):
            user_id = st.text_input("User ID", autocomplete="username", max_chars=120)
            password = st.text_input(
                "Password", type="password", autocomplete="current-password", max_chars=256
            )
            submitted = st.form_submit_button(
                "Sign in securely", type="primary", width="stretch"
            )

        if submitted:
            if not user_id.strip() or not password:
                st.error("❌ Please enter both User ID and Password.")
            elif verify_recruiter_credentials(user_id, password):
                _reset_login_counter()
                st.session_state.recruiter_authenticated = True
                st.success("✅ Authentication successful.")
                st.rerun()
            else:
                _record_failed_attempt()
                attempts = st.session_state.get("login_failed_attempts", 0)
                remaining_attempts = max(0, _MAX_LOGIN_ATTEMPTS - attempts)
                if remaining_attempts > 0:
                    st.error(
                        f"❌ Invalid User ID or password. "
                        f"{remaining_attempts} attempt(s) remaining before lockout."
                    )
                else:
                    st.error("🔒 Too many failed attempts. Access temporarily locked.")

        # Only show the credentials warning if neither hash nor plaintext password is configured.
        has_user = bool(get_setting("RECRUITER_USER_ID"))
        has_creds = bool(get_setting("RECRUITER_PASSWORD_HASH") or get_setting("RECRUITER_PASSWORD"))
        if not has_user or not has_creds:
            st.warning(
                "⚠️ Recruiter credentials are not fully configured. "
                "Add RECRUITER_USER_ID and RECRUITER_PASSWORD_HASH to Streamlit Secrets before deployment."
            )

    return False


def _load_db_candidates() -> list[dict]:
    """Load candidate records from DB and re-parse their stored PDFs for resume text."""
    records = get_candidates()
    candidates = []
    base_dir = Path(__file__).resolve().parent
    for record in records:
        path = base_dir / record["file_path"]
        parse_result = extract_text_from_pdf(path)
        
        # Handle missing or unreadable files gracefully
        if not path.exists():
            parse_status = "Error: File Missing"
        elif not parse_result.success:
            parse_status = f"Error: {parse_result.error or 'Unreadable'}"
        else:
            parse_status = record.get("parse_status", "Clean")

        candidates.append(
            {
                "id": record["id"],
                "name": record["name"],
                "email": record["email"],
                "role": record["target_role"],
                "years_exp": record["years_exp"],
                "file_name": record["original_filename"],
                # Do NOT expose full filesystem path; only keep relative info.
                "file_size_kb": round(record["file_size_bytes"] / 1024, 1),
                "parsed_text": parse_result.text if parse_result.success else "",
                "page_count": parse_result.page_count,
                "word_count": parse_result.word_count,
                "parse_status": parse_status,
                "submitted_at": record["created_at"],
            }
        )
    return candidates


def _save_direct_upload(uploaded, source: str) -> bool:
    """Validate and persist a recruiter-uploaded PDF."""
    if uploaded.size > MAX_UPLOAD_SIZE_BYTES:
        st.error(f"⚠️ `{Path(uploaded.name).name}` exceeds the {MAX_UPLOAD_SIZE_MB} MB limit.")
        return False
    raw = uploaded.getvalue()
    if not raw.startswith(b"%PDF") and b"%PDF-" not in raw[:1024]:
        st.error(f"⚠️ `{Path(uploaded.name).name}` is not a valid PDF.")
        return False
    parsed = extract_text_from_pdf(raw)
    if not parsed.success:
        st.error(f"⚠️ Could not parse `{Path(uploaded.name).name}`: {parsed.error}")
        return False

    # Use a random internal email so batch uploads don't collide with each other or
    # with genuine candidate portal submissions.
    internal_email = f"{uuid.uuid4()}@batch.internal"
    # Derive a display name from the filename, safely.
    display_name = Path(uploaded.name).stem.replace("_", " ").replace("-", " ").title()[:120]
    try:
        save_resume(
            name=display_name,
            email=internal_email,
            target_role="Direct Recruiter Upload",
            years_exp=0,
            original_filename=Path(uploaded.name).name,
            file_bytes=raw,
            page_count=parsed.page_count,
            word_count=parsed.word_count,
            parse_status="Clean" if not parsed.is_scanned else "Warning: Low Text",
            source=source,
        )
        return True
    except Exception:
        logger.exception("Failed to persist direct upload: %s", Path(uploaded.name).name)
        st.error(f"❌ Could not store `{Path(uploaded.name).name}`. Please try again.")
        return False


def render_recruiter_dashboard(go_home) -> None:
    # Authentication gate — must be first, cannot be bypassed.
    if not _login():
        if st.button("← Back to Home", width="stretch"):
            go_home()
        return

    # ── Header ──────────────────────────────────────────────────────────────
    top_left, top_mid, top_right = st.columns([5, 2, 1])
    with top_left:
        st.markdown(
            '<div class="section-title">📋 Recruiter Command Center</div>',
            unsafe_allow_html=True,
        )
        st.caption("Persistent applicant management and AI-assisted resume analysis.")
    with top_mid:
        st.caption("Authenticated recruiter")
        st.success("● Secure session")
    with top_right:
        if st.button("Logout", width="stretch"):
            st.session_state.recruiter_authenticated = False
            st.session_state.view = "home"
            _reset_login_counter()
            st.rerun()

    # ── Stats Row ────────────────────────────────────────────────────────────
    stats = get_stats()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Applicants", stats["total"])
    c2.metric("Screened", stats["screened"])
    c3.metric("Top Match", f"{stats['top_score']}%" if stats["top_score"] is not None else "—")
    c4.metric("Average Score", f"{stats['average_score']}%" if stats["average_score"] is not None else "—")

    st.markdown("---")

    # ── Job Description + Upload ─────────────────────────────────────────────
    col_jd, col_upload = st.columns(2, gap="large")

    with col_jd:
        st.markdown("### 1. Job Description")
        if "job_description" not in st.session_state:
            st.session_state.job_description = ""
        if st.button("Load sample JD", width="stretch"):
            st.session_state.job_description = SAMPLE_JD
            st.rerun()
        jd = st.text_area(
            "Target requirements",
            value=st.session_state.job_description,
            height=310,
            placeholder="Paste the role description and requirements…",
        )
        st.session_state.job_description = jd
        word_count = len(jd.split()) if jd.strip() else 0
        st.caption(f"{word_count} words · {len(jd)} characters")

    with col_upload:
        st.markdown("### 2. Manual Resume Upload")
        st.caption(
            "Candidates applying through the portal are added automatically. "
            "Use this tool to manually upload resumes received via email or external referrals."
        )
        direct_files = st.file_uploader(
            "Batch upload PDFs",
            type=["pdf"],
            accept_multiple_files=True,
            key="recruiter_uploads",
        )

        if direct_files:
            added = 0
            # Deduplicate by stored filename — more reliable than original_filename
            existing_names = {c["original_filename"] for c in get_candidates()}
            for uploaded in direct_files:
                safe_name = Path(uploaded.name).name
                if safe_name in existing_names:
                    st.info(f"ℹ️ `{safe_name}` is already stored; skipped duplicate.")
                    continue
                if _save_direct_upload(uploaded, "recruiter_batch"):
                    existing_names.add(safe_name)
                    added += 1
            if added:
                st.success(f"✅ Stored {added} new resume(s).")
                st.rerun()

    st.markdown("---")

    # ── Candidate List ───────────────────────────────────────────────────────
    candidates = _load_db_candidates()
    if not candidates:
        st.info("No applications have been stored yet. Candidate submissions will appear here automatically.")
        return

    # ── Candidate Management ─────────────────────────────────────────────────
    st.markdown("### ⚙️ Candidate Management")
    m_col1, m_col2 = st.columns([3, 1])

    with m_col1:
        candidate_options = {c["id"]: f"{c['name']} ({c['file_name']})" for c in candidates}
        selected_id = st.selectbox(
            "Select a candidate to remove:",
            options=[None] + list(candidate_options.keys()),
            format_func=lambda x: candidate_options[x] if x else "Choose a candidate…",
        )

        if selected_id:
            if st.button("🗑️ Delete Selected Candidate"):
                cand_name = candidate_options.get(selected_id, "Candidate")
                success = delete_candidate(selected_id)
                if success:
                    st.success(f"✅ Deleted {cand_name.split(' (')[0]} from database and storage.")
                else:
                    st.warning("Candidate not found — may have already been deleted.")
                st.rerun()

    with m_col2:
        st.write("")
        st.write("")
        if st.button("🚨 Delete ALL Candidates", type="primary", width="stretch"):
            delete_all_candidates()
            st.success("✅ All records and files removed.")
            st.rerun()

    st.markdown("---")

    # ── AI Evaluation Pipeline ───────────────────────────────────────────────
    st.markdown("### 3. AI Evaluation Pipeline")
    run_screening = st.button("🤖 Run AI Screening", type="primary", width="stretch")

    if run_screening:
        validation_errors = []
        if len(st.session_state.get("job_description", "").strip()) < 30:
            validation_errors.append("Job Description must contain at least 30 characters.")
        readable = [c for c in candidates if c.get("parsed_text")]
        if not readable:
            validation_errors.append("No stored resumes currently contain readable text.")
        if validation_errors:
            for err in validation_errors:
                st.error(f"⚠️ {err}")
        else:
            with st.status("🤖 Running AI Resume Screening…", expanded=True) as status:
                progress = st.progress(0.0)
                ticker = st.empty()

                def update_progress(curr, total, name):
                    progress.progress(curr / total)
                    ticker.write(f"Screening {curr}/{total}: {name}")

                try:
                    results = evaluate_candidate_batch(
                        job_description=st.session_state.job_description,
                        candidates=readable,
                        progress_callback=update_progress,
                    )
                    saved = 0
                    for result in results:
                        add_screening(
                            candidate_id=result["candidate_id"],
                            job_description=st.session_state.job_description,
                            match_score=result.get("match_score", 0),
                            recommendation=result.get("recommendation", "Unclassified"),
                            matching_skills=result.get("matching_skills", []),
                            missing_skills=result.get("missing_skills", []),
                            justification=result.get("justification", ""),
                            estimated_experience_years=result.get("estimated_experience_years"),
                            status=result.get("status", "Unknown"),
                        )
                        saved += 1
                    successful = sum(1 for r in results if r.get("status") == "Success")
                    failed = len(results) - successful
                    if failed == 0:
                        status.update(
                            label=f"✅ Screening complete. Persisted {saved} evaluation(s).",
                            state="complete",
                            expanded=False,
                        )
                        st.success("All screening results have been written to the database and will survive page refreshes.")
                    elif successful > 0:
                        status.update(
                            label=f"⚠️ Screening partially complete: {successful} succeeded, {failed} failed.",
                            state="complete",
                            expanded=False,
                        )
                        st.warning(f"Screening partially complete: {successful} succeeded, {failed} failed. See candidate cards below.")
                    else:
                        status.update(
                            label=f"❌ Screening failed for all {failed} candidate(s).",
                            state="error",
                            expanded=True,
                        )
                        st.error("All candidate evaluations failed. Check candidate details below for diagnostic error details.")
                except Exception:
                    logger.exception("AI screening batch failed.")
                    status.update(label="❌ Screening failed.", state="error", expanded=False)
                    st.error(
                        "AI screening encountered an error. Please check your API key is configured "
                        "correctly and try again."
                    )
                    return
            st.rerun()

    st.markdown("---")

    # ── Candidate Leaderboard ────────────────────────────────────────────────
    st.markdown("### 4. Candidate Leaderboard")
    results = get_screening_results()
    screened_results = [r for r in results if r.get("screening_status")]

    if screened_results:
        table = pd.DataFrame(
            [
                {
                    "Candidate": r["name"],
                    "Role": r["target_role"],
                    "Score": r["match_score"] / 100,
                    "Verdict": r["recommendation"],
                    "Experience": (
                        f"{r['estimated_experience_years']} yrs"
                        if r.get("estimated_experience_years") is not None
                        else "—"
                    ),
                    "Resume": r["original_filename"],
                    "Screened At": r["screened_at"],
                }
                for r in screened_results
            ]
        )
        st.dataframe(
            table,
            width="stretch",
            hide_index=True,
            column_config={
                "Score": st.column_config.ProgressColumn(
                    "Match Score", min_value=0, max_value=1, format="%.0f%%"
                ),
                "Candidate": st.column_config.TextColumn(width="medium"),
                "Role": st.column_config.TextColumn(width="medium"),
            },
        )
        st.download_button(
            "📥 Export CSV",
            table.to_csv(index=False).encode(),
            "candidate_leaderboard.csv",
            "text/csv",
        )

        st.markdown("### Candidate Details")
        for rank, r in enumerate(screened_results, start=1):
            is_success = r.get("screening_status") == "Success"
            status_badge = f"{r['match_score']}% · {r['recommendation']}" if is_success else f"⚠️ Failed ({r.get('screening_status', 'Error')})"
            with st.expander(
                f"#{rank} · {r['name']} · {status_badge}",
                expanded=rank == 1,
            ):
                info1, info2 = st.columns(2)
                with info1:
                    st.write(f"**Role:** {r['target_role']}")
                    st.write(f"**Resume:** `{r['original_filename']}`")
                    st.write(f"**Submitted:** {r['created_at']}")
                with info2:
                    st.metric("Match Score", f"{r['match_score']}%")
                    st.progress(r["match_score"] / 100)
                match_col, missing_col = st.columns(2)
                with match_col:
                    st.markdown("**✅ Matching skills**")
                    st.write(", ".join(r["matching_skills"]) if r["matching_skills"] else "None identified")
                with missing_col:
                    st.markdown("**⚠️ Missing skills / gaps**")
                    st.write(", ".join(r["missing_skills"]) if r["missing_skills"] else "None identified")
                st.markdown("**📝 AI assessment**")
                st.write(r["justification"])
    else:
        st.info(
            "Applications are stored and ready. "
            "Add a Job Description above and run AI Screening to generate persistent evaluations."
        )

    st.caption(f"Persistent records: {len(candidates)} · SQLite database: local application storage")