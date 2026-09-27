"""
AI Resume Screening & Candidate Ranking System
Root Multipage Orchestrator using st.navigation and st.Page
"""

import os
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Global Page Configuration
st.set_page_config(
    page_title="AI Resume Screener",
    page_icon="logo.ico",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Shared Global Styling
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.1rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.25rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    div[data-testid="stMetric"] {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        padding: 0.75rem 1rem;
        border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Shared Global State Initialization
if "candidate_pool" not in st.session_state:
    st.session_state.candidate_pool = []
if "job_description" not in st.session_state:
    st.session_state.job_description = ""
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = []

# Define Modern Multipage Navigation
recruiter_page = st.Page(
    "pages/recruiter_dashboard.py",
    title="Recruiter Dashboard",
    icon="📊",
    default=True,
)

candidate_page = st.Page(
    "pages/candidate_portal.py",
    title="Candidate Portal",
    icon="📤",
)

# Render Navigation
pg = st.navigation(
    {
        "Navigation": [recruiter_page, candidate_page],
    }
)

# Sidebar System Footer
with st.sidebar:
    st.markdown("---")
    st.caption("🎯 **AI Resume Screener**")
    st.caption("🔒 Environment: `.env` Protected")
    st.caption("⚡ Streamlit 1.38+ Multipage Architecture")

# Run Current Page
pg.run()
