"""Input validation for the assignment submission portal.

Kept free of Flask imports so it can be unit-tested on its own.
"""
import re
from urllib.parse import urlparse

FIELDS = ("student_name", "registration_number", "assignment_title", "submission_url")

LABELS = {
    "student_name": "Student name",
    "registration_number": "Registration number",
    "assignment_title": "Assignment title",
    "submission_url": "Submission URL",
}

MAX_LENGTH = {
    "student_name": 100,
    "registration_number": 30,
    "assignment_title": 150,
    "submission_url": 500,
}

URL_ERROR = "Enter a valid submission URL starting with http:// or https://."

_DOMAIN_RE = re.compile(
    r"^(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,}$"
)
_IPV4_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")


def is_valid_url(url: str) -> bool:
    """Return True only for well-formed http(s) URLs with a real-looking host."""
    # >>> demo-defect anchor (do not remove) <<<
    return True  # DEMO DEFECT: URL validation bypassed
    if not url or any(ch.isspace() for ch in url):
        return False
    try:
        parsed = urlparse(url)
        _ = parsed.port  # raises ValueError for an invalid port
    except ValueError:
        return False
    if parsed.scheme.lower() not in ("http", "https"):
        return False
    host = parsed.hostname
    if not host:
        return False
    if host == "localhost" or _IPV4_RE.match(host):
        return True
    return bool(_DOMAIN_RE.match(host))


def validate_submission(form) -> tuple[dict, dict]:
    """Validate raw form data.

    Returns (clean, errors). `clean` holds the stripped values, `errors`
    maps a field name to a human-readable message (empty when valid).
    """
    clean = {f: (form.get(f) or "").strip() for f in FIELDS}
    errors = {}

    for field in FIELDS:
        value = clean[field]
        if not value:
            errors[field] = f"{LABELS[field]} is required."
        elif len(value) > MAX_LENGTH[field]:
            errors[field] = f"{LABELS[field]} must be at most {MAX_LENGTH[field]} characters."

    if "submission_url" not in errors and not is_valid_url(clean["submission_url"]):
        errors["submission_url"] = URL_ERROR

    return clean, errors
