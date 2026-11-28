"""FastAPI REST adapter connecting the React frontend to the existing Python backend."""

import logging
import re
import secrets
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

load_dotenv()

from validation import (
    COUNTRY_PHONE_META,
    MAX_UPLOAD_SIZE_BYTES,
    MAX_UPLOAD_SIZE_MB,
    SAMPLE_JD,
    TECHNICAL_ROLES,
    valid_email,
    validate_full_name,
    validate_phone_number,
)
from database import (
    add_screening,
    delete_all_candidates,
    delete_candidate,
    ensure_storage,
    get_candidates,
    get_screening_results,
    get_stats,
    save_resume,
)
from email_verification import (
    consume_verification,
    is_email_verified,
    issue_otp,
    normalize_email,
    sync_email_change,
    verify_otp,
)
from screener import evaluate_candidate_batch
from utils import extract_text_from_pdf, verify_recruiter_credentials

logger = logging.getLogger(__name__)

app = FastAPI(title="AI Resume Screener API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ensure_storage()

_AUTH_LOCK = threading.Lock()
_RECRUITER_TOKENS: Dict[str, float] = {}
_TOKEN_TTL_SECONDS = 8 * 3600
_MAX_LOGIN_ATTEMPTS = 5
_LOCKOUT_SECONDS = 300
_LOGIN_ATTEMPTS = {"count": 0, "lockout_until": 0.0}


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "An internal server error occurred."})


async def _read_upload_bounded(upload: UploadFile, max_bytes: int) -> bytes:
    """Read an uploaded file in chunks and abort early if it exceeds max_bytes."""
    chunks: List[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"The uploaded file exceeds the {MAX_UPLOAD_SIZE_MB} MB limit.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _sanitize_pdf_filename(raw_name: Optional[str]) -> str:
    """Extract safe basename, strip control characters, and verify .pdf extension."""
    base = Path(raw_name or "resume.pdf").name
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", base).strip()
    if not cleaned.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only .pdf files are accepted.")
    return cleaned


class OtpRequest(BaseModel):
    session_id: str
    email: str


class OtpVerifyRequest(BaseModel):
    session_id: str
    email: str
    otp: str


class RecruiterLoginRequest(BaseModel):
    user_id: str
    password: str


class ScreeningRequest(BaseModel):
    job_description: str


def _require_recruiter(authorization: Optional[str] = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Recruiter authentication required.")
    token = authorization.split(" ", 1)[1].strip()
    now = time.time()
    with _AUTH_LOCK:
        expired = [t for t, exp in _RECRUITER_TOKENS.items() if now > exp]
        for t in expired:
            _RECRUITER_TOKENS.pop(t, None)
        expires_at = _RECRUITER_TOKENS.get(token)
        if not expires_at or now > expires_at:
            _RECRUITER_TOKENS.pop(token, None)
            raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    return token


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/candidate/config")
def candidate_config() -> dict:
    return {
        "technical_roles": TECHNICAL_ROLES,
        "country_phone_meta": COUNTRY_PHONE_META,
        "max_upload_size_mb": MAX_UPLOAD_SIZE_MB,
    }


@app.post("/api/candidate/sync-email")
def candidate_sync_email(payload: OtpRequest) -> dict:
    normalized = normalize_email(payload.email)
    sync_email_change(payload.session_id, normalized)
    return {"verified": is_email_verified(payload.session_id, normalized)}


@app.post("/api/candidate/send-otp")
def candidate_send_otp(payload: OtpRequest) -> dict:
    normalized = normalize_email(payload.email)
    if not valid_email(normalized):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")
    sync_email_change(payload.session_id, normalized)
    ok, msg = issue_otp(payload.session_id, normalized)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@app.post("/api/candidate/verify-otp")
def candidate_verify_otp(payload: OtpVerifyRequest) -> dict:
    normalized = normalize_email(payload.email)
    ok, msg = verify_otp(payload.session_id, normalized, payload.otp)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "verified": True, "message": msg}


@app.post("/api/candidate/submit")
async def candidate_submit(
    session_id: str = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    region_code: str = Form("IN"),
    phone: str = Form(...),
    target_role: str = Form(...),
    years_exp: float = Form(0.0),
    confirm_adult: bool = Form(False),
    resume: UploadFile = File(...),
) -> dict:
    if not confirm_adult:
        raise HTTPException(
            status_code=400,
            detail="You must confirm that you are at least 18 years old and accept the Privacy Policy and Terms.",
        )

    name_ok, normalized_name, name_err = validate_full_name(name)
    if not name_ok:
        raise HTTPException(status_code=400, detail=name_err)

    normalized_email = normalize_email(email)
    if not valid_email(normalized_email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")
    if not is_email_verified(session_id, normalized_email):
        raise HTTPException(
            status_code=403,
            detail="Please verify your email address using the 4-digit OTP before submitting.",
        )

    phone_ok, e164_phone, phone_err = validate_phone_number(region_code, phone)
    if not phone_ok:
        raise HTTPException(status_code=400, detail=phone_err)

    role = (target_role or "").strip()
    if role not in TECHNICAL_ROLES:
        raise HTTPException(status_code=400, detail="Please select a valid target position from the list.")

    if years_exp < 0 or years_exp > 50 or round(years_exp * 2) != years_exp * 2:
        raise HTTPException(
            status_code=400,
            detail="Professional experience must be between 0 and 50 years in 0.5-year increments.",
        )

    safe_filename = _sanitize_pdf_filename(resume.filename)
    file_bytes = await _read_upload_bounded(resume, MAX_UPLOAD_SIZE_BYTES)
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Please upload a PDF resume.")
    if not file_bytes.startswith(b"%PDF") and b"%PDF-" not in file_bytes[:1024]:
        raise HTTPException(status_code=400, detail="The uploaded file does not appear to be a valid PDF.")

    parse_result = extract_text_from_pdf(file_bytes)
    if not parse_result.success:
        raise HTTPException(status_code=400, detail=f"Resume validation failed: {parse_result.error}")

    parse_status = "Clean" if not parse_result.is_scanned else "Warning: Low Text"
    record = save_resume(
        name=normalized_name,
        email=normalized_email,
        phone=e164_phone,
        target_role=role,
        years_exp=years_exp,
        original_filename=safe_filename,
        file_bytes=file_bytes,
        page_count=parse_result.page_count,
        word_count=parse_result.word_count,
        parse_status=parse_status,
        source="candidate_portal",
    )
    consume_verification(session_id, normalized_email)

    return {
        "ok": True,
        "candidate_name": record["name"],
        "page_count": parse_result.page_count,
        "is_scanned": parse_result.is_scanned,
        "warning": parse_result.error if parse_result.is_scanned else None,
    }


@app.post("/api/recruiter/login")
def recruiter_login(payload: RecruiterLoginRequest) -> dict:
    now = time.time()
    with _AUTH_LOCK:
        if now < _LOGIN_ATTEMPTS["lockout_until"]:
            remaining = int(_LOGIN_ATTEMPTS["lockout_until"] - now)
            raise HTTPException(
                status_code=429,
                detail=f"Too many failed attempts. Wait {remaining // 60}m {remaining % 60}s.",
            )
    if not payload.user_id.strip() or not payload.password:
        raise HTTPException(status_code=400, detail="Please enter both User ID and Password.")

    if verify_recruiter_credentials(payload.user_id, payload.password):
        token = secrets.token_urlsafe(32)
        with _AUTH_LOCK:
            _LOGIN_ATTEMPTS["count"] = 0
            _LOGIN_ATTEMPTS["lockout_until"] = 0.0
            _RECRUITER_TOKENS[token] = now + _TOKEN_TTL_SECONDS
        return {"ok": True, "token": token}

    with _AUTH_LOCK:
        _LOGIN_ATTEMPTS["count"] += 1
        if _LOGIN_ATTEMPTS["count"] >= _MAX_LOGIN_ATTEMPTS:
            _LOGIN_ATTEMPTS["lockout_until"] = now + _LOCKOUT_SECONDS
            raise HTTPException(status_code=429, detail="Too many failed attempts. Access temporarily locked.")
        remaining_attempts = max(0, _MAX_LOGIN_ATTEMPTS - _LOGIN_ATTEMPTS["count"])
    raise HTTPException(
        status_code=401,
        detail=f"Invalid User ID or password. {remaining_attempts} attempt(s) remaining.",
    )


@app.post("/api/recruiter/logout")
def recruiter_logout(token: str = Depends(_require_recruiter)) -> dict:
    with _AUTH_LOCK:
        _RECRUITER_TOKENS.pop(token, None)
    return {"ok": True}


@app.get("/api/recruiter/session")
def recruiter_session(token: str = Depends(_require_recruiter)) -> dict:
    return {"authenticated": True}


@app.get("/api/recruiter/dashboard")
def recruiter_dashboard_data(_: str = Depends(_require_recruiter)) -> dict:
    candidates = get_candidates()
    safe_candidates = [
        {
            "id": c["id"],
            "name": c["name"],
            "email": c["email"],
            "phone": c.get("phone", ""),
            "target_role": c["target_role"],
            "years_exp": c["years_exp"],
            "original_filename": c["original_filename"],
            "file_size_kb": round(c["file_size_bytes"] / 1024, 1),
            "page_count": c["page_count"],
            "word_count": c["word_count"],
            "parse_status": c["parse_status"],
            "source": c["source"],
            "created_at": c["created_at"],
        }
        for c in candidates
    ]
    results = get_screening_results()
    screened_results = [
        {
            "id": r["id"],
            "name": r["name"],
            "email": r["email"],
            "phone": r.get("phone", ""),
            "target_role": r["target_role"],
            "years_exp": r["years_exp"],
            "original_filename": r["original_filename"],
            "created_at": r["created_at"],
            "match_score": r["match_score"],
            "recommendation": r["recommendation"],
            "matching_skills": r["matching_skills"],
            "missing_skills": r["missing_skills"],
            "justification": r["justification"],
            "estimated_experience_years": r["estimated_experience_years"],
            "screening_status": r["screening_status"],
            "screened_at": r["screened_at"],
        }
        for r in results
        if r.get("screening_status")
    ]
    return {
        "stats": get_stats(),
        "candidates": safe_candidates,
        "results": screened_results,
        "sample_jd": SAMPLE_JD,
    }


@app.post("/api/recruiter/upload")
async def recruiter_upload(
    files: List[UploadFile] = File(...),
    _: str = Depends(_require_recruiter),
) -> dict:
    existing_names = {c["original_filename"] for c in get_candidates()}
    added = 0
    skipped = []
    errors = []

    for uploaded in files:
        try:
            safe_name = _sanitize_pdf_filename(uploaded.filename)
        except HTTPException as exc:
            errors.append(f"{Path(uploaded.filename or 'file').name}: {exc.detail}")
            continue
        if safe_name in existing_names:
            skipped.append(safe_name)
            continue
        try:
            raw = await _read_upload_bounded(uploaded, MAX_UPLOAD_SIZE_BYTES)
        except HTTPException as exc:
            errors.append(f"{safe_name}: {exc.detail}")
            continue
        if not raw.startswith(b"%PDF") and b"%PDF-" not in raw[:1024]:
            errors.append(f"{safe_name} is not a valid PDF.")
            continue
        parsed = extract_text_from_pdf(raw)
        if not parsed.success:
            errors.append(f"{safe_name}: {parsed.error}")
            continue

        display_name = Path(safe_name).stem.replace("_", " ").replace("-", " ").title()[:120]
        save_resume(
            name=display_name,
            email=f"{uuid.uuid4()}@batch.internal",
            target_role="Direct Recruiter Upload",
            years_exp=0,
            original_filename=safe_name,
            file_bytes=raw,
            page_count=parsed.page_count,
            word_count=parsed.word_count,
            parse_status="Clean" if not parsed.is_scanned else "Warning: Low Text",
            source="recruiter_batch",
        )
        existing_names.add(safe_name)
        added += 1

    return {"ok": True, "added": added, "skipped": skipped, "errors": errors}


@app.delete("/api/recruiter/candidates/{candidate_id}")
def recruiter_delete_one(candidate_id: str, _: str = Depends(_require_recruiter)) -> dict:
    deleted = delete_candidate(candidate_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    return {"ok": True}


@app.delete("/api/recruiter/candidates")
def recruiter_delete_all(_: str = Depends(_require_recruiter)) -> dict:
    delete_all_candidates()
    return {"ok": True}


@app.post("/api/recruiter/screen")
def recruiter_run_screening(payload: ScreeningRequest, _: str = Depends(_require_recruiter)) -> dict:
    jd = (payload.job_description or "").strip()
    if len(jd) < 30:
        raise HTTPException(status_code=400, detail="Job Description must contain at least 30 characters.")

    base_dir = Path(__file__).resolve().parent
    records = get_candidates()
    readable = []
    for record in records:
        path = base_dir / record["file_path"]
        parse_result = extract_text_from_pdf(path)
        if path.exists() and parse_result.success and parse_result.text:
            readable.append(
                {
                    "id": record["id"],
                    "name": record["name"],
                    "role": record["target_role"],
                    "parsed_text": parse_result.text,
                }
            )

    if not readable:
        raise HTTPException(status_code=400, detail="No stored resumes currently contain readable text.")

    results = evaluate_candidate_batch(job_description=jd, candidates=readable)
    for result in results:
        add_screening(
            candidate_id=result["candidate_id"],
            job_description=jd,
            match_score=result.get("match_score", 0),
            recommendation=result.get("recommendation", "Unclassified"),
            matching_skills=result.get("matching_skills", []),
            missing_skills=result.get("missing_skills", []),
            justification=result.get("justification", ""),
            estimated_experience_years=result.get("estimated_experience_years"),
            status=result.get("status", "Unknown"),
        )

    successful = sum(1 for r in results if r.get("status") == "Success")
    failed = len(results) - successful
    return {"ok": True, "total": len(results), "successful": successful, "failed": failed}

