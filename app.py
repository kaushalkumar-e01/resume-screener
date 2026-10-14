"""Main router and polished landing page for the AI Resume Screener."""
import os
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

from database import ensure_storage
from candidate_portal import render_candidate_portal
from recruiter_dashboard import render_recruiter_dashboard

st.set_page_config(
    page_title="AI Resume Screener",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed",
)

ensure_storage()

for key, value in {
    "view": "home",
    "recruiter_authenticated": False,
}.items():
    st.session_state.setdefault(key, value)

st.markdown(
    """
    <style>
    :root { --ink:#0f172a; --muted:#64748b; --line:#e2e8f0; --brand:#2563eb; --brand2:#7c3aed; }
    .stApp { background: radial-gradient(circle at 10% 0%, #eef5ff 0, #f8fafc 38%, #ffffff 100%); }
    .block-container { max-width: 1250px; padding-top: 2rem; padding-bottom: 3rem; }
    .hero { padding: 3.2rem 1rem 2rem; text-align:center; }
    .eyebrow { display:inline-block; padding:.35rem .75rem; border:1px solid #dbeafe; border-radius:999px; background:#eff6ff; color:#1d4ed8; font-weight:700; font-size:.82rem; }
    .hero h1 { font-size: clamp(2.25rem, 5vw, 4.6rem); line-height:1.02; letter-spacing:-.055em; margin:.9rem auto .9rem; color:var(--ink); max-width:900px; }
    .hero p { color:var(--muted); font-size:clamp(1rem, 2vw, 1.2rem); max-width:760px; margin:0 auto; line-height:1.7; }
    .portal-card { min-height:285px; padding:1.8rem; border:1px solid rgba(226,232,240,.95); border-radius:24px; background:rgba(255,255,255,.9); box-shadow:0 18px 45px rgba(15,23,42,.08); margin-bottom:.75rem; }
    .portal-icon { font-size:2.4rem; }
    .portal-card h2 { margin:.7rem 0 .5rem; color:var(--ink); font-size:1.45rem; }
    .portal-card p { color:var(--muted); min-height:65px; line-height:1.55; }
    .trust-row { text-align:center; color:#64748b; margin-top:1.7rem; font-size:.9rem; }
    .topbar { display:flex; justify-content:space-between; align-items:center; gap:1rem; margin-bottom:1.5rem; }
    .section-title { color:var(--ink); font-size:1.8rem; font-weight:800; letter-spacing:-.025em; }
    div[data-testid="stMetric"] { background:rgba(255,255,255,.85); border:1px solid var(--line); border-radius:16px; padding:1rem; }
    div[data-testid="stForm"] { border:1px solid var(--line); border-radius:20px; padding:1.25rem; background:rgba(255,255,255,.88); }
    @media (max-width: 700px) {
      .block-container { padding:1rem .8rem 2rem; }
      .hero { padding:2rem .2rem 1.2rem; }
      .portal-card { min-height:0; padding:1.25rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def go_home() -> None:
    st.session_state.view = "home"
    st.session_state.recruiter_authenticated = False
    st.rerun()


def landing_page() -> None:
    st.markdown(
        """
        <section class="hero">
          <span class="eyebrow">AI-POWERED RECRUITMENT WORKSPACE</span>
          <h1>Screen resumes faster. Make every profile easier to review.</h1>
          <p>Securely collect candidate applications and give recruiters a focused workspace for AI-assisted resume analysis, matching, and review.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown(
            """
            <div class="portal-card">
            <div class="portal-icon"></div>
              <h2>Candidate Portal</h2>
              <p>Submit your profile, target role, and PDF resume through a clean application flow. Your application is stored securely for recruiter review.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Continue as Candidate →", width="stretch", type="primary"):
            st.session_state.view = "candidate"
            st.rerun()

    with right:
        st.markdown(
            """
            <div class="portal-card">
            <div class="portal-icon"></div>
              <h2>Recruiter Workspace</h2>
              <p>Sign in to manage applications, define job requirements, run AI-assisted screening, and review persistent candidate results.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Enter Recruiter Workspace →", width="stretch"):
            st.session_state.view = "recruiter"
            st.rerun()

    st.markdown('<div class="trust-row">🔐 Credentials stay outside source code &nbsp;•&nbsp; 💾 SQLite persistence &nbsp;•&nbsp; 📄 PDF validation</div>', unsafe_allow_html=True)


if st.session_state.view == "candidate":
    render_candidate_portal(go_home)
elif st.session_state.view == "recruiter":
    render_recruiter_dashboard(go_home)
else:
    landing_page()
