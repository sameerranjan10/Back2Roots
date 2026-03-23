"""
Tests for /ai/recommendations and /ai/chatbot.
"""

import pytest
from .conftest import make_user, get_token, auth_headers


class TestRecommendations:
    def test_recommendations_returns_list(self, client, db):
        make_user(db, email="student@c.edu", role="student", skills="Python, ML")
        make_user(db, email="alumni1@c.edu", role="alumni",  skills="Python, ML, TensorFlow")
        make_user(db, email="alumni2@c.edu", role="alumni",  skills="React, Node.js")
        token = get_token(client, "student@c.edu", "password123")
        res = client.get("/ai/recommendations", headers=auth_headers(token))
        assert res.status_code == 200
        body = res.json()
        assert isinstance(body, list)
        for rec in body:
            assert "user"   in rec
            assert "score"  in rec
            assert "reason" in rec
            assert rec["user"]["role"] == "alumni"

    def test_recommendations_sorted_by_score(self, client, db):
        make_user(db, email="student@c.edu", role="student", skills="Python, ML")
        make_user(db, email="best@c.edu",   role="alumni",  skills="Python, ML, TensorFlow")
        make_user(db, email="worst@c.edu",  role="alumni",  skills="Java, Spring")
        token = get_token(client, "student@c.edu", "password123")
        recs = client.get("/ai/recommendations", headers=auth_headers(token)).json()
        scores = [r["score"] for r in recs]
        assert scores == sorted(scores, reverse=True)

    def test_recommendations_excludes_self(self, client, db):
        """A user should never be recommended to themselves."""
        user  = make_user(db, email="alumni@c.edu", role="alumni", skills="Python")
        token = get_token(client, "alumni@c.edu", "password123")
        recs  = client.get("/ai/recommendations", headers=auth_headers(token)).json()
        ids   = [r["user"]["id"] for r in recs]
        assert user.id not in ids

    def test_recommendations_no_alumni_returns_empty(self, client, db):
        make_user(db, role="student")
        token = get_token(client, "test@college.edu", "password123")
        recs  = client.get("/ai/recommendations", headers=auth_headers(token)).json()
        assert recs == []

    def test_same_college_boosts_score(self, client, db):
        """Alumni from the same college should score higher than an equally-skilled stranger."""
        student  = make_user(db, email="s@c.edu",  role="student", college="IIT", skills="Python")
        same_col = make_user(db, email="a1@c.edu", role="alumni",  college="IIT", skills="Java")
        diff_col = make_user(db, email="a2@c.edu", role="alumni",  college="MIT", skills="Java")
        token    = get_token(client, "s@c.edu", "password123")
        recs = client.get("/ai/recommendations", headers=auth_headers(token)).json()
        scores = {r["user"]["id"]: r["score"] for r in recs}
        assert scores[same_col.id] > scores[diff_col.id]


class TestChatbot:
    def _chat(self, client, token, message):
        return client.post("/ai/chatbot", json={"message": message},
                           headers=auth_headers(token))

    def test_chatbot_help_response(self, client, db):
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        res = self._chat(client, token, "help")
        assert res.status_code == 200
        body = res.json()
        assert "reply"       in body
        assert "suggestions" in body
        assert len(body["reply"]) > 10

    def test_chatbot_resume_keyword(self, client, db):
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        res = self._chat(client, token, "How do I write a resume?")
        assert res.status_code == 200
        assert "resume" in res.json()["reply"].lower()

    def test_chatbot_interview_keyword(self, client, db):
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        res = self._chat(client, token, "interview tips please")
        assert "interview" in res.json()["reply"].lower()

    def test_chatbot_mentor_returns_suggestions(self, client, db):
        make_user(db, email="s@c.edu",  role="student", skills="Python")
        make_user(db, email="a1@c.edu", role="alumni",  skills="Python, ML")
        make_user(db, email="a2@c.edu", role="alumni",  skills="Java")
        token = get_token(client, "s@c.edu", "password123")
        res = self._chat(client, token, "suggest a mentor for me")
        assert res.status_code == 200
        body = res.json()
        assert isinstance(body["suggestions"], list)

    def test_chatbot_unknown_topic(self, client, db):
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        res = self._chat(client, token, "xyzzy frobnicator plonk")
        assert res.status_code == 200
        assert len(res.json()["reply"]) > 0   # always returns a fallback

    def test_chatbot_requires_auth(self, client, db):
        res = client.post("/ai/chatbot", json={"message": "hi"})
        assert res.status_code == 401
