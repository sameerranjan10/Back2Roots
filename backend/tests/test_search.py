"""
Tests for GET /search and GET /search/users.
"""

import pytest
from .conftest import make_user, get_token, auth_headers


class TestSearch:
    def _setup(self, db):
        make_user(db, name="Alice Python",   email="alice@c.edu",  role="alumni",  skills="Python, ML",    college="IIT")
        make_user(db, name="Bob Java",       email="bob@c.edu",    role="student", skills="Java, Spring",  college="NIT")
        make_user(db, name="Carol Rust",     email="carol@c.edu",  role="alumni",  skills="Rust, Systems", college="IIT")
        viewer = make_user(db, name="Viewer", email="viewer@c.edu", role="student")
        return viewer

    def test_search_users_by_name(self, client, db):
        viewer = self._setup(db)
        token = get_token(client, "viewer@c.edu", "password123")
        res = client.get("/search?q=Alice&type=users", headers=auth_headers(token))
        assert res.status_code == 200
        body = res.json()
        assert body["total_users"] >= 1
        names = [u["name"] for u in body["users"]]
        assert any("Alice" in n for n in names)

    def test_search_users_by_skill(self, client, db):
        viewer = self._setup(db)
        token = get_token(client, "viewer@c.edu", "password123")
        res = client.get("/search?q=Rust&type=users", headers=auth_headers(token))
        assert res.status_code == 200
        assert res.json()["total_users"] >= 1

    def test_search_users_by_college(self, client, db):
        viewer = self._setup(db)
        token = get_token(client, "viewer@c.edu", "password123")
        res = client.get("/search?q=NIT&type=users", headers=auth_headers(token))
        assert res.status_code == 200
        users = res.json()["users"]
        assert any(u.get("college") == "NIT" for u in users)

    def test_search_posts(self, client, db):
        make_user(db, email="poster@c.edu")
        token = get_token(client, "poster@c.edu", "password123")
        client.post("/posts", json={"content": "Learning FastAPI is amazing!"}, headers=auth_headers(token))
        res = client.get("/search?q=FastAPI&type=posts", headers=auth_headers(token))
        assert res.status_code == 200
        assert res.json()["total_posts"] >= 1

    def test_search_all_returns_both(self, client, db):
        make_user(db, name="Django Fan", email="d@c.edu", role="alumni", skills="Django")
        token = get_token(client, "d@c.edu", "password123")
        client.post("/posts", json={"content": "Django is great!"}, headers=auth_headers(token))
        make_user(db, name="Viewer", email="v@c.edu")
        t2 = get_token(client, "v@c.edu", "password123")
        res = client.get("/search?q=Django&type=all", headers=auth_headers(t2))
        assert res.status_code == 200
        body = res.json()
        assert "users" in body
        assert "posts" in body

    def test_search_no_results(self, client, db):
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        res = client.get("/search?q=xyzzynonexistent&type=all", headers=auth_headers(token))
        assert res.status_code == 200
        body = res.json()
        assert body["total_users"] == 0
        assert body["total_posts"] == 0

    def test_search_requires_query(self, client, db):
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        res = client.get("/search", headers=auth_headers(token))
        assert res.status_code == 422   # q is required

    def test_search_requires_auth(self, client, db):
        res = client.get("/search?q=test")
        assert res.status_code == 401


class TestSearchUsers:
    def test_user_quick_search(self, client, db):
        make_user(db, name="SearchMe User", email="sm@c.edu", role="alumni")
        make_user(db, email="searcher@c.edu")
        token = get_token(client, "searcher@c.edu", "password123")
        res = client.get("/search/users?q=SearchMe", headers=auth_headers(token))
        assert res.status_code == 200
        assert len(res.json()) >= 1

    def test_user_quick_search_excludes_self(self, client, db):
        user = make_user(db, name="Myself", email="me@c.edu")
        token = get_token(client, "me@c.edu", "password123")
        res = client.get("/search/users?q=Myself", headers=auth_headers(token))
        assert res.status_code == 200
        ids = [u["id"] for u in res.json()]
        assert user.id not in ids

    def test_user_quick_search_filter_by_role(self, client, db):
        make_user(db, name="Alumni One", email="a@c.edu",  role="alumni")
        make_user(db, name="Stu One",    email="s@c.edu",  role="student")
        make_user(db, email="v@c.edu")
        token = get_token(client, "v@c.edu", "password123")
        res = client.get("/search/users?q=One&role=alumni", headers=auth_headers(token))
        assert res.status_code == 200
        roles = [u["role"] for u in res.json()]
        assert all(r == "alumni" for r in roles)
