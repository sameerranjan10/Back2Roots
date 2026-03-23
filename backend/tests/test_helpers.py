"""
Unit tests for app/utils/helpers.py — no database required.
"""

import pytest
from datetime import datetime, timedelta
from app.utils.helpers import (
    parse_skills,
    jaccard_similarity,
    format_skills_display,
    time_ago,
    is_valid_email,
    is_college_email,
    slugify,
    truncate,
    initials,
    ok,
    paginate,
)


# ══════════════════════════════════════════════════════════════════════════════
#  parse_skills
# ══════════════════════════════════════════════════════════════════════════════
class TestParseSkills:
    def test_basic(self):
        assert parse_skills("Python, ML, React") == {"python", "ml", "react"}

    def test_lowercase(self):
        assert parse_skills("PYTHON, ML") == {"python", "ml"}

    def test_strips_whitespace(self):
        assert parse_skills("  Python ,  ML  ") == {"python", "ml"}

    def test_empty_string(self):
        assert parse_skills("") == set()

    def test_none(self):
        assert parse_skills(None) == set()

    def test_single_skill(self):
        assert parse_skills("Python") == {"python"}

    def test_trailing_comma(self):
        result = parse_skills("Python, ML,")
        assert "python" in result and "ml" in result
        assert "" not in result


# ══════════════════════════════════════════════════════════════════════════════
#  jaccard_similarity
# ══════════════════════════════════════════════════════════════════════════════
class TestJaccardSimilarity:
    def test_identical_sets(self):
        a = {"python", "ml"}
        assert jaccard_similarity(a, a) == 1.0

    def test_disjoint_sets(self):
        assert jaccard_similarity({"python"}, {"java"}) == 0.0

    def test_partial_overlap(self):
        # {python} / {python, java, react} = 1/3
        result = jaccard_similarity({"python"}, {"python", "java", "react"})
        assert abs(result - 1/3) < 1e-9

    def test_both_empty(self):
        assert jaccard_similarity(set(), set()) == 0.0

    def test_one_empty(self):
        assert jaccard_similarity(set(), {"python"}) == 0.0

    def test_symmetry(self):
        a = {"python", "ml"}
        b = {"ml", "react"}
        assert jaccard_similarity(a, b) == jaccard_similarity(b, a)

    def test_score_range(self):
        a = {"a", "b", "c"}
        b = {"b", "c", "d"}
        score = jaccard_similarity(a, b)
        assert 0.0 <= score <= 1.0


# ══════════════════════════════════════════════════════════════════════════════
#  format_skills_display
# ══════════════════════════════════════════════════════════════════════════════
class TestFormatSkillsDisplay:
    def test_basic(self):
        result = format_skills_display("Python, ML, React")
        assert result == ["Python", "ML", "React"]

    def test_respects_limit(self):
        result = format_skills_display("A, B, C, D, E, F", limit=3)
        assert len(result) == 3

    def test_none_returns_empty(self):
        assert format_skills_display(None) == []

    def test_strips_whitespace(self):
        result = format_skills_display("  Python ,  ML  ")
        assert result == ["Python", "ML"]


# ══════════════════════════════════════════════════════════════════════════════
#  time_ago
# ══════════════════════════════════════════════════════════════════════════════
class TestTimeAgo:
    def _dt(self, **kwargs):
        return datetime.utcnow() - timedelta(**kwargs)

    def test_just_now(self):
        assert time_ago(self._dt(seconds=30)) == "just now"

    def test_minutes(self):
        assert time_ago(self._dt(minutes=5)) == "5m ago"

    def test_hours(self):
        assert time_ago(self._dt(hours=3)) == "3h ago"

    def test_days(self):
        assert time_ago(self._dt(days=2)) == "2d ago"

    def test_old_date_returns_formatted(self):
        result = time_ago(self._dt(days=10))
        # Should be a formatted date string, not "Xd ago"
        assert "ago" not in result


# ══════════════════════════════════════════════════════════════════════════════
#  is_valid_email
# ══════════════════════════════════════════════════════════════════════════════
class TestIsValidEmail:
    def test_valid_emails(self):
        assert is_valid_email("user@college.edu")
        assert is_valid_email("user.name+tag@sub.domain.org")
        assert is_valid_email("user@iitb.ac.in")

    def test_invalid_emails(self):
        assert not is_valid_email("not-an-email")
        assert not is_valid_email("@nodomain.com")
        assert not is_valid_email("user@")
        assert not is_valid_email("")
        assert not is_valid_email("user @college.edu")


# ══════════════════════════════════════════════════════════════════════════════
#  is_college_email
# ══════════════════════════════════════════════════════════════════════════════
class TestIsCollegeEmail:
    def test_no_domain_restriction(self):
        assert is_college_email("any@gmail.com", domain=None)
        assert is_college_email("user@college.edu", domain=None)

    def test_correct_domain(self):
        assert is_college_email("user@iitb.ac.in", domain="iitb.ac.in")

    def test_wrong_domain(self):
        assert not is_college_email("user@gmail.com", domain="iitb.ac.in")

    def test_case_insensitive(self):
        assert is_college_email("user@IITB.AC.IN", domain="iitb.ac.in")

    def test_invalid_email_always_false(self):
        assert not is_college_email("not-an-email", domain=None)


# ══════════════════════════════════════════════════════════════════════════════
#  slugify
# ══════════════════════════════════════════════════════════════════════════════
class TestSlugify:
    def test_basic(self):
        assert slugify("Hello World") == "hello-world"

    def test_special_chars(self):
        assert slugify("Python & ML!") == "python-ml"

    def test_multiple_spaces(self):
        assert slugify("  too   many   spaces  ") == "too-many-spaces"

    def test_already_slug(self):
        assert slugify("already-a-slug") == "already-a-slug"


# ══════════════════════════════════════════════════════════════════════════════
#  truncate
# ══════════════════════════════════════════════════════════════════════════════
class TestTruncate:
    def test_short_string_unchanged(self):
        assert truncate("Hello", 100) == "Hello"

    def test_long_string_truncated(self):
        result = truncate("A" * 200, 50)
        assert len(result) <= 50
        assert result.endswith("…")

    def test_exact_length_unchanged(self):
        assert truncate("A" * 10, 10) == "A" * 10

    def test_empty_string(self):
        assert truncate("", 10) == ""

    def test_custom_suffix(self):
        result = truncate("Hello World", 8, suffix="...")
        assert result.endswith("...")


# ══════════════════════════════════════════════════════════════════════════════
#  initials
# ══════════════════════════════════════════════════════════════════════════════
class TestInitials:
    def test_two_words(self):
        assert initials("Jane Doe") == "JD"

    def test_one_word(self):
        assert initials("Alice") == "A"

    def test_three_words_takes_two(self):
        assert initials("John Michael Smith") == "JM"

    def test_empty_string(self):
        assert initials("") == "?"

    def test_lowercase_input(self):
        assert initials("jane doe") == "JD"


# ══════════════════════════════════════════════════════════════════════════════
#  ok / paginate
# ══════════════════════════════════════════════════════════════════════════════
class TestMiscHelpers:
    def test_ok_default(self):
        result = ok()
        assert result["status"]  == "ok"
        assert result["message"] == "Success"

    def test_ok_custom_message(self):
        result = ok("Done!")
        assert result["message"] == "Done!"

    def test_paginate_first_page(self):
        items = list(range(100))
        assert paginate(items, skip=0, limit=10) == list(range(10))

    def test_paginate_second_page(self):
        items = list(range(100))
        assert paginate(items, skip=10, limit=10) == list(range(10, 20))

    def test_paginate_beyond_end(self):
        items = list(range(5))
        assert paginate(items, skip=10, limit=10) == []

    def test_paginate_partial(self):
        items = list(range(15))
        result = paginate(items, skip=10, limit=10)
        assert result == [10, 11, 12, 13, 14]
