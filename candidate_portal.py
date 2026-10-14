"""Candidate application portal with persistent, secure resume storage."""

import logging
import re
from pathlib import Path

import streamlit as st

from database import save_resume
from utils import extract_text_from_pdf

logger = logging.getLogger(__name__)

MAX_UPLOAD_SIZE_MB = 10
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024


def _valid_email(email: str) -> bool:
    return bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email.strip()))


def render_candidate_portal(go_home) -> None:
    top_left, top_right = st.columns([5, 1])
    with top_left:
        st.markdown(
            '<div class="section-title">📤 Candidate Application Portal</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Submit your application once. Your resume and application metadata are stored "
            "persistently for authorized recruiter review."
        )
    with top_right:
        if st.button("← Home", width="stretch"):
            go_home()

    st.info(
        f"🔐 Your PDF is stored with a server-generated filename. "
        f"Only authenticated recruiters can access application records. "
        f"Maximum file size: **{MAX_UPLOAD_SIZE_MB} MB**."
    )

    with st.form("candidate_application_form", clear_on_submit=True):
        st.markdown("### 1. Applicant information")
        col1, col2 = st.columns(2, gap="large")
        with col1:
            candidate_name = st.text_input(
                "Full Name *", max_chars=120, placeholder="Jane Doe"
            )
            candidate_email = st.text_input(
                "Email Address *", max_chars=254, placeholder="jane.doe@example.com"
            )
        with col2:
            target_role = st.text_input(
                "Target Position / Role *", max_chars=160, placeholder="AI Engineer"
            )
            years_exp = st.number_input(
                "Professional Experience (years)",
                min_value=0.0,
                max_value=50.0,
                value=0.0,
                step=0.5,
            )

        st.markdown("### 2. Resume")
        uploaded_file = st.file_uploader(
            "Upload Resume (PDF only) *",
            type=["pdf"],
            accept_multiple_files=False,
            help=f"Text-selectable PDF only. Maximum {MAX_UPLOAD_SIZE_MB} MB.",
        )
        submitted = st.form_submit_button(
            "📨 Submit Application", type="primary", width="stretch"
        )

    if not submitted:
        return

    # ── Input validation ─────────────────────────────────────────────────────
    form_errors = []
    name = candidate_name.strip()
    email = candidate_email.strip().lower()
    role = target_role.strip()

    if len(name) < 2:
        form_errors.append("Please enter a valid full name (at least 2 characters).")
    if not _valid_email(email):
        form_errors.append("Please enter a valid email address.")
    if len(role) < 2:
        form_errors.append("Please specify the target position.")
    if uploaded_file is None:
        form_errors.append("Please upload a PDF resume.")
    elif uploaded_file.size > MAX_UPLOAD_SIZE_BYTES:
        form_errors.append(f"The uploaded file exceeds the {MAX_UPLOAD_SIZE_MB} MB limit.")

    if form_errors:
        for message in form_errors:
            st.error(f"⚠️ {message}")
        return

    # ── File type validation (magic bytes) ───────────────────────────────────
    file_bytes = uploaded_file.getvalue()
    if not file_bytes.startswith(b"%PDF") and b"%PDF-" not in file_bytes[:1024]:
        st.error("❌ The uploaded file does not appear to be a valid PDF.")
        return

    # ── PDF content extraction ────────────────────────────────────────────────
    with st.spinner("Validating your resume…"):
        parse_result = extract_text_from_pdf(file_bytes)

    if not parse_result.success:
        # parse_result.error is already sanitized in utils.py (no internal paths)
        st.error(f"❌ Resume validation failed: {parse_result.error}")
        return

    parse_status = "Clean" if not parse_result.is_scanned else "Warning: Low Text"
    if parse_result.is_scanned:
        # Show the user-facing warning (also already sanitized)
        st.warning(f"⚠️ {parse_result.error}")

    # ── Persist ───────────────────────────────────────────────────────────────
    try:
        with st.spinner("Securely storing your application…"):
            record = save_resume(
                name=name,
                email=email,
                target_role=role,
                years_exp=years_exp,
                original_filename=Path(uploaded_file.name).name,  # basename only
                file_bytes=file_bytes,
                page_count=parse_result.page_count,
                word_count=parse_result.word_count,
                parse_status=parse_status,
                source="candidate_portal",
            )
        st.success(
            f"🎉 Application submitted successfully for **{record['name']}**. "
            f"Your {parse_result.page_count}-page resume is now securely stored for recruiter review."
        )
        st.info(
            "You can close this page. Your application is no longer dependent on this browser session."
        )
    except Exception:
        logger.exception("Failed to save candidate application for email: %s", email)
        st.error("❌ We could not save your application due to a server error. Please try again later.")
