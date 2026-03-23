"""
Tests for POST /upload/avatar and POST /upload/post-image.
"""

import io
import pytest
from PIL import Image as PILImage
from .conftest import make_user, get_token, auth_headers


def _make_image_bytes(fmt: str = "JPEG", size: tuple = (100, 100)) -> bytes:
    """Create a minimal valid image file in memory."""
    buf = io.BytesIO()
    try:
        img = PILImage.new("RGB", size, color=(100, 150, 200))
        img.save(buf, format=fmt)
    except Exception:
        # If Pillow is not available, create a minimal JPEG header manually
        buf = io.BytesIO(
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
            b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
            b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
            b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\x1e\xff\xd9"
        )
    buf.seek(0)
    return buf.read()


def _image_file(filename: str = "test.jpg", content_type: str = "image/jpeg") -> tuple:
    """Return a (files dict, content) tuple for multipart upload."""
    data = _make_image_bytes()
    return {"file": (filename, io.BytesIO(data), content_type)}


class TestAvatarUpload:
    def test_upload_avatar_success(self, client, db):
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        res = client.post(
            "/upload/avatar",
            files=_image_file(),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        body = res.json()
        assert "url"      in body
        assert "filename" in body
        assert "size"     in body
        assert body["url"].startswith("/static/uploads/avatars/")

    def test_upload_avatar_updates_profile(self, client, db):
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        res = client.post(
            "/upload/avatar",
            files=_image_file(),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200

        # Profile should now have the new URL
        me = client.get("/users/me", headers=auth_headers(token)).json()
        assert me["profile_picture"] == res.json()["url"]

    def test_upload_avatar_wrong_type(self, client, db):
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        res = client.post(
            "/upload/avatar",
            files={"file": ("test.pdf", io.BytesIO(b"%PDF fake content"), "application/pdf")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 415

    def test_upload_avatar_requires_auth(self, client, db):
        res = client.post("/upload/avatar", files=_image_file())
        assert res.status_code == 401

    def test_upload_png(self, client, db):
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        res = client.post(
            "/upload/avatar",
            files=_image_file("pic.png", "image/png"),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert res.json()["url"].startswith("/static/uploads/avatars/")


class TestPostImageUpload:
    def test_upload_post_image_success(self, client, db):
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        res = client.post(
            "/upload/post-image",
            files=_image_file(),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["url"].startswith("/static/uploads/post_images/")

    def test_upload_post_image_wrong_type(self, client, db):
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")
        res = client.post(
            "/upload/post-image",
            files={"file": ("doc.txt", io.BytesIO(b"plain text"), "text/plain")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 415

    def test_upload_returned_url_usable_in_post(self, client, db):
        """Full workflow: upload image → create post with its URL."""
        make_user(db)
        token = get_token(client, "test@college.edu", "password123")

        upload_res = client.post(
            "/upload/post-image",
            files=_image_file(),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert upload_res.status_code == 200
        image_url = upload_res.json()["url"]

        post_res = client.post(
            "/posts",
            json={"content": "Post with uploaded image", "image_url": image_url},
            headers=auth_headers(token),
        )
        assert post_res.status_code == 201
        assert post_res.json()["image_url"] == image_url

    def test_upload_requires_auth(self, client, db):
        res = client.post("/upload/post-image", files=_image_file())
        assert res.status_code == 401
