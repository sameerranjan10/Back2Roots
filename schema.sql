-- ══════════════════════════════════════════════════════════════════════════════
--  Back2Roots — MySQL Schema
--  Run this ONCE to set up the database before starting the backend.
--  SQLAlchemy will also auto-create these via Base.metadata.create_all(),
--  but this file is provided for manual inspection / CI pipelines.
-- ══════════════════════════════════════════════════════════════════════════════

CREATE DATABASE IF NOT EXISTS alumni_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE alumni_db;

-- ─── users ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              INT          NOT NULL AUTO_INCREMENT,
    name            VARCHAR(100) NOT NULL,
    email           VARCHAR(150) NOT NULL,
    password        VARCHAR(255) NOT NULL,
    role            ENUM('student','alumni','admin') NOT NULL DEFAULT 'student',
    college         VARCHAR(200),
    skills          TEXT,
    bio             TEXT,
    profile_picture VARCHAR(500),
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_users_email (email),
    KEY ix_users_id    (id),
    KEY ix_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── posts ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS posts (
    id         INT      NOT NULL AUTO_INCREMENT,
    user_id    INT      NOT NULL,
    content    TEXT     NOT NULL,
    image_url  VARCHAR(500),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY ix_posts_id      (id),
    KEY ix_posts_user_id (user_id),
    CONSTRAINT fk_posts_user
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── comments ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS comments (
    id         INT      NOT NULL AUTO_INCREMENT,
    post_id    INT      NOT NULL,
    user_id    INT      NOT NULL,
    content    TEXT     NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY ix_comments_id      (id),
    KEY ix_comments_post_id (post_id),
    CONSTRAINT fk_comments_post
        FOREIGN KEY (post_id) REFERENCES posts (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_comments_user
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── likes ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS likes (
    id      INT NOT NULL AUTO_INCREMENT,
    post_id INT NOT NULL,
    user_id INT NOT NULL,

    PRIMARY KEY (id),
    UNIQUE KEY uq_post_user_like (post_id, user_id),
    KEY ix_likes_id (id),
    CONSTRAINT fk_likes_post
        FOREIGN KEY (post_id) REFERENCES posts (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_likes_user
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── messages ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS messages (
    id          INT      NOT NULL AUTO_INCREMENT,
    sender_id   INT      NOT NULL,
    receiver_id INT      NOT NULL,
    content     TEXT     NOT NULL,
    is_read     TINYINT(1) NOT NULL DEFAULT 0,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY ix_messages_id          (id),
    KEY ix_messages_sender_id   (sender_id),
    KEY ix_messages_receiver_id (receiver_id),
    CONSTRAINT fk_messages_sender
        FOREIGN KEY (sender_id)   REFERENCES users (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_messages_receiver
        FOREIGN KEY (receiver_id) REFERENCES users (id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── mentorship_requests ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mentorship_requests (
    id         INT      NOT NULL AUTO_INCREMENT,
    student_id INT      NOT NULL,
    alumni_id  INT      NOT NULL,
    status     ENUM('pending','accepted','rejected') NOT NULL DEFAULT 'pending',
    message    TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY ix_mentorship_id         (id),
    KEY ix_mentorship_student_id (student_id),
    KEY ix_mentorship_alumni_id  (alumni_id),
    CONSTRAINT fk_mentorship_student
        FOREIGN KEY (student_id) REFERENCES users (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_mentorship_alumni
        FOREIGN KEY (alumni_id)  REFERENCES users (id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── Optional: seed an admin account ─────────────────────────────────────────
-- Password below is bcrypt hash of "admin123" — change immediately in prod.
-- INSERT INTO users (name, email, password, role, college)
-- VALUES (
--     'Platform Admin',
--     'admin@college.edu',
--     '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
--     'admin',
--     'Back2Roots College'
-- );

-- ─── notifications ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notifications (
    id          INT      NOT NULL AUTO_INCREMENT,
    user_id     INT      NOT NULL,
    actor_id    INT,
    type        ENUM('like','comment','mentorship_request','mentorship_update','message','system')
                NOT NULL,
    message     TEXT     NOT NULL,
    link        VARCHAR(500),
    is_read     TINYINT(1) NOT NULL DEFAULT 0,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY ix_notifications_id      (id),
    KEY ix_notifications_user_id (user_id),
    CONSTRAINT fk_notif_user
        FOREIGN KEY (user_id)  REFERENCES users (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_notif_actor
        FOREIGN KEY (actor_id) REFERENCES users (id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
