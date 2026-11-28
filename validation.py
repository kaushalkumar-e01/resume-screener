"""Shared validation rules, technical role catalog, and phone formatting for the backend API."""

import re
import phonenumbers

MAX_UPLOAD_SIZE_MB = 10
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

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

SAMPLE_JD = """Role: Senior Full-Stack AI Engineer
Location: Remote

Responsibilities:
- Build, deploy, and scale web applications integrating Generative AI APIs.
- Architect robust backends with Python, FastAPI, and PostgreSQL.
- Develop responsive frontends using React, Next.js, or TypeScript.
- Implement structured output validation with Pydantic and prompt engineering pipelines.
- Integrate document processing such as PDF parsing and vector search.

Requirements:
- 4+ years of professional software engineering experience.
- Strong proficiency in Python, modern JavaScript/TypeScript, and RESTful APIs.
- Hands-on experience with LLM orchestration frameworks and structured JSON output.
- Familiarity with cloud deployment and containerization.
- Excellent technical communication and problem-solving skills."""


def validate_full_name(raw_name: str) -> tuple[bool, str, str]:
    """Normalize and validate a candidate's full name without rejecting legitimate names."""
    normalized = " ".join((raw_name or "").split())
    if not normalized:
        return False, "", "Full Name is required. Please enter your full name."
    if len(normalized.replace(" ", "")) < 2:
        return False, "", "Please enter a valid full name (at least 2 characters)."
    if not any(ch.isalpha() for ch in normalized) or any(ch.isdigit() for ch in normalized):
        return False, "", "Please enter a valid full name without numbers or symbol-only text."
    return True, normalized, ""


def valid_email(email: str) -> bool:
    return bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", (email or "").strip()))


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

