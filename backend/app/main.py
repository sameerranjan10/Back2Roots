"""
Alumni Nexus — AI-Driven Alumni Management and Networking Platform
FastAPI application entry point — all routers, middleware, static files.
"""

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import engine, Base
from .config import settings
from .routes import (
    auth_routes,
    user_routes,
    post_routes,
    message_routes,
    mentorship_routes,
    ai_routes,
    search_routes,
    upload_routes,
    notification_routes,
)

# ── Create all database tables (includes Notification table) ───────────────────
Base.metadata.create_all(bind=engine)

# ── Ensure upload directories exist ───────────────────────────────────────────
Path("uploads/avatars").mkdir(parents=True, exist_ok=True)
Path("uploads/post_images").mkdir(parents=True, exist_ok=True)

# ── Application ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Alumni Nexus API",
    description=(
        "## AI-Driven Alumni Management and Networking Platform\n\n"
        "A college-ecosystem REST API powering:\n"
        "- 🔐 JWT authentication with rate limiting & password reset\n"
        "- 👤 User profiles with file upload support\n"
        "- 📰 LinkedIn-style post feed with likes & comments\n"
        "- 🔍 Full-text search across users and posts\n"
        "- 💬 One-to-one messaging with read receipts\n"
        "- 🎓 Mentorship request workflow\n"
        "- 🔔 Real-time-style notification system\n"
        "- 🤖 AI recommendation engine + career chatbot\n"
        "- 🛡️ Admin panel with user management\n\n"
        "**Authentication:** Use `POST /auth/login` to obtain a JWT, "
        "then click **Authorize** and enter `Bearer <token>`."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    debug=settings.DEBUG,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static file serving (uploaded files) ──────────────────────────────────────
app.mount("/static/uploads", StaticFiles(directory="uploads"), name="uploads")

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_routes.router)
app.include_router(user_routes.router)
app.include_router(post_routes.router)
app.include_router(message_routes.router)
app.include_router(mentorship_routes.router)
app.include_router(ai_routes.router)
app.include_router(search_routes.router)
app.include_router(upload_routes.router)
app.include_router(notification_routes.router)

# ── Health endpoints ──────────────────────────────────────────────────────────
@app.get("/", tags=["Health"], summary="Root health check")
def root():
    return {
        "status":  "online",
        "app":     settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs":    "/docs",
    }

@app.get("/health", tags=["Health"], summary="Health probe")
def health():
    return {"status": "healthy"}
