"""
Tests for /messages and /mentorship endpoints.
"""

import pytest
from .conftest import make_user, get_token, auth_headers


# ══════════════════════════════════════════════════════════════════════════════
#  Messages
# ══════════════════════════════════════════════════════════════════════════════

class TestMessages:
    def test_send_message(self, client, db):
        sender   = make_user(db, email="sender@college.edu")
        receiver = make_user(db, email="recv@college.edu")
        token    = get_token(client, "sender@college.edu", "password123")
        res = client.post("/messages",
                          json={"receiver_id": receiver.id, "content": "Hello!"},
                          headers=auth_headers(token))
        assert res.status_code == 201
        body = res.json()
        assert body["sender_id"]   == sender.id
        assert body["receiver_id"] == receiver.id
        assert body["content"]     == "Hello!"
        assert body["is_read"]     is False

    def test_send_message_to_self_rejected(self, client, db):
        user  = make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        res = client.post("/messages",
                          json={"receiver_id": user.id, "content": "Talking to myself"},
                          headers=auth_headers(token))
        assert res.status_code == 400

    def test_send_message_to_nonexistent_user(self, client, db):
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        res = client.post("/messages",
                          json={"receiver_id": 9999, "content": "Hi ghost"},
                          headers=auth_headers(token))
        assert res.status_code == 404

    def test_get_conversation(self, client, db):
        u1 = make_user(db, email="u1@college.edu")
        u2 = make_user(db, email="u2@college.edu")
        t1 = get_token(client, "u1@college.edu", "password123")
        t2 = get_token(client, "u2@college.edu", "password123")

        # Exchange 3 messages
        client.post("/messages", json={"receiver_id": u2.id, "content": "Hi"},
                    headers=auth_headers(t1))
        client.post("/messages", json={"receiver_id": u1.id, "content": "Hey!"},
                    headers=auth_headers(t2))
        client.post("/messages", json={"receiver_id": u2.id, "content": "How are you?"},
                    headers=auth_headers(t1))

        res = client.get(f"/messages/{u2.id}", headers=auth_headers(t1))
        assert res.status_code == 200
        assert len(res.json()) == 3

    def test_conversation_marks_messages_read(self, client, db):
        sender   = make_user(db, email="sender@college.edu")
        receiver = make_user(db, email="recv@college.edu")
        t_s = get_token(client, "sender@college.edu",   "password123")
        t_r = get_token(client, "recv@college.edu",     "password123")

        client.post("/messages", json={"receiver_id": receiver.id, "content": "Mark me read"},
                    headers=auth_headers(t_s))

        # Receiver fetches conversation — should mark as read
        msgs = client.get(f"/messages/{sender.id}", headers=auth_headers(t_r)).json()
        assert msgs[0]["is_read"] is True

    def test_conversations_list(self, client, db):
        u1 = make_user(db, email="u1@college.edu")
        u2 = make_user(db, email="u2@college.edu")
        u3 = make_user(db, email="u3@college.edu")
        t1 = get_token(client, "u1@college.edu", "password123")
        t2 = get_token(client, "u2@college.edu", "password123")
        t3 = get_token(client, "u3@college.edu", "password123")

        client.post("/messages", json={"receiver_id": u2.id, "content": "A"},
                    headers=auth_headers(t1))
        client.post("/messages", json={"receiver_id": u3.id, "content": "B"},
                    headers=auth_headers(t1))

        res = client.get("/messages/conversations", headers=auth_headers(t1))
        assert res.status_code == 200
        assert len(res.json()) == 2     # u1 has talked to u2 and u3

    def test_empty_message_rejected(self, client, db):
        u1 = make_user(db, email="u1@college.edu")
        u2 = make_user(db, email="u2@college.edu")
        t1 = get_token(client, "u1@college.edu", "password123")
        res = client.post("/messages",
                          json={"receiver_id": u2.id, "content": "   "},
                          headers=auth_headers(t1))
        assert res.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
#  Mentorship
# ══════════════════════════════════════════════════════════════════════════════

class TestMentorship:
    def _setup(self, db):
        student = make_user(db, email="student@college.edu", role="student")
        alumni  = make_user(db, email="alumni@college.edu",  role="alumni")
        return student, alumni

    def test_student_sends_request(self, client, db):
        student, alumni = self._setup(db)
        token = get_token(client, "student@college.edu", "password123")
        res = client.post("/mentorship",
                          json={"alumni_id": alumni.id, "message": "Please mentor me!"},
                          headers=auth_headers(token))
        assert res.status_code == 201
        body = res.json()
        assert body["student_id"] == student.id
        assert body["alumni_id"]  == alumni.id
        assert body["status"]     == "pending"

    def test_alumni_cannot_send_request(self, client, db):
        _, alumni = self._setup(db)
        token = get_token(client, "alumni@college.edu", "password123")
        res = client.post("/mentorship",
                          json={"alumni_id": alumni.id},
                          headers=auth_headers(token))
        assert res.status_code == 403

    def test_duplicate_pending_rejected(self, client, db):
        _, alumni = self._setup(db)
        token = get_token(client, "student@college.edu", "password123")
        client.post("/mentorship", json={"alumni_id": alumni.id}, headers=auth_headers(token))
        res = client.post("/mentorship", json={"alumni_id": alumni.id}, headers=auth_headers(token))
        assert res.status_code == 409

    def test_alumni_accepts_request(self, client, db):
        _, alumni = self._setup(db)
        t_student = get_token(client, "student@college.edu", "password123")
        t_alumni  = get_token(client, "alumni@college.edu",  "password123")

        req_id = client.post("/mentorship", json={"alumni_id": alumni.id},
                             headers=auth_headers(t_student)).json()["id"]

        res = client.put(f"/mentorship/{req_id}",
                         json={"status": "accepted"},
                         headers=auth_headers(t_alumni))
        assert res.status_code == 200
        assert res.json()["status"] == "accepted"

    def test_alumni_rejects_request(self, client, db):
        _, alumni = self._setup(db)
        t_student = get_token(client, "student@college.edu", "password123")
        t_alumni  = get_token(client, "alumni@college.edu",  "password123")

        req_id = client.post("/mentorship", json={"alumni_id": alumni.id},
                             headers=auth_headers(t_student)).json()["id"]
        res = client.put(f"/mentorship/{req_id}",
                         json={"status": "rejected"},
                         headers=auth_headers(t_alumni))
        assert res.json()["status"] == "rejected"

    def test_student_cannot_respond_to_request(self, client, db):
        student, alumni = self._setup(db)
        t_student = get_token(client, "student@college.edu", "password123")
        t_alumni  = get_token(client, "alumni@college.edu",  "password123")

        req_id = client.post("/mentorship", json={"alumni_id": alumni.id},
                             headers=auth_headers(t_student)).json()["id"]
        res = client.put(f"/mentorship/{req_id}",
                         json={"status": "accepted"},
                         headers=auth_headers(t_student))
        assert res.status_code == 403

    def test_cannot_respond_twice(self, client, db):
        _, alumni = self._setup(db)
        t_student = get_token(client, "student@college.edu", "password123")
        t_alumni  = get_token(client, "alumni@college.edu",  "password123")

        req_id = client.post("/mentorship", json={"alumni_id": alumni.id},
                             headers=auth_headers(t_student)).json()["id"]
        client.put(f"/mentorship/{req_id}", json={"status": "accepted"},
                   headers=auth_headers(t_alumni))
        res = client.put(f"/mentorship/{req_id}", json={"status": "rejected"},
                         headers=auth_headers(t_alumni))
        assert res.status_code == 400

    def test_my_requests_student(self, client, db):
        _, alumni = self._setup(db)
        token = get_token(client, "student@college.edu", "password123")
        client.post("/mentorship", json={"alumni_id": alumni.id}, headers=auth_headers(token))
        res = client.get("/mentorship/my-requests", headers=auth_headers(token))
        assert res.status_code == 200
        assert len(res.json()) == 1

    def test_pending_endpoint_for_alumni(self, client, db):
        _, alumni = self._setup(db)
        t_student = get_token(client, "student@college.edu", "password123")
        t_alumni  = get_token(client, "alumni@college.edu",  "password123")
        client.post("/mentorship", json={"alumni_id": alumni.id},
                    headers=auth_headers(t_student))
        res = client.get("/mentorship/pending", headers=auth_headers(t_alumni))
        assert res.status_code == 200
        assert len(res.json()) == 1

    def test_pending_endpoint_non_alumni_forbidden(self, client, db):
        make_user(db, email="s@college.edu", role="student")
        token = get_token(client, "s@college.edu", "password123")
        res = client.get("/mentorship/pending", headers=auth_headers(token))
        assert res.status_code == 403
