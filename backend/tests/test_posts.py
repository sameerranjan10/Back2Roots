"""
Tests for /posts, /comments, and /likes.
"""

import pytest
from .conftest import make_user, get_token, auth_headers


def _create_post(client, token, content="Hello world!", image_url=None):
    return client.post(
        "/posts",
        json={"content": content, "image_url": image_url},
        headers=auth_headers(token),
    )


class TestPosts:
    def test_create_post(self, client, db):
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        res = _create_post(client, token, "My first post!")
        assert res.status_code == 201
        body = res.json()
        assert body["content"]    == "My first post!"
        assert body["likes_count"] == 0
        assert body["liked_by_me"] is False
        assert "author" in body

    def test_create_post_with_image(self, client, db):
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        res = _create_post(client, token, "With image", "https://example.com/img.png")
        assert res.status_code == 201
        assert res.json()["image_url"] == "https://example.com/img.png"

    def test_create_empty_post_rejected(self, client, db):
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        res = _create_post(client, token, "   ")
        assert res.status_code == 422

    def test_get_feed(self, client, db):
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        _create_post(client, token, "Post A")
        _create_post(client, token, "Post B")
        _create_post(client, token, "Post C")
        res = client.get("/posts", headers=auth_headers(token))
        assert res.status_code == 200
        assert len(res.json()) == 3

    def test_feed_newest_first(self, client, db):
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        _create_post(client, token, "First")
        _create_post(client, token, "Second")
        _create_post(client, token, "Third")
        posts = client.get("/posts", headers=auth_headers(token)).json()
        assert posts[0]["content"] == "Third"

    def test_get_user_posts(self, client, db):
        u1 = make_user(db, email="u1@college.edu")
        u2 = make_user(db, email="u2@college.edu")
        t1 = get_token(client, "u1@college.edu", "password123")
        t2 = get_token(client, "u2@college.edu", "password123")
        _create_post(client, t1, "U1 post")
        _create_post(client, t2, "U2 post")
        res = client.get(f"/posts/user/{u1.id}", headers=auth_headers(t1))
        assert res.status_code == 200
        assert len(res.json()) == 1
        assert res.json()[0]["user_id"] == u1.id

    def test_delete_own_post(self, client, db):
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        post_id = _create_post(client, token).json()["id"]
        res = client.delete(f"/posts/{post_id}", headers=auth_headers(token))
        assert res.status_code == 204

    def test_delete_other_users_post_forbidden(self, client, db):
        make_user(db, email="owner@college.edu")
        make_user(db, email="thief@college.edu")
        t_owner = get_token(client, "owner@college.edu", "password123")
        t_thief = get_token(client, "thief@college.edu", "password123")
        post_id = _create_post(client, t_owner).json()["id"]
        res = client.delete(f"/posts/{post_id}", headers=auth_headers(t_thief))
        assert res.status_code == 403

    def test_admin_can_delete_any_post(self, client, db):
        make_user(db, email="poster@college.edu")
        make_user(db, email="admin@college.edu", role="admin")
        t_poster = get_token(client, "poster@college.edu", "password123")
        t_admin  = get_token(client, "admin@college.edu",  "password123")
        post_id  = _create_post(client, t_poster).json()["id"]
        res = client.delete(f"/posts/{post_id}", headers=auth_headers(t_admin))
        assert res.status_code == 204

    def test_delete_nonexistent_post(self, client, db):
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        res = client.delete("/posts/9999", headers=auth_headers(token))
        assert res.status_code == 404


class TestComments:
    def test_add_comment(self, client, db):
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        post_id = _create_post(client, token).json()["id"]
        res = client.post("/comments",
                          json={"post_id": post_id, "content": "Great post!"},
                          headers=auth_headers(token))
        assert res.status_code == 201
        body = res.json()
        assert body["content"] == "Great post!"
        assert "author" in body

    def test_comment_on_nonexistent_post(self, client, db):
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        res = client.post("/comments",
                          json={"post_id": 9999, "content": "Hmm"},
                          headers=auth_headers(token))
        assert res.status_code == 404

    def test_delete_own_comment(self, client, db):
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        post_id    = _create_post(client, token).json()["id"]
        comment_id = client.post("/comments",
                                 json={"post_id": post_id, "content": "Temp"},
                                 headers=auth_headers(token)).json()["id"]
        res = client.delete(f"/comments/{comment_id}", headers=auth_headers(token))
        assert res.status_code == 204


class TestLikes:
    def test_like_post(self, client, db):
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        post_id = _create_post(client, token).json()["id"]
        res = client.post("/likes", json={"post_id": post_id},
                          headers=auth_headers(token))
        assert res.status_code == 200
        body = res.json()
        assert body["liked"]       is True
        assert body["likes_count"] == 1

    def test_unlike_post(self, client, db):
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        post_id = _create_post(client, token).json()["id"]
        # Like first
        client.post("/likes", json={"post_id": post_id}, headers=auth_headers(token))
        # Unlike
        res = client.post("/likes", json={"post_id": post_id}, headers=auth_headers(token))
        assert res.json()["liked"]       is False
        assert res.json()["likes_count"] == 0

    def test_like_nonexistent_post(self, client, db):
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        res = client.post("/likes", json={"post_id": 9999}, headers=auth_headers(token))
        assert res.status_code == 404

    def test_like_count_across_users(self, client, db):
        make_user(db, email="u1@college.edu")
        make_user(db, email="u2@college.edu")
        t1 = get_token(client, "u1@college.edu", "password123")
        t2 = get_token(client, "u2@college.edu", "password123")
        post_id = _create_post(client, t1).json()["id"]
        client.post("/likes", json={"post_id": post_id}, headers=auth_headers(t1))
        res = client.post("/likes", json={"post_id": post_id}, headers=auth_headers(t2))
        assert res.json()["likes_count"] == 2
