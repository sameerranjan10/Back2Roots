# Back2Roots — AI-Driven Alumni Management Platform

A full-stack college networking platform with LinkedIn-style UI, AI recommendations, mentorship, messaging, and notifications.

---

## Project Structure

```
back2roots/
├── backend/                    ← FastAPI Python backend
│   ├── app/
│   │   ├── main.py             ← App entry point
│   │   ├── database.py         ← SQLAlchemy + MySQL
│   │   ├── models.py           ← ORM models (6 tables)
│   │   ├── schemas.py          ← Pydantic schemas
│   │   ├── auth.py             ← JWT + bcrypt
│   │   ├── config.py           ← Environment config
│   │   └── routes/
│   │       ├── auth_routes.py         POST /auth/register|login|forgot-password
│   │       ├── user_routes.py         GET|PUT /users/me, alumni list, admin
│   │       ├── post_routes.py         Feed, posts, comments, likes
│   │       ├── message_routes.py      One-to-one messaging
│   │       ├── mentorship_routes.py   Request workflow
│   │       ├── ai_routes.py           Recommendations + chatbot
│   │       ├── search_routes.py       Full-text search
│   │       ├── upload_routes.py       Avatar + image upload
│   │       └── notification_routes.py Real-time notifications
│   ├── tests/                  ← 87 pytest tests (SQLite in-memory)
│   ├── alembic/                ← Database migrations
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── Dockerfile
│   ├── run.py                  ← Dev server launcher
│   ├── create_admin.py         ← CLI admin account creator
│   ├── seed.py                 ← Demo data seeder
│   └── .env.example
│
├── frontend/                   ← Vanilla HTML/CSS/JS frontend
│   ├── index.html              ← Landing page
│   ├── login.html              ← JWT login
│   ├── signup.html             ← Registration
│   ├── dashboard.html          ← Main 3-column feed
│   ├── profile.html            ← User profile
│   ├── chat.html               ← Messaging
│   ├── settings.html           ← Account settings / change password
│   ├── forgot-password.html    ← Password reset
│   ├── css/
│   │   └── styles.css          ← LinkedIn-style CSS (900+ lines)
│   └── js/
│       ├── api.js              ← All API wrappers + helpers
│       ├── auth.js             ← Login + register module
│       ├── dashboard.js        ← Feed, search, notifications, chatbot
│       ├── chat.js             ← Messaging module
│       └── profile.js          ← Profile + edit module
│
├── schema.sql                  ← MySQL DDL (all 7 tables)
├── docker-compose.yml          ← MySQL + Backend + Nginx (HTTPS)
├── nginx.conf                  ← Reverse proxy + HTTPS + security headers
└── ssl_gen.sh                  ← Dev SSL certificate generator
```

---

## Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- MySQL 8.0+

### 1. Setup Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and set:
#   DATABASE_URL=mysql+pymysql://root:yourpassword@localhost:3306/alumni_db
#   SECRET_KEY=your-long-random-secret
```

### 3. Create MySQL Database

```sql
CREATE DATABASE alumni_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Or apply full schema:
```bash
mysql -u root -p < ../schema.sql
```

### 4. Start Backend Server

```bash
python run.py
# → API live at http://localhost:8000
# → Swagger docs at http://localhost:8000/docs
```

### 5. Serve Frontend

Open any HTML file directly in browser, or serve with Python:

```bash
cd ../frontend
python -m http.server 3000
# → Frontend at http://localhost:3000
```

> **Note:** The frontend `js/api.js` is pre-configured to call `http://localhost:8000`.
> Change `API_BASE` in `api.js` if your backend runs on a different port.

### 6. Create Admin Account

```bash
cd backend
python create_admin.py
```

### 7. Seed Demo Data (optional)

```bash
python seed.py
# Creates: 1 admin, 5 alumni, 5 students, posts, messages, mentorship requests
# All demo users share password: password123
```

---

## Docker (Full Stack with HTTPS)

```bash
# 1. Generate dev SSL cert
bash ssl_gen.sh

# 2. Configure
cp backend/.env.example backend/.env
# Edit DATABASE_URL and SECRET_KEY

# 3. Start everything
docker compose up --build

# Access:
#   https://localhost          → Frontend
#   https://localhost/docs     → API Swagger
#   http://localhost           → Redirects to HTTPS
```

---

## Run Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest                         # 87 tests, uses SQLite in-memory (no MySQL needed)
pytest -v                      # verbose
pytest tests/test_auth.py      # single file
```

---

## API Endpoints

| Method | Endpoint                          | Description                    |
|--------|-----------------------------------|--------------------------------|
| POST   | /auth/register                    | Create account                 |
| POST   | /auth/login                       | Login → JWT token              |
| POST   | /auth/forgot-password             | Request reset token            |
| POST   | /auth/reset-password              | Reset with token               |
| POST   | /auth/change-password             | Change password (auth)         |
| GET    | /users/me                         | My profile                     |
| PUT    | /users/me                         | Update profile                 |
| GET    | /users/alumni                     | List all alumni                |
| GET    | /users/{id}                       | Public profile                 |
| GET    | /users/                           | [Admin] All users              |
| DELETE | /users/{id}                       | [Admin] Delete user            |
| POST   | /posts                            | Create post                    |
| GET    | /posts                            | Paginated feed                 |
| DELETE | /posts/{id}                       | Delete post                    |
| POST   | /comments                         | Add comment                    |
| POST   | /likes                            | Toggle like                    |
| POST   | /messages                         | Send message                   |
| GET    | /messages/conversations           | Conversation list              |
| GET    | /messages/{user_id}               | Chat history                   |
| POST   | /mentorship                       | Send request (student)         |
| PUT    | /mentorship/{id}                  | Accept/reject (alumni)         |
| GET    | /mentorship/pending               | Pending requests (alumni)      |
| GET    | /ai/recommendations               | AI alumni recommendations      |
| POST   | /ai/chatbot                       | Career guidance chatbot        |
| GET    | /search                           | Search users + posts           |
| GET    | /search/users                     | Quick user search              |
| POST   | /upload/avatar                    | Upload profile picture         |
| POST   | /upload/post-image                | Upload post image              |
| GET    | /notifications                    | My notifications               |
| GET    | /notifications/unread             | Unread count (badge)           |
| PUT    | /notifications/read-all           | Mark all read                  |
| PUT    | /notifications/{id}/read          | Mark one read                  |

---

## Tech Stack

| Layer       | Technology                                      |
|-------------|-------------------------------------------------|
| Backend     | FastAPI, SQLAlchemy, MySQL, Pydantic v2         |
| Auth        | JWT (python-jose), bcrypt (passlib)             |
| Frontend    | HTML5, CSS3, Vanilla JavaScript (ES Modules)    |
| Database    | MySQL 8.0 (SQLite for tests)                    |
| Migrations  | Alembic                                         |
| Testing     | pytest, httpx, SQLite in-memory                 |
| Deployment  | Docker, Nginx, HTTPS/TLS                        |
