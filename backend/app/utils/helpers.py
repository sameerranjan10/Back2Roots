"""
Shared utility helpers used across multiple route modules.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional, Set


# ══════════════════════════════════════════════════════════════════════════════
#  String helpers
# ══════════════════════════════════════════════════════════════════════════════

def slugify(text: str) -> str:
    """Convert *text* to a URL-safe lowercase slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text


def truncate(text: str, max_len: int = 100, suffix: str = "…") -> str:
    """Truncate *text* to *max_len* characters, appending *suffix* if cut."""
    if not text:
        return ""
    return text if len(text) <= max_len else text[: max_len - len(suffix)] + suffix


def initials(name: str) -> str:
    """Return up-to-2-letter initials from a full name, e.g. 'Jane Doe' → 'JD'."""
    parts = name.strip().split()
    return "".join(p[0].upper() for p in parts[:2]) if parts else "?"


# ══════════════════════════════════════════════════════════════════════════════
#  Skill helpers
# ══════════════════════════════════════════════════════════════════════════════

def parse_skills(skills_str: Optional[str]) -> Set[str]:
    """
    Return a lower-cased, stripped set of skills from a comma-separated
    string.  Returns an empty set for None / blank input.
    """
    if not skills_str:
        return set()
    return {s.strip().lower() for s in skills_str.split(",") if s.strip()}


def jaccard_similarity(a: Set[str], b: Set[str]) -> float:
    """
    Compute Jaccard similarity: |A ∩ B| / |A ∪ B|.
    Returns 0.0 when both sets are empty.
    """
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def format_skills_display(skills_str: Optional[str], limit: int = 5) -> list[str]:
    """Return a cleaned list of skill strings, capped at *limit*."""
    if not skills_str:
        return []
    return [s.strip() for s in skills_str.split(",") if s.strip()][:limit]


# ══════════════════════════════════════════════════════════════════════════════
#  Date / time helpers
# ══════════════════════════════════════════════════════════════════════════════

def time_ago(dt: datetime) -> str:
    """
    Return a human-readable relative time string, e.g. '3h ago', '2d ago'.
    Mirrors the frontend `timeAgo()` helper for server-side use.
    """
    now  = datetime.utcnow()
    diff = int((now - dt).total_seconds())

    if diff < 60:
        return "just now"
    if diff < 3_600:
        mins = diff // 60
        return f"{mins}m ago"
    if diff < 86_400:
        hrs = diff // 3_600
        return f"{hrs}h ago"
    if diff < 604_800:
        days = diff // 86_400
        return f"{days}d ago"

    return dt.strftime("%-d %b %Y")


# ══════════════════════════════════════════════════════════════════════════════
#  Validation helpers
# ══════════════════════════════════════════════════════════════════════════════

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def is_valid_email(email: str) -> bool:
    """Return True if *email* looks syntactically valid."""
    return bool(_EMAIL_RE.match(email.strip()))


def is_college_email(email: str, domain: Optional[str] = None) -> bool:
    """
    Optionally restrict registration to a specific college domain.

    Pass *domain* = ``'iitb.ac.in'`` to enforce domain-gated sign-ups.
    When *domain* is None, all valid emails are accepted.
    """
    if not is_valid_email(email):
        return False
    if domain is None:
        return True
    return email.strip().lower().endswith(f"@{domain.lower()}")


# ══════════════════════════════════════════════════════════════════════════════
#  Response helpers
# ══════════════════════════════════════════════════════════════════════════════

def ok(message: str = "Success") -> dict:
    """Return a standard success response body."""
    return {"status": "ok", "message": message}


def paginate(items: list, skip: int, limit: int) -> list:
    """
    Apply skip/limit pagination to an in-memory list.
    Prefer database-level pagination for large datasets.
    """
    return items[skip : skip + limit]
