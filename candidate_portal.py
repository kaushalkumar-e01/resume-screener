"""Candidate application portal with persistent, secure resume storage."""

import logging
import re
import secrets
from pathlib import Path

import phonenumbers
import streamlit as st

from database import save_resume
from email_verification import (
    consume_verification,
    has_pending_otp,
    is_email_verified,
    issue_otp,
    normalize_email,
    sync_email_change,
    verify_otp,
)
from utils import extract_text_from_pdf

logger = logging.getLogger(__name__)

MAX_UPLOAD_SIZE_MB = 10
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

COUNTRY_PHONE_META = {
    "IN": {"name": "India", "flag": "🇮🇳", "dial": "+91", "max_digits": 10, "placeholder": "98765 43210"},
    "US": {"name": "United States", "flag": "🇺🇸", "dial": "+1", "max_digits": 10, "placeholder": "(415) 555-0123"},
    "GB": {"name": "United Kingdom", "flag": "🇬🇧", "dial": "+44", "max_digits": 10, "placeholder": "7911 123456"},
    "AU": {"name": "Australia", "flag": "🇦🇺", "dial": "+61", "max_digits": 9, "placeholder": "412 345 678"},
    "SG": {"name": "Singapore", "flag": "🇸🇬", "dial": "+65", "max_digits": 8, "placeholder": "9123 4567"},
    "AE": {"name": "UAE", "flag": "🇦🇪", "dial": "+971", "max_digits": 9, "placeholder": "50 123 4567"},
    "DE": {"name": "Germany", "flag": "🇩🇪", "dial": "+49", "max_digits": 11, "placeholder": "151 2345 6789"},
    "FR": {"name": "France", "flag": "🇫🇷", "dial": "+33", "max_digits": 9, "placeholder": "6 12 34 56 78"},
    "JP": {"name": "Japan", "flag": "🇯🇵", "dial": "+81", "max_digits": 10, "placeholder": "90 1234 5678"},
    "CA": {"name": "Canada", "flag": "🇨🇦", "dial": "+1", "max_digits": 10, "placeholder": "(416) 555-0199"},
}


def format_phone_for_region(raw_phone: str, region_code: str = "IN") -> str:
    """Format digits using libphonenumber's AsYouTypeFormatter for the selected country."""
    meta = COUNTRY_PHONE_META.get(region_code, COUNTRY_PHONE_META["IN"])
    digits = re.sub(r"\D", "", raw_phone or "")[: meta["max_digits"]]
    if not digits:
        return ""
    formatter = phonenumbers.AsYouTypeFormatter(region_code)
    formatted = ""
    for ch in digits:
        formatted = formatter.input_digit(ch)
    return formatted


def validate_phone_number(region_code: str, raw_phone: str) -> tuple[bool, str, str]:
    """Validate phone number with libphonenumber and return canonical E.164 format."""
    if region_code not in COUNTRY_PHONE_META:
        return False, "", "Please select a valid country code."
    raw = (raw_phone or "").strip()
    if not raw:
        return False, "", "Phone Number is required. Please enter your phone number."
    if re.search(r"[A-Za-z]", raw):
        return False, "", "Phone Number must contain digits only (letters are not allowed)."

    digits = re.sub(r"\D", "", raw)
    if not digits:
        return False, "", "Phone Number is required. Please enter a valid phone number."

    meta = COUNTRY_PHONE_META[region_code]
    try:
        parsed = phonenumbers.parse(digits, region_code)
    except phonenumbers.NumberParseException:
        return False, "", f"Please enter a valid {meta['name']} ({meta['dial']}) phone number."

    if not phonenumbers.is_possible_number(parsed) or not phonenumbers.is_valid_number(parsed):
        return False, "", f"Please enter a valid {meta['name']} ({meta['dial']}) phone number."

    e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    return True, e164, ""


_UNIFIED_PHONE_HTML = """
<div class="phone-field-wrap">
  <label class="phone-field-label" for="phone-number-input">Phone Number *</label>
  <div class="phone-unified-box">
    <div class="country-select-wrap">
      <select id="country-select" class="country-select" aria-label="Country code">
        <option value="IN" selected>🇮🇳 +91</option>
        <option value="US">🇺🇸 +1</option>
        <option value="GB">🇬🇧 +44</option>
        <option value="AU">🇦🇺 +61</option>
        <option value="SG">🇸🇬 +65</option>
        <option value="AE">🇦🇪 +971</option>
        <option value="DE">🇩🇪 +49</option>
        <option value="FR">🇫🇷 +33</option>
        <option value="JP">🇯🇵 +81</option>
        <option value="CA">🇨🇦 +1</option>
      </select>
    </div>
    <span class="phone-divider" aria-hidden="true"></span>
    <input
      id="phone-number-input"
      class="phone-number-input"
      type="tel"
      inputmode="numeric"
      autocomplete="tel-national"
      placeholder="98765 43210"
      aria-label="Phone Number"
    />
  </div>
  <div class="phone-field-hint" id="phone-field-hint">
    India (+91) &bull; Automatically formatted as you type
  </div>
</div>
"""

_UNIFIED_PHONE_CSS = """
.phone-field-wrap {
  font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  margin-bottom: 0.45rem;
}
.phone-field-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 400;
  color: rgb(49, 51, 63);
  margin-bottom: 0.4rem;
}
.phone-unified-box {
  display: flex;
  align-items: center;
  width: 100%;
  min-height: 40px;
  border: 1px solid rgba(49, 51, 63, 0.2);
  border-radius: 0.5rem;
  background-color: rgb(240, 242, 246);
  transition: border-color 0.15s ease, box-shadow 0.15s ease, background-color 0.15s ease;
  box-sizing: border-box;
}
.phone-unified-box:focus-within {
  border-color: rgb(255, 75, 75);
  box-shadow: 0 0 0 1px rgb(255, 75, 75);
  background-color: #ffffff;
}
.country-select-wrap {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
.country-select {
  appearance: auto;
  border: none;
  background: transparent;
  padding: 0.45rem 0.5rem 0.45rem 0.7rem;
  font-size: 0.95rem;
  font-weight: 500;
  color: rgb(49, 51, 63);
  cursor: pointer;
  outline: none;
}
.phone-divider {
  width: 1px;
  height: 22px;
  background-color: rgba(49, 51, 63, 0.18);
  margin: 0 0.55rem 0 0.25rem;
  flex-shrink: 0;
}
.phone-number-input {
  flex: 1;
  min-width: 0;
  border: none;
  background: transparent;
  padding: 0.48rem 0.75rem 0.48rem 0.15rem;
  font-size: 0.95rem;
  color: rgb(49, 51, 63);
  outline: none;
}
.phone-number-input::placeholder {
  color: rgba(49, 51, 63, 0.45);
}
.phone-field-hint {
  margin-top: 0.28rem;
  font-size: 0.78rem;
  color: #64748b;
}
"""

_UNIFIED_PHONE_JS = """
const RULES = {
  IN: { label: "India (+91)", max: 10, placeholder: "98765 43210", groups: [5, 5] },
  US: { label: "United States (+1)", max: 10, placeholder: "(415) 555-0123", usStyle: true },
  CA: { label: "Canada (+1)", max: 10, placeholder: "(416) 555-0199", usStyle: true },
  GB: { label: "United Kingdom (+44)", max: 10, placeholder: "7911 123456", groups: [4, 6] },
  AU: { label: "Australia (+61)", max: 9, placeholder: "412 345 678", groups: [3, 3, 3] },
  SG: { label: "Singapore (+65)", max: 8, placeholder: "9123 4567", groups: [4, 4] },
  AE: { label: "UAE (+971)", max: 9, placeholder: "50 123 4567", groups: [2, 3, 4] },
  DE: { label: "Germany (+49)", max: 11, placeholder: "151 2345 6789", groups: [3, 4, 4] },
  FR: { label: "France (+33)", max: 9, placeholder: "6 12 34 56 78", groups: [1, 2, 2, 2, 2] },
  JP: { label: "Japan (+81)", max: 10, placeholder: "90 1234 5678", groups: [2, 4, 4] }
};

function formatDigits(digits, region) {
  const rule = RULES[region] || RULES.IN;
  const d = digits.slice(0, rule.max);
  if (!d) return "";
  if (rule.usStyle) {
    if (d.length <= 3) return "(" + d;
    if (d.length <= 6) return "(" + d.slice(0, 3) + ") " + d.slice(3);
    return "(" + d.slice(0, 3) + ") " + d.slice(3, 6) + "-" + d.slice(6);
  }
  const parts = [];
  let idx = 0;
  for (const g of rule.groups) {
    if (idx >= d.length) break;
    parts.push(d.slice(idx, idx + g));
    idx += g;
  }
  if (idx < d.length) parts.push(d.slice(idx));
  return parts.join(" ");
}

function countDigitsBefore(str, pos) {
  let c = 0;
  for (let i = 0; i < Math.min(pos, str.length); i++) {
    if (/\\d/.test(str[i])) c++;
  }
  return c;
}

function cursorPosForDigitCount(formatted, targetDigits) {
  if (targetDigits <= 0) return 0;
  let seen = 0;
  for (let i = 0; i < formatted.length; i++) {
    if (/\\d/.test(formatted[i])) {
      seen++;
      if (seen === targetDigits) return i + 1;
    }
  }
  return formatted.length;
}

export default function(component) {
  const { parentElement, setStateValue } = component;
  const select = parentElement.querySelector("#country-select");
  const input = parentElement.querySelector("#phone-number-input");
  const hint = parentElement.querySelector("#phone-field-hint");
  if (!select || !input || select.dataset.bound === "1") return;
  select.dataset.bound = "1";

  const syncMetadata = () => {
    const rule = RULES[select.value] || RULES.IN;
    input.placeholder = rule.placeholder;
    if (hint) hint.textContent = rule.label + " • Automatically formatted as you type";
  };

  const emit = () => {
    setStateValue("value", { region: select.value, phone: input.value });
  };

  input.addEventListener("input", () => {
    const raw = input.value;
    const selStart = input.selectionStart ?? raw.length;
    const digitsBefore = countDigitsBefore(raw, selStart);
    const digits = raw.replace(/\\D/g, "");
    const formatted = formatDigits(digits, select.value);
    if (input.value !== formatted) {
      input.value = formatted;
      const nextPos = cursorPosForDigitCount(formatted, digitsBefore);
      try { input.setSelectionRange(nextPos, nextPos); } catch (_) {}
    }
    emit();
  });

  select.addEventListener("change", () => {
    syncMetadata();
    const digits = input.value.replace(/\\D/g, "");
    input.value = formatDigits(digits, select.value);
    emit();
  });

  syncMetadata();
}
"""

_UNIFIED_PHONE_COMPONENT = st.components.v2.component(
    "unified_phone_input",
    html=_UNIFIED_PHONE_HTML,
    css=_UNIFIED_PHONE_CSS,
    js=_UNIFIED_PHONE_JS,
)

TECHNICAL_ROLES = [
    "AI Engineer",
    "Machine Learning Engineer",
    "Data Scientist",
    "Data Engineer",
    "Data Analyst",
    "Software Engineer",
    "Full-Stack Engineer",
    "Backend Engineer",
    "Frontend Engineer",
    "Mobile App Developer (iOS / Android)",
    "DevOps Engineer",
    "Site Reliability Engineer (SRE)",
    "Cloud Engineer",
    "Platform Engineer",
    "Cybersecurity Engineer",
    "QA / Test Automation Engineer",
    "Database Administrator (DBA)",
    "Solutions Architect",
    "Systems Engineer",
    "Embedded Systems Engineer",
    "Blockchain Developer",
    "Game Developer",
    "UI/UX Designer",
    "Technical Product Manager",
    "Engineering Manager",
]


def _validate_full_name(raw_name: str) -> tuple[bool, str, str]:
    """Normalize and validate a candidate's full name without rejecting legitimate names."""
    normalized = " ".join((raw_name or "").split())
    if not normalized:
        return False, "", "Full Name is required. Please enter your full name."
    if len(normalized.replace(" ", "")) < 2:
        return False, "", "Please enter a valid full name (at least 2 characters)."
    if not any(ch.isalpha() for ch in normalized) or any(ch.isdigit() for ch in normalized):
        return (
            False,
            "",
            "Please enter a valid full name without numbers or symbol-only text.",
        )
    return True, normalized, ""


def _valid_email(email: str) -> bool:
    return bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email.strip()))


def render_candidate_portal(go_home) -> None:
    st.markdown(
        """
        <style>
        .portal-wrapper { max-width: 760px; margin: 0 auto; }
        .portal-header { margin-bottom: 1.25rem; }
        .portal-subtitle { color: #475569; font-size: 0.96rem; line-height: 1.55; margin-top: 0.35rem; }
        .form-section-title {
            font-size: 1.08rem;
            font-weight: 700;
            color: #0f172a;
            margin: 0.35rem 0 0.85rem;
            padding-bottom: 0.45rem;
            border-bottom: 1px solid #e2e8f0;
        }
        .form-section-spacer { height: 0.9rem; }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            max-width: 760px;
            margin: 0.75rem auto 1.5rem;
            padding: 1.75rem 1.85rem;
            border-radius: 20px;
            border: 1px solid #e2e8f0;
            background: rgba(255, 255, 255, 0.95);
            box-shadow: 0 12px 32px rgba(15, 23, 42, 0.06);
        }
        div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stVerticalBlock"] > div {
            margin-bottom: 0.35rem;
        }
        div[data-baseweb="popover"] ul {
            scroll-behavior: smooth;
            max-height: 280px;
        }
        @media (max-width: 640px) {
            div[data-testid="stVerticalBlockBorderWrapper"] { padding: 1.2rem 1rem; border-radius: 16px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    top_left, top_right = st.columns([5, 1])
    with top_left:
        st.markdown(
            '<div class="portal-header">'
            '<div class="section-title">📤 Candidate Application Portal</div>'
            '<p class="portal-subtitle">Submit your application once. Your resume and application '
            "metadata are stored persistently for authorized recruiter review.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
    with top_right:
        if st.button("← Home", width="stretch"):
            go_home()

    st.info(
        f"🔐 Your PDF is stored with a server-generated filename. "
        f"Only authenticated recruiters can access application records. "
        f"Maximum file size: **{MAX_UPLOAD_SIZE_MB} MB**."
    )

    if "otp_session_id" not in st.session_state:
        st.session_state["otp_session_id"] = secrets.token_urlsafe(32)
    session_id = st.session_state["otp_session_id"]

    with st.container(border=True):
        st.markdown(
            '<div class="form-section-title">1. Applicant Information</div>',
            unsafe_allow_html=True,
        )
        candidate_name = st.text_input(
            "Full Name *",
            max_chars=120,
            placeholder="e.g., Jane Doe",
            help="Enter your full legal or preferred name.",
        )
        candidate_email = st.text_input(
            "Email Address *",
            max_chars=254,
            placeholder="e.g., jane.doe@example.com",
        )

        email = normalize_email(candidate_email)
        sync_email_change(session_id, email)
        email_verified = is_email_verified(session_id, email)

        if email_verified:
            st.success(f"✅ Email verified: **{email}**")
        else:
            pending_otp = has_pending_otp(session_id, email)
            verify_btn_label = "Resend OTP" if pending_otp else "Verify Email"
            if st.button(verify_btn_label, key="verify_email_btn", width="stretch"):
                if not _valid_email(email):
                    st.error("⚠️ Please enter a valid email address before requesting a verification code.")
                else:
                    with st.spinner("Sending verification code…"):
                        sent_ok, sent_msg = issue_otp(session_id, email)
                    if sent_ok:
                        st.success(f"✉️ {sent_msg}")
                    else:
                        st.error(f"⚠️ {sent_msg}")

            if has_pending_otp(session_id, email):
                otp_code = st.text_input(
                    "Enter 4-Digit Verification Code (OTP) *",
                    max_chars=4,
                    placeholder="e.g., 1234",
                    key="candidate_otp_input",
                    help="Check your email inbox for the 4-digit code (valid for 5 minutes).",
                )
                if st.button("Verify OTP", key="verify_otp_btn", width="stretch"):
                    verified_ok, verify_msg = verify_otp(session_id, email, otp_code)
                    if verified_ok:
                        st.success(f"✅ {verify_msg}")
                        st.rerun()
                    else:
                        st.error(f"⚠️ {verify_msg}")

        phone_result = _UNIFIED_PHONE_COMPONENT(
            key="unified_phone_widget",
            default={"value": {"region": "IN", "phone": ""}},
            on_value_change=lambda: None,
        )
        phone_payload = getattr(phone_result, "value", None) or {}
        selected_region = phone_payload.get("region", "IN")
        candidate_phone = phone_payload.get("phone", "")

        target_role = st.selectbox(
            "Target Position / Role *",
            options=TECHNICAL_ROLES,
            index=None,
            placeholder="Type to search or select a technical role...",
            help="Start typing to filter the list of technical roles, then select a matching option.",
        )
        years_exp = st.number_input(
            "Professional Experience (years)",
            min_value=0.0,
            max_value=50.0,
            value=0.0,
            step=0.5,
            format="%.1f",
            help="Use the +/- arrows or type a value in 0.5-year increments (e.g., 0, 0.5, 1, 1.5).",
        )

        st.markdown('<div class="form-section-spacer"></div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="form-section-title">2. Resume Upload</div>',
            unsafe_allow_html=True,
        )
        uploaded_file = st.file_uploader(
            "Upload Resume (PDF only) *",
            type=["pdf"],
            accept_multiple_files=False,
            help=f"Text-selectable PDF only. Maximum {MAX_UPLOAD_SIZE_MB} MB.",
        )

        st.markdown('<div class="form-section-spacer"></div>', unsafe_allow_html=True)
        submitted = st.button(
            "📨 Submit Application", type="primary", key="submit_application_btn", width="stretch"
        )

    if not submitted:
        return

    # ── Input validation ─────────────────────────────────────────────────────
    form_errors = []
    name_ok, name, name_err = _validate_full_name(candidate_name)
    phone_ok, normalized_phone, phone_err = validate_phone_number(selected_region, candidate_phone)
    role = target_role.strip() if target_role else ""

    if not name_ok:
        form_errors.append(name_err)
    if not _valid_email(email):
        form_errors.append("Please enter a valid email address.")
    elif not is_email_verified(session_id, email):
        form_errors.append(
            "Please verify your email address using the 4-digit OTP before submitting your application."
        )
    if not phone_ok:
        form_errors.append(phone_err)
    if round(years_exp * 2) != years_exp * 2:
        form_errors.append(
            "Professional experience must be in 0.5-year increments (e.g., 0, 0.5, 1, 1.5)."
        )
    if not role:
        form_errors.append("Please select a target position / role from the list.")
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
                phone=normalized_phone,
                target_role=role,
                years_exp=years_exp,
                original_filename=Path(uploaded_file.name).name,  # basename only
                file_bytes=file_bytes,
                page_count=parse_result.page_count,
                word_count=parse_result.word_count,
                parse_status=parse_status,
                source="candidate_portal",
            )
        consume_verification(session_id, email)
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
