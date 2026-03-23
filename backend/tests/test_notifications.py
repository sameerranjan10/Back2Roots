"""
Tests for the notification system.
Verifies notification creation and endpoint behaviour.
"""

import pytest
from .conftest import make_user, get_token, auth_headers
from app.routes.notification_routes import Notification, create_notification


class TestNotificationEndpoints:
    def test_get_notifications_empty(self, client, db):
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        res = client.get("/notifications", headers=auth_headers(token))
        assert res.status_code == 200
        assert res.json() == []

    def test_unread_count_zero_initially(self, client, db):
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        res = client.get("/notifications/unread", headers=auth_headers(token))
        assert res.status_code == 200
        assert res.json()["unread_count"] == 0

    def test_notification_appears_after_creation(self, client, db):
        user = make_user(db)
        token = get_token(client, "test@college.edu", "password123")

        # Manually create a notification
        create_notification(db, user.id, "system", "Welcome to Alumni Nexus!")
        db.commit()

        res = client.get("/notifications", headers=auth_headers(token))
        assert res.status_code == 200
        assert len(res.json()) == 1
        assert res.json()[0]["type"]    == "system"
        assert res.json()[0]["is_read"] is False

    def test_unread_count_increments(self, client, db):
        user = make_user(db)
        token = get_token(client, "test@college.edu", "password123")

        create_notification(db, user.id, "like",    "Someone liked your post")
        create_notification(db, user.id, "comment", "Someone commented")
        db.commit()

        res = client.get("/notifications/unread", headers=auth_headers(token))
        assert res.json()["unread_count"] == 2

    def test_mark_all_read(self, client, db):
        user = make_user(db)
        token = get_token(client, "test@college.edu", "password123")

        create_notification(db, user.id, "system", "Notif 1")
        create_notification(db, user.id, "system", "Notif 2")
        db.commit()

        res = client.put("/notifications/read-all", headers=auth_headers(token))
        assert res.status_code == 204

        count = client.get("/notifications/unread", headers=auth_headers(token))
        assert count.json()["unread_count"] == 0

    def test_mark_single_read(self, client, db):
        user = make_user(db)
        token = get_token(client, "test@college.edu", "password123")

        create_notification(db, user.id, "system", "Notif 1")
        create_notification(db, user.id, "system", "Notif 2")
        db.commit()

        notifs = client.get("/notifications", headers=auth_headers(token)).json()
        target_id = notifs[0]["id"]

        res = client.put(f"/notifications/{target_id}/read", headers=auth_headers(token))
        assert res.status_code == 204

        count = client.get("/notifications/unread", headers=auth_headers(token))
        assert count.json()["unread_count"] == 1   # one still unread

    def test_cannot_read_others_notification(self, client, db):
        owner   = make_user(db, email="owner@c.edu")
        other   = make_user(db, email="other@c.edu")
        t_other = get_token(client, "other@c.edu", "password123")

        create_notification(db, owner.id, "system", "Owner's notif")
        db.commit()

        notifs = db.query(Notification).filter(Notification.user_id == owner.id).all()
        notif_id = notifs[0].id

        res = client.put(f"/notifications/{notif_id}/read", headers=auth_headers(t_other))
        assert res.status_code == 404   # other user can't see it

    def test_notifications_requires_auth(self, client, db):
        assert client.get("/notifications").status_code        == 401
        assert client.get("/notifications/unread").status_code == 401
        assert client.put("/notifications/read-all").status_code == 401

    def test_pagination(self, client, db):
        user  = make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        for i in range(15):
            create_notification(db, user.id, "system", f"Notif {i}")
        db.commit()

        res = client.get("/notifications?skip=0&limit=5", headers=auth_headers(token))
        assert res.status_code == 200
        assert len(res.json()) == 5

        res2 = client.get("/notifications?skip=5&limit=5", headers=auth_headers(token))
        assert len(res2.json()) == 5


class TestNotificationTriggering:
    """Verify that notifications are created by other routes."""

    def test_like_triggers_notification(self, client, db):
        author  = make_user(db, email="author@c.edu")
        liker   = make_user(db, email="liker@c.edu")
        t_auth  = get_token(client, "author@c.edu", "password123")
        t_liker = get_token(client, "liker@c.edu",  "password123")

        post_id = client.post("/posts",
                              json={"content": "Test post"},
                              headers=auth_headers(t_auth)).json()["id"]
        client.post("/likes", json={"post_id": post_id}, headers=auth_headers(t_liker))

        notifs = client.get("/notifications", headers=auth_headers(t_auth)).json()
        types  = [n["type"] for n in notifs]
        assert "like" in types

    def test_comment_triggers_notification(self, client, db):
        author    = make_user(db, email="author@c.edu")
        commenter = make_user(db, email="cmt@c.edu")
        t_auth    = get_token(client, "author@c.edu", "password123")
        t_cmt     = get_token(client, "cmt@c.edu",    "password123")

        post_id = client.post("/posts",
                              json={"content": "Post"},
                              headers=auth_headers(t_auth)).json()["id"]
        client.post("/comments",
                    json={"post_id": post_id, "content": "Nice post!"},
                    headers=auth_headers(t_cmt))

        notifs = client.get("/notifications", headers=auth_headers(t_auth)).json()
        assert any(n["type"] == "comment" for n in notifs)

    def test_message_triggers_notification(self, client, db):
        receiver = make_user(db, email="recv@c.edu")
        sender   = make_user(db, email="send@c.edu")
        t_send   = get_token(client, "send@c.edu", "password123")
        t_recv   = get_token(client, "recv@c.edu", "password123")

        client.post("/messages",
                    json={"receiver_id": receiver.id, "content": "Hello!"},
                    headers=auth_headers(t_send))

        notifs = client.get("/notifications", headers=auth_headers(t_recv)).json()
        assert any(n["type"] == "message" for n in notifs)

    def test_mentorship_request_triggers_notification(self, client, db):
        student = make_user(db, email="stu@c.edu", role="student")
        alumni  = make_user(db, email="alm@c.edu", role="alumni")
        t_stu   = get_token(client, "stu@c.edu", "password123")
        t_alm   = get_token(client, "alm@c.edu", "password123")

        client.post("/mentorship",
                    json={"alumni_id": alumni.id, "message": "Hi!"},
                    headers=auth_headers(t_stu))

        notifs = client.get("/notifications", headers=auth_headers(t_alm)).json()
        assert any(n["type"] == "mentorship_request" for n in notifs)

    def test_mentorship_response_triggers_notification(self, client, db):
        student = make_user(db, email="stu@c.edu", role="student")
        alumni  = make_user(db, email="alm@c.edu", role="alumni")
        t_stu   = get_token(client, "stu@c.edu", "password123")
        t_alm   = get_token(client, "alm@c.edu", "password123")

        req_id = client.post("/mentorship",
                             json={"alumni_id": alumni.id},
                             headers=auth_headers(t_stu)).json()["id"]
        client.put(f"/mentorship/{req_id}",
                   json={"status": "accepted"},
                   headers=auth_headers(t_alm))

        notifs = client.get("/notifications", headers=auth_headers(t_stu)).json()
        assert any(n["type"] == "mentorship_update" for n in notifs)

    def test_self_like_does_not_notify(self, client, db):
        """Liking your own post should NOT create a notification."""
        user  = make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        post_id = client.post("/posts",
                              json={"content": "My post"},
                              headers=auth_headers(token)).json()["id"]
        client.post("/likes", json={"post_id": post_id}, headers=auth_headers(token))

        notifs = client.get("/notifications", headers=auth_headers(token)).json()
        like_notifs = [n for n in notifs if n["type"] == "like"]
        assert len(like_notifs) == 0
