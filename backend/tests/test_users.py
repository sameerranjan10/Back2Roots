"""
Tests for /users/me, /users/alumni, /users/{id}, and admin endpoints.
"""

import pytest
from .conftest import make_user, get_token, auth_headers


class TestMyProfile:
    def test_get_me(self, client, db):
        make_user(db, name="Me User", email="me@college.edu")
        token = get_token(client, "me@college.edu", "password123")
        res = client.get("/users/me", headers=auth_headers(token))
        assert res.status_code == 200
        body = res.json()
        assert body["name"]  == "Me User"
        assert body["email"] == "me@college.edu"
        assert "password" not in body   # never expose hash

    def test_update_profile(self, client, db):
        make_user(db, email="upd@college.edu")
        token = get_token(client, "upd@college.edu", "password123")
        res = client.put("/users/me", json={"bio": "Updated bio", "skills": "Rust, Go"},
                         headers=auth_headers(token))
        assert res.status_code == 200
        body = res.json()
        assert body["bio"]    == "Updated bio"
        assert body["skills"] == "Rust, Go"

    def test_update_profile_partial(self, client, db):
        """Only provided fields are updated; others remain unchanged."""
        make_user(db, email="partial@college.edu", skills="Python")
        token = get_token(client, "partial@college.edu", "password123")
        res = client.put("/users/me", json={"bio": "New bio only"},
                         headers=auth_headers(token))
        assert res.status_code == 200
        body = res.json()
        assert body["bio"]    == "New bio only"
        assert body["skills"] == "Python"   # unchanged


class TestAlumniList:
    def test_get_alumni(self, client, db):
        make_user(db, email="alumni1@college.edu", role="alumni")
        make_user(db, email="alumni2@college.edu", role="alumni")
        make_user(db, email="student@college.edu", role="student")
        token = get_token(client, "student@college.edu", "password123")
        res = client.get("/users/alumni", headers=auth_headers(token))
        assert res.status_code == 200
        roles = [u["role"] for u in res.json()]
        assert all(r == "alumni" for r in roles)
        assert len(res.json()) == 2

    def test_get_public_profile(self, client, db):
        target = make_user(db, email="target@college.edu", name="Target User")
        viewer = make_user(db, email="viewer@college.edu")
        token  = get_token(client, "viewer@college.edu", "password123")
        res = client.get(f"/users/{target.id}", headers=auth_headers(token))
        assert res.status_code == 200
        assert res.json()["name"] == "Target User"

    def test_get_nonexistent_user(self, client, db):
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        res = client.get("/users/9999", headers=auth_headers(token))
        assert res.status_code == 404


class TestAdminPanel:
    def _make_admin(self, db, email="admin@college.edu"):
        return make_user(db, email=email, role="admin")

    def test_admin_list_users(self, client, db):
        self._make_admin(db)
        make_user(db, email="s1@college.edu", role="student")
        make_user(db, email="s2@college.edu", role="alumni")
        token = get_token(client, "admin@college.edu", "password123")
        res = client.get("/users/", headers=auth_headers(token))
        assert res.status_code == 200
        assert len(res.json()) == 3   # admin + 2 users

    def test_non_admin_cannot_list_all_users(self, client, db):
        make_user(db, email="nonadmin@college.edu", role="student")
        token = get_token(client, "nonadmin@college.edu", "password123")
        res = client.get("/users/", headers=auth_headers(token))
        assert res.status_code == 403

    def test_admin_delete_user(self, client, db):
        self._make_admin(db)
        victim = make_user(db, email="victim@college.edu", role="student")
        token = get_token(client, "admin@college.edu", "password123")
        res = client.delete(f"/users/{victim.id}", headers=auth_headers(token))
        assert res.status_code == 204
        # Verify gone
        res2 = client.get(f"/users/{victim.id}", headers=auth_headers(token))
        assert res2.status_code == 404

    def test_admin_cannot_delete_self(self, client, db):
        admin = self._make_admin(db)
        token = get_token(client, "admin@college.edu", "password123")
        res = client.delete(f"/users/{admin.id}", headers=auth_headers(token))
        assert res.status_code == 400
