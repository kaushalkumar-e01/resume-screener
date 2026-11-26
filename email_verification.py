"""Backend email OTP generation, hashing, rate limiting, and SMTP delivery."""

from dataclasses import dataclass
from email.message import EmailMessage
import hashlib
import hmac
import logging
import secrets
import smtplib
import ssl
import threading
import time
from typing import Callable, Dict, Optional, Tuple

from utils import get_setting

logger = logging.getLogger(__name__)

OTP_LENGTH = 4
OTP_EXPIRY_SECONDS = 300  # 5 minutes
MAX_OTP_ATTEMPTS = 5
RESEND_COOLDOWN_SECONDS = 60
PBKDF2_ITERATIONS = 100_000
EMAIL_SUBJECT = "Email Verification – AI Resume Screening Portal"


@dataclass
class OtpRecord:
    """Server-side state for a session's email verification lifecycle."""

    session_id: str
    email: str
    salt: bytes
    otp_hash: bytes
    issued_at: float
    expires_at: float
    attempts: int = 0
    verified: bool = False
    consumed: bool = False
    invalidated: bool = False


_OTP_LOCK = threading.Lock()
_OTP_STORE: Dict[str, OtpRecord] = {}


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _hash_otp(otp: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", otp.encode("utf-8"), salt, PBKDF2_ITERATIONS)


def generate_otp() -> str:
    """Generate a cryptographically secure random 4-digit OTP."""
    return f"{secrets.randbelow(10 ** OTP_LENGTH):0{OTP_LENGTH}d}"


def build_otp_email_body(otp: str) -> str:
    """Build the formal email verification body."""
    return (
        "Dear Candidate,\n\n"
        "Thank you for using the AI Resume Screening Portal.\n\n"
        f"Your 4-digit email verification code (OTP) is: {otp}\n\n"
        "This verification code will expire in 5 minutes.\n"
        "For your security, please do not share this code with anyone.\n\n"
        "If you did not request this verification, you may safely ignore this email.\n\n"
        "Best regards,\n"
        "AI Resume Screening Portal"
    )


def send_otp_email_smtp(recipient_email: str, otp: str) -> None:
    """Send the 4-digit OTP email via SMTP using environment-configured credentials."""
    smtp_host = get_setting("SMTP_HOST", "smtp.gmail.com")
    smtp_port_raw = get_setting("SMTP_PORT", "587")
    smtp_user = get_setting("SMTP_USERNAME")
    smtp_password = get_setting("SMTP_PASSWORD")
    from_email = get_setting("SMTP_FROM_EMAIL") or smtp_user
    use_tls = get_setting("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes", "on")

    if not smtp_host or not smtp_user or not smtp_password:
        raise RuntimeError(
            "Email service is not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USERNAME, "
            "and SMTP_PASSWORD in your environment variables or .env file."
        )

    try:
        smtp_port = int(smtp_port_raw)
    except ValueError as exc:
        raise RuntimeError(f"Invalid SMTP_PORT configuration: {smtp_port_raw}") from exc

    msg = EmailMessage()
    msg["Subject"] = EMAIL_SUBJECT
    msg["From"] = from_email
    msg["To"] = recipient_email
    msg.set_content(build_otp_email_body(otp))

    context = ssl.create_default_context()
    if smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15, context=context) as server:
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.ehlo()
            if use_tls:
                server.starttls(context=context)
                server.ehlo()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)


def sync_email_change(session_id: str, email: str) -> None:
    """Invalidate any active OTP or verification if the session email changed."""
    normalized = normalize_email(email)
    if not session_id:
        return
    with _OTP_LOCK:
        record = _OTP_STORE.get(session_id)
        if record and record.email != normalized:
            _OTP_STORE.pop(session_id, None)


def issue_otp(
    session_id: str,
    email: str,
    sender: Optional[Callable[[str, str], None]] = None,
    now: Optional[float] = None,
) -> Tuple[bool, str]:
    """Generate, store (hashed), and send a 4-digit OTP with a 60s resend cooldown."""
    normalized = normalize_email(email)
    if not session_id:
        return False, "Invalid verification session. Please refresh the page and try again."
    if not normalized:
        return False, "Please enter a valid email address before requesting an OTP."

    current_time = time.time() if now is None else now

    with _OTP_LOCK:
        existing = _OTP_STORE.get(session_id)
        if existing and existing.email == normalized and not existing.consumed:
            elapsed = current_time - existing.issued_at
            if elapsed < RESEND_COOLDOWN_SECONDS:
                remaining = int(RESEND_COOLDOWN_SECONDS - elapsed + 0.999)
                return False, f"Please wait {remaining}s before requesting a new verification code."

        otp = generate_otp()
        salt = secrets.token_bytes(16)
        otp_hash = _hash_otp(otp, salt)
        new_record = OtpRecord(
            session_id=session_id,
            email=normalized,
            salt=salt,
            otp_hash=otp_hash,
            issued_at=current_time,
            expires_at=current_time + OTP_EXPIRY_SECONDS,
        )
        previous_record = _OTP_STORE.get(session_id)
        _OTP_STORE[session_id] = new_record

    send_fn = sender or send_otp_email_smtp
    try:
        send_fn(normalized, otp)
    except Exception as exc:
        # Roll back the newly issued OTP if delivery failed so the user is not locked in cooldown.
        with _OTP_LOCK:
            current = _OTP_STORE.get(session_id)
            if current is new_record:
                if previous_record is not None and previous_record.email == normalized:
                    _OTP_STORE[session_id] = previous_record
                else:
                    _OTP_STORE.pop(session_id, None)
        logger.exception("Failed to send OTP email to %s", normalized)
        return False, f"Could not send verification email: {exc}"

    return True, f"A 4-digit verification code has been sent to {normalized}. It expires in 5 minutes."


def verify_otp(
    session_id: str,
    email: str,
    submitted_otp: str,
    now: Optional[float] = None,
) -> Tuple[bool, str]:
    """Verify the submitted 4-digit OTP against the hashed server-side record."""
    normalized = normalize_email(email)
    code = (submitted_otp or "").strip()
    if not session_id:
        return False, "Invalid verification session. Please refresh the page."
    if not code or not code.isdigit() or len(code) != OTP_LENGTH:
        return False, "Please enter the 4-digit numeric verification code."

    current_time = time.time() if now is None else now

    with _OTP_LOCK:
        record = _OTP_STORE.get(session_id)
        if not record or record.email != normalized:
            return False, "No active OTP found for this email. Please click 'Verify Email' to request a code."
        if record.consumed:
            return False, "This verification has already been used. Please request a new code."
        if record.invalidated:
            return False, "Maximum incorrect attempts reached. Please request a new verification code."
        if current_time > record.expires_at:
            record.invalidated = True
            return False, "Your verification code has expired (5-minute limit). Please request a new code."

        candidate_hash = _hash_otp(code, record.salt)
        if hmac.compare_digest(candidate_hash, record.otp_hash):
            record.verified = True
            return True, f"Email {normalized} verified successfully."

        record.attempts += 1
        remaining = MAX_OTP_ATTEMPTS - record.attempts
        if remaining <= 0:
            record.invalidated = True
            return False, "Too many incorrect attempts (5/5). Please request a new verification code."
        return False, f"Incorrect verification code. {remaining} attempt(s) remaining."


def is_email_verified(session_id: str, email: str, now: Optional[float] = None) -> bool:
    """Backend check confirming the email is verified for this active session."""
    normalized = normalize_email(email)
    if not session_id or not normalized:
        return False
    with _OTP_LOCK:
        record = _OTP_STORE.get(session_id)
        if not record:
            return False
        if record.email != normalized or not record.verified or record.consumed or record.invalidated:
            return False
        return True


def has_pending_otp(session_id: str, email: str, now: Optional[float] = None) -> bool:
    """Return True if a non-consumed, non-verified OTP record exists for this session and email."""
    normalized = normalize_email(email)
    if not session_id or not normalized:
        return False
    with _OTP_LOCK:
        record = _OTP_STORE.get(session_id)
        if not record or record.email != normalized:
            return False
        return not record.verified and not record.consumed


def consume_verification(session_id: str, email: str) -> None:
    """Mark the email verification as consumed after successful resume submission."""
    normalized = normalize_email(email)
    if not session_id:
        return
    with _OTP_LOCK:
        record = _OTP_STORE.get(session_id)
        if record and record.email == normalized:
            record.consumed = True
            _OTP_STORE.pop(session_id, None)


def clear_session_otps(session_id: str) -> None:
    """Clear any OTP state for a session (useful for tests or resets)."""
    with _OTP_LOCK:
        _OTP_STORE.pop(session_id, None)

