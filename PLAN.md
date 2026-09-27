# AI Resume Screening System - Architecture Plan

## 1. Overview
Build a web-based AI Resume Screening System that accepts a Job Description and multiple candidate resumes (PDFs), analyzes them using an LLM, and outputs a ranked leaderboard of candidates based on their match score.

## 2. Tech Stack
- **Language:** Python 3.11+
- **Frontend/UI:** Streamlit (for rapid, modern AI web interfaces)
- **PDF Extraction:** `PyPDF2` or `pdfplumber`
- **AI Integration:** Google GenAI SDK (Gemini API)
- **Data Handling:** Pandas (for displaying the leaderboard in a clean table)

## 3. Core User Flow
1. User opens the app and sees two input sections: a text box for the "Job Description" and a file uploader for "Candidate Resumes" (accepts multiple PDFs).
2. User clicks "Analyze Candidates".
3. The backend extracts text from all PDFs.
4. The system loops through each resume, sending a structured prompt to the Gemini API containing the JD and the candidate's text.
5. The AI returns a JSON object with: `candidate_name`, `match_score` (0-100), `matching_skills`, `missing_skills`, and a `brief_justification`.
6. The UI updates to show a leaderboard table ranked by `match_score` descending.

## 4. Execution Phases (Agent Task List)
**Phase 1: Setup & Basic UI**
- Initialize a Python virtual environment and install dependencies (`streamlit`, `PyPDF2`, `google-genai`, `pandas`, `pydantic`).
- Create `app.py` with a clean Streamlit interface layout (Sidebar for API Key, main area for JD text input and file uploader).

**Phase 2: PDF Parsing Logic**
- Create a helper function in `utils.py` that takes uploaded Streamlit file objects and extracts clean text from them.
- Add error handling for unreadable PDFs.

**Phase 3: AI Evaluation Engine**
- Implement the Gemini API call using Pydantic structured outputs to ensure the AI strictly returns JSON with the required fields (`score`, `skills`, `justification`).
- Write a highly specific system prompt instructing the AI to act as a ruthless technical recruiter.

**Phase 4: Dashboard Integration**
- Connect the UI to the backend logic.
- Display the AI's JSON output as a stylized Pandas dataframe (Leaderboard).
- Add an expander for each candidate so the user can click to read the `brief_justification`.