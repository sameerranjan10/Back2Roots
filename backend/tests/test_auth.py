"""
Tests for POST /auth/register and POST /auth/login.
"""

import pytest
from .conftest import make_user, get_token, auth_headers


# ══════════════════════════════════════════════════════════════════════════════
#  Registration
# ══════════════════════════════════════════════════════════════════════════════

class TestRegister:
    def test_register_student_success(self, client):
        res = client.post("/auth/register", json={
            "name":    "Alice Student",
            "email":   "alice@college.edu",
            "password":"password123",
            "role":    "student",
            "college": "Test College",
            "skills":  "Python, ML",
        })
        assert res.status_code == 201
        body = res.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["user"]["email"] == "alice@college.edu"
        assert body["user"]["role"]  == "student"

    def test_register_alumni_success(self, client):
        res = client.post("/auth/register", json={
            "name":    "Bob Alumni",
            "email":   "bob@alumni.college.edu",
            "password":"password123",
            "role":    "alumni",
        })
        assert res.status_code == 201
        assert res.json()["user"]["role"] == "alumni"

    def test_register_duplicate_email(self, client, db):
        make_user(db, email="dup@college.edu")
        res = client.post("/auth/register", json={
            "name":    "Dupe User",
            "email":   "dup@college.edu",
            "password":"password123",
            "role":    "student",
        })
        assert res.status_code == 400
        assert "already" in res.json()["detail"].lower()

    def test_register_short_password(self, client):
        res = client.post("/auth/register", json={
            "name":    "Short PW",
            "email":   "shortpw@college.edu",
            "password":"123",
            "role":    "student",
        })
        assert res.status_code == 422   # Pydantic validation error

    def test_register_invalid_email(self, client):
        res = client.post("/auth/register", json={
            "name":    "Bad Email",
            "email":   "not-an-email",
            "password":"password123",
            "role":    "student",
        })
        assert res.status_code == 422

    def test_register_missing_required_fields(self, client):
        res = client.post("/auth/register", json={"email": "noname@college.edu"})
        assert res.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
#  Login
# ══════════════════════════════════════════════════════════════════════════════

class TestLogin:
    def test_login_success(self, client, db):
        make_user(db, email="login@college.edu", password="secret99")
        res = client.post("/auth/login", json={
            "email":    "login@college.edu",
            "password": "secret99",
        })
        assert res.status_code == 200
        assert "access_token" in res.json()

    def test_login_wrong_password(self, client, db):
        make_user(db, email="pw@college.edu", password="correct")
        res = client.post("/auth/login", json={
            "email":    "pw@college.edu",
            "password": "wrong",
        })
        assert res.status_code == 401

    def test_login_unknown_email(self, client):
        res = client.post("/auth/login", json={
            "email":    "ghost@college.edu",
            "password": "anything",
        })
        assert res.status_code == 401

    def test_token_is_usable(self, client, db):
        make_user(db, email="tok@college.edu", password="tokpass")
        token = get_token(client, "tok@college.edu", "tokpass")
        res = client.get("/users/me", headers=auth_headers(token))
        assert res.status_code == 200
        assert res.json()["email"] == "tok@college.edu"

    def test_no_token_returns_401(self, client):
        res = client.get("/users/me")
        assert res.status_code == 401

    def test_bad_token_returns_401(self, client):
        res = client.get("/users/me", headers={"Authorization": "Bearer this.is.invalid"})
        assert res.status_code == 401
