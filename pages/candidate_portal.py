"""
Candidate Portal — Resume Submission Page
Allows candidates to upload resumes and submit their application.
Enforces a strict 10MB maximum file size limit.
"""

from datetime import datetime
import streamlit as st
from utils import extract_text_from_pdf

MAX_UPLOAD_SIZE_MB = 10
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

# Page Header
st.markdown('<div class="main-header">📤 Candidate Application Portal</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Submit your application and resume to be evaluated by our AI screening system.</div>',
    unsafe_allow_html=True,
)

# Information Card
with st.container():
    st.info(
        "💡 **Instructions:** Please fill in your contact information and upload your resume in PDF format. "
        f"Maximum allowed file size is strictly **{MAX_UPLOAD_SIZE_MB}MB**."
    )

# Application Submission Form
with st.form("candidate_application_form", clear_on_submit=False):
    st.subheader("1. Applicant Information")
    col1, col2 = st.columns(2)

    with col1:
        candidate_name = st.text_input(
            "Full Name *",
            placeholder="e.g. Jane Doe",
            help="Your legal full name as shown on your resume.",
        )
        candidate_email = st.text_input(
            "Email Address *",
            placeholder="e.g. jane.doe@example.com",
            help="We will use this email for interview updates.",
        )

    with col2:
        target_role = st.text_input(
            "Target Position / Role *",
            placeholder="e.g. Senior AI Engineer",
            help="The position you are applying for.",
        )
        years_exp = st.number_input(
            "Years of Professional Experience",
            min_value=0,
            max_value=50,
            value=3,
            step=1,
        )

    st.markdown("---")
    st.subheader("2. Resume Upload")

    uploaded_file = st.file_uploader(
        f"Upload Resume (PDF format, max {MAX_UPLOAD_SIZE_MB}MB) *",
        type=["pdf"],
        accept_multiple_files=False,
        help=f"Only PDF files are accepted. Max upload size is strictly {MAX_UPLOAD_SIZE_MB}MB.",
    )

    # Submission Trigger
    submit_button = st.form_submit_button("📨 Submit Application", type="primary", use_container_width=True)

if submit_button:
    validation_passed = True
    errors = []

    # Field validations
    if not candidate_name.strip():
        errors.append("Please enter your Full Name.")
        validation_passed = False

    if not candidate_email.strip() or "@" not in candidate_email:
        errors.append("Please enter a valid Email Address.")
        validation_passed = False

    if not target_role.strip():
        errors.append("Please specify the Target Position.")
        validation_passed = False

    if uploaded_file is None:
        errors.append("Please upload your PDF resume.")
        validation_passed = False
    elif uploaded_file.size > MAX_UPLOAD_SIZE_BYTES:
        size_mb = uploaded_file.size / (1024 * 1024)
        errors.append(
            f"Uploaded file '{uploaded_file.name}' is {size_mb:.2f}MB, which exceeds the {MAX_UPLOAD_SIZE_MB}MB limit."
        )
        validation_passed = False

    if not validation_passed:
        for err in errors:
            st.error(f"⚠️ {err}")
    else:
        # Pre-screen PDF text extraction
        with st.spinner("Analyzing and parsing resume document..."):
            parse_result = extract_text_from_pdf(uploaded_file)

        if not parse_result.success:
            st.error(f"❌ **Invalid Resume Document:** {parse_result.error}")
            st.info("💡 Please ensure your resume is an unlocked, standard text PDF (not an encrypted or corrupted file).")
        else:
            if parse_result.is_scanned:
                st.warning(f"⚠️ **Notice:** {parse_result.error}")

            # Save resume into session_state candidate pool
            file_bytes = uploaded_file.getvalue()
            submission_record = {
                "id": f"cand-{len(st.session_state.candidate_pool) + 1:03d}",
                "name": candidate_name.strip(),
                "email": candidate_email.strip(),
                "role": target_role.strip(),
                "years_exp": years_exp,
                "file_name": uploaded_file.name,
                "file_size_kb": round(uploaded_file.size / 1024, 1),
                "file_bytes": file_bytes,
                "parsed_text": parse_result.text,
                "page_count": parse_result.page_count,
                "word_count": parse_result.word_count,
                "parse_status": "Clean" if not parse_result.is_scanned else "Warning: Low Text",
                "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "screened": False,
            }

            # Check for duplicates by email
            existing_index = next(
                (idx for idx, c in enumerate(st.session_state.candidate_pool) if c["email"] == submission_record["email"]),
                None,
            )

            if existing_index is not None:
                st.session_state.candidate_pool[existing_index] = submission_record
                st.success(
                    f"🔄 Application updated for **{candidate_name}**! "
                    f"Extracted **{parse_result.word_count}** words across **{parse_result.page_count}** page(s)."
                )
            else:
                st.session_state.candidate_pool.append(submission_record)
                st.success(
                    f"🎉 Application submitted successfully for **{candidate_name}**! "
                    f"Extracted **{parse_result.word_count}** words across **{parse_result.page_count}** page(s). "
                    f"Your profile is now in the recruiter screening pool."
                )

# Current submissions overview
if st.session_state.candidate_pool:
    st.markdown("---")
    st.subheader("📋 Applications Registered in Current Session")
    st.caption("These applications are immediately visible on the Recruiter Dashboard for AI screening.")

    for cand in st.session_state.candidate_pool:
        status_badge = "✅ Screened" if cand.get("screened") else "⏳ Pending Review"
        stats_info = f" • 📑 {cand.get('page_count', 1)}p / {cand.get('word_count', 0)} words" if 'word_count' in cand else ""
        with st.container():
            st.markdown(
                f"""
                <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>{cand['name']}</strong> ({cand['email']}) &bull; <em>{cand['role']}</em> &bull; 📄 <code>{cand['file_name']}</code> ({cand['file_size_kb']} KB){stats_info}
                    </div>
                    <div>
                        <span style="background-color: #E2E8F0; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.8rem; font-weight: 600;">{status_badge}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
