#!/usr/bin/env python3
"""
seed.py — Populate the database with realistic demo data for development.

Creates:
  • 1 admin
  • 5 alumni with varied skills
  • 5 students with varied skills
  • 12 posts spread across users
  • Likes and comments
  • 6 messages (2 conversations)
  • 3 mentorship requests (various statuses)

Usage:
    python seed.py           # seeds data (skips if data already exists)
    python seed.py --reset   # drops all rows, then re-seeds
"""

import argparse
import sys
import os
from datetime import datetime, timedelta
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine, Base
from app.models import User, Post, Comment, Like, Message, MentorshipRequest
from app.auth import get_password_hash

# ── Demo data ─────────────────────────────────────────────────────────────────

COLLEGE = "IIT Bombay"
PASSWORD_HASH = get_password_hash("password123")   # all seed users share this

ALUMNI: list[dict] = [
    {
        "name": "Priya Sharma",
        "email": "priya.sharma@alumni.iitb.ac.in",
        "college": COLLEGE,
        "skills": "Machine Learning, Python, TensorFlow, Data Science, NLP",
        "bio": "ML Engineer at Google Brain. IIT Bombay CSE 2018. Passionate about building AI products that matter.",
    },
    {
        "name": "Rahul Verma",
        "email": "rahul.verma@alumni.iitb.ac.in",
        "college": COLLEGE,
        "skills": "Full Stack, React, Node.js, AWS, System Design",
        "bio": "Senior SWE at Microsoft. Love open source and distributed systems. Happy to mentor students.",
    },
    {
        "name": "Ananya Iyer",
        "email": "ananya.iyer@alumni.iitb.ac.in",
        "college": COLLEGE,
        "skills": "Product Management, Strategy, SQL, A/B Testing, Growth",
        "bio": "Product Manager at Swiggy. Ex-Flipkart. Let's talk product, career pivots, and startup life.",
    },
    {
        "name": "Karthik Nair",
        "email": "karthik.nair@alumni.iitb.ac.in",
        "college": COLLEGE,
        "skills": "Blockchain, Solidity, Web3, Rust, Cryptography",
        "bio": "Co-founder at a DeFi startup. Building the next generation of financial infrastructure.",
    },
    {
        "name": "Sneha Patel",
        "email": "sneha.patel@alumni.iitb.ac.in",
        "college": COLLEGE,
        "skills": "DevOps, Kubernetes, Docker, CI/CD, Terraform, AWS",
        "bio": "Site Reliability Engineer at Amazon. Obsessed with uptime, automation, and clean pipelines.",
    },
]

STUDENTS: list[dict] = [
    {
        "name": "Arjun Mehta",
        "email": "arjun.mehta@iitb.ac.in",
        "college": COLLEGE,
        "skills": "Python, Machine Learning, Flask, SQL",
        "bio": "3rd year CSE student. Interested in ML and AI. Looking for internship opportunities.",
    },
    {
        "name": "Divya Krishnan",
        "email": "divya.krishnan@iitb.ac.in",
        "college": COLLEGE,
        "skills": "React, JavaScript, CSS, Node.js",
        "bio": "Web dev enthusiast. Building projects. Open to product roles.",
    },
    {
        "name": "Rohan Gupta",
        "email": "rohan.gupta@iitb.ac.in",
        "college": COLLEGE,
        "skills": "C++, Algorithms, Data Structures, Competitive Programming",
        "bio": "2nd year student. Competitive programmer. ICPC aspirant.",
    },
    {
        "name": "Neha Joshi",
        "email": "neha.joshi@iitb.ac.in",
        "college": COLLEGE,
        "skills": "Data Analysis, Python, Tableau, SQL, Statistics",
        "bio": "Final year student. Passionate about data-driven decision making.",
    },
    {
        "name": "Vikram Singh",
        "email": "vikram.singh@iitb.ac.in",
        "college": COLLEGE,
        "skills": "Android, Kotlin, Firebase, REST APIs",
        "bio": "Mobile developer. Building apps for social impact.",
    },
]

POSTS: list[dict] = [
    {
        "role": "alumni",
        "idx":  0,
        "content": "🚀 Excited to share that our team just open-sourced our distributed ML training framework!\n\nAfter 18 months of building at Google Brain, we're giving back to the community. Star us on GitHub if you find it useful!\n\n#MachineLearning #OpenSource #AI",
    },
    {
        "role": "alumni",
        "idx":  1,
        "content": "💡 System Design Tip:\n\nWhen designing for scale, always ask: 'What breaks first?'\n\nMost junior engineers jump to fancy architectures. Start simple. A single Postgres instance handles millions of rows. You probably don't need microservices yet.\n\nHappy to discuss this in depth — message me! 👇",
    },
    {
        "role": "alumni",
        "idx":  2,
        "content": "📊 Product lesson I learned the hard way:\n\nData can tell you WHAT is happening. It almost never tells you WHY.\n\nAlways pair your dashboards with user interviews. That's where the real insights live.\n\n#ProductManagement #UXResearch",
    },
    {
        "role": "alumni",
        "idx":  3,
        "content": "🔐 Web3 is not just hype.\n\nWe just closed our seed round. The problem we're solving — transparent cross-border payments — is very real.\n\nLooking for strong Rust/Solidity engineers who want to build infrastructure that matters. DM me.",
    },
    {
        "role": "alumni",
        "idx":  4,
        "content": "⚡ Zero-downtime deployments are not magic.\n\nHere's the short version:\n1. Blue-green deployment\n2. Health checks before routing traffic\n3. Canary releases for big changes\n4. Rollback scripts ready before you deploy\n\nThat's it. No magic. Just discipline.",
    },
    {
        "role": "student",
        "idx":  0,
        "content": "Just submitted my first ML project — a sentiment analysis model on movie reviews!\n\nAccuracy: 91% with BERT fine-tuning 🎉\n\nCode is on my GitHub. Would love feedback from anyone working in NLP!\n#FirstProject #MachineLearning",
    },
    {
        "role": "student",
        "idx":  1,
        "content": "Built my first full-stack app this weekend — a real-time collaborative whiteboard!\n\nStack: React + WebSockets + Node.js + Redis\n\nStill rough around the edges but it works 😄 Deployed on Railway.\n\nLooking for feedback! Link in comments.",
    },
    {
        "role": "student",
        "idx":  2,
        "content": "Solved my 500th LeetCode problem today 🎯\n\nHonestly the most useful thing I've practiced is not solving problems fast — it's explaining my thought process clearly.\n\nInter-views are conversations, not coding sprints.",
    },
    {
        "role": "student",
        "idx":  3,
        "content": "Presenting my data viz project to the department next week.\n\nBuilt an interactive dashboard showing enrollment trends across IITs using Plotly + Pandas.\n\nAny seniors who've done final-year presentations — tips welcome! 🙏",
    },
    {
        "role": "student",
        "idx":  4,
        "content": "My Android app just hit 1,000 downloads on the Play Store! 🥳\n\nStarted as a hobby project to help students track assignments. Never expected real users.\n\nBiggest lesson: ship early, iterate fast.",
    },
    {
        "role": "alumni",
        "idx":  0,
        "content": "📌 Internship season is coming up.\n\nIf you're a student at our college looking for ML/AI roles, I'm happy to refer strong candidates at Google.\n\nDM me your resume and a 2-line pitch on why you want to work in AI. I'll review every message I get.",
    },
    {
        "role": "alumni",
        "idx":  1,
        "content": "Reminder that the best time to build your network is before you need it.\n\nSend that connection request. Write that comment. Attend that virtual meetup.\n\nYour future self will thank you. 🤝",
    },
]

COMMENTS: list[tuple] = [
    # (post_idx, commenter_role, commenter_idx, text)
    (0, "student", 0, "This is incredible! Would love to contribute. Is there a good-first-issues label?"),
    (0, "student", 1, "Congrats Priya! Following the repo 🌟"),
    (1, "student", 0, "This is exactly what I needed to hear before my system design interview. Thank you!"),
    (2, "student", 3, "So true. Analytics kept telling us users loved the feature but interviews revealed they were just confused 😅"),
    (5, "alumni", 0, "Nice work! Have you tried DistilBERT? Faster with comparable accuracy for sentiment tasks."),
    (6, "alumni", 1, "Love the stack choice. Consider adding offline support with service workers next!"),
    (10, "student", 0, "Just sent you a DM! This would be a dream opportunity 🙏"),
    (10, "student", 2, "Applied! Thanks for doing this. Really means a lot to us students."),
]

# ── Seeder ────────────────────────────────────────────────────────────────────

def reset_data(db) -> None:
    """Delete all seeded content in safe dependency order."""
    print("🗑️  Resetting existing data…")
    db.query(MentorshipRequest).delete()
    db.query(Message).delete()
    db.query(Like).delete()
    db.query(Comment).delete()
    db.query(Post).delete()
    db.query(User).delete()
    db.commit()
    print("   Done.\n")


def seed(reset: bool = False) -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Check for existing data
        if not reset and db.query(User).count() > 0:
            print("ℹ️  Database already contains users. Run with --reset to re-seed.")
            return

        if reset:
            reset_data(db)

        print("🌱 Seeding Back2Roots demo data…\n")

        # ── Admin ──────────────────────────────────────────────────────────────
        admin = User(
            name="Platform Admin",
            email="admin@iitb.ac.in",
            password=PASSWORD_HASH,
            role="admin",
            college=COLLEGE,
            skills="Administration, Platform Management",
            bio="Back2Roots platform administrator.",
        )
        db.add(admin)
        db.flush()
        print(f"  ✅ Admin   : {admin.email}")

        # ── Alumni ─────────────────────────────────────────────────────────────
        alumni_objs: list[User] = []
        for a in ALUMNI:
            user = User(
                name=a["name"],
                email=a["email"],
                password=PASSWORD_HASH,
                role="alumni",
                college=a["college"],
                skills=a["skills"],
                bio=a["bio"],
            )
            db.add(user)
            alumni_objs.append(user)
        db.flush()
        for u in alumni_objs:
            print(f"  ✅ Alumni  : {u.email}")

        # ── Students ───────────────────────────────────────────────────────────
        student_objs: list[User] = []
        for s in STUDENTS:
            user = User(
                name=s["name"],
                email=s["email"],
                password=PASSWORD_HASH,
                role="student",
                college=s["college"],
                skills=s["skills"],
                bio=s["bio"],
            )
            db.add(user)
            student_objs.append(user)
        db.flush()
        for u in student_objs:
            print(f"  ✅ Student : {u.email}")

        # ── Posts ──────────────────────────────────────────────────────────────
        post_objs: list[Post] = []
        base_time = datetime.utcnow() - timedelta(days=7)
        for i, p in enumerate(POSTS):
            author = alumni_objs[p["idx"]] if p["role"] == "alumni" else student_objs[p["idx"]]
            post = Post(
                user_id=author.id,
                content=p["content"],
                created_at=base_time + timedelta(hours=i * 4),
            )
            db.add(post)
            post_objs.append(post)
        db.flush()
        print(f"\n  ✅ Posts     : {len(post_objs)}")

        # ── Likes ──────────────────────────────────────────────────────────────
        all_users = [admin] + alumni_objs + student_objs
        likes_added = 0
        for post in post_objs:
            likers = random.sample(all_users, k=random.randint(1, min(6, len(all_users))))
            for liker in likers:
                if liker.id != post.user_id:
                    db.add(Like(post_id=post.id, user_id=liker.id))
                    likes_added += 1
        db.flush()
        print(f"  ✅ Likes     : {likes_added}")

        # ── Comments ───────────────────────────────────────────────────────────
        comments_added = 0
        for (post_idx, comm_role, comm_idx, text) in COMMENTS:
            if post_idx >= len(post_objs):
                continue
            author = alumni_objs[comm_idx] if comm_role == "alumni" else student_objs[comm_idx]
            db.add(Comment(
                post_id=post_objs[post_idx].id,
                user_id=author.id,
                content=text,
            ))
            comments_added += 1
        db.flush()
        print(f"  ✅ Comments  : {comments_added}")

        # ── Messages ───────────────────────────────────────────────────────────
        convo1 = [
            (student_objs[0], alumni_objs[0], "Hi Priya! I'm really interested in ML roles. Could we have a quick chat?"),
            (alumni_objs[0], student_objs[0], "Hey Arjun! Sure, happy to help. What kind of ML work interests you most?"),
            (student_objs[0], alumni_objs[0], "Mostly NLP and recommendation systems. I've been working with BERT lately."),
            (alumni_objs[0], student_objs[0], "Great! Send me your resume and 2-3 projects you're proud of. I'll take a look."),
        ]
        convo2 = [
            (student_objs[1], alumni_objs[1], "Hi Rahul, I saw your post about system design. Any book recommendations?"),
            (alumni_objs[1], student_objs[1], "Hi Divya! Absolutely — 'Designing Data-Intensive Applications' by Kleppmann is the gold standard."),
        ]
        msgs_added = 0
        for t_offset, (sender, receiver, content) in enumerate(convo1 + convo2):
            db.add(Message(
                sender_id=sender.id,
                receiver_id=receiver.id,
                content=content,
                created_at=datetime.utcnow() - timedelta(hours=2) + timedelta(minutes=t_offset * 5),
            ))
            msgs_added += 1
        db.flush()
        print(f"  ✅ Messages  : {msgs_added}")

        # ── Mentorship requests ────────────────────────────────────────────────
        mentorship_data = [
            (student_objs[0], alumni_objs[0], "accepted",
             "Hi Priya, I'm an ML student looking for guidance on breaking into research roles at top companies."),
            (student_objs[1], alumni_objs[1], "pending",
             "Hi Rahul, I'd love to learn more about full-stack engineering and how you got to Microsoft."),
            (student_objs[3], alumni_objs[2], "pending",
             "Hi Ananya, I'm considering a pivot to product management after graduation. Your journey is very inspiring."),
        ]
        for student, alumni, status, message in mentorship_data:
            db.add(MentorshipRequest(
                student_id=student.id,
                alumni_id=alumni.id,
                status=status,
                message=message,
            ))
        db.flush()
        print(f"  ✅ Mentorship: {len(mentorship_data)}")

        db.commit()

        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("  🎉  Seeding complete!")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"\n  All seed users share the password: password123")
        print(f"\n  Test accounts:")
        print(f"    Admin   → admin@iitb.ac.in")
        print(f"    Alumni  → priya.sharma@alumni.iitb.ac.in")
        print(f"    Student → arjun.mehta@iitb.ac.in")
        print()

    except Exception as exc:
        db.rollback()
        print(f"\n❌  Seeding failed: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Back2Roots with demo data")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete all existing data before seeding",
    )
    args = parser.parse_args()
    seed(reset=args.reset)
