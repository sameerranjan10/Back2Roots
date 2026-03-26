from faker import Faker
import random
import bcrypt
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import User, Post, Comment, Like, Message, MentorshipRequest

fake = Faker()
db: Session = SessionLocal()

# -----------------------
# Password hash
# -----------------------
def hash_password(password: str):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

# -----------------------
# Data pools
# -----------------------
skills_pool = ["Python", "Java", "React", "Node.js", "ML", "AI", "SQL", "Docker"]
companies = ["TCS", "Infosys", "Wipro", "Google", "Microsoft", "Amazon"]

users = []
posts = []
comments = []
likes = []
messages = []
mentorships = []

# -----------------------
# Create Students
# -----------------------
students = []
for _ in range(50):
    user = User(
        name=fake.name(),
        email=fake.unique.email(),
        password=hash_password("password123"),
        role="student",
        college="GIET University",
        skills=", ".join(random.sample(skills_pool, 3)),
        bio=fake.text(max_nb_chars=100)
    )
    users.append(user)
    students.append(user)

# -----------------------
# Create Alumni
# -----------------------
alumni_list = []
for _ in range(10):
    alumni = User(
        name=fake.name(),
        email=fake.unique.email(),
        password=hash_password("password123"),
        role="alumni",
        college="GIET University",
        skills=", ".join(random.sample(skills_pool, 4)),
        bio=f"Working at {random.choice(companies)}"
    )
    users.append(alumni)
    alumni_list.append(alumni)

# -----------------------
# Save Users
# -----------------------
db.add_all(users)
db.commit()

for user in users:
    db.refresh(user)

# -----------------------
# Create Posts
# -----------------------
for user in users:
    for _ in range(random.randint(1, 3)):
        post = Post(
            user_id=user.id,
            content=fake.sentence()
        )
        posts.append(post)

db.add_all(posts)
db.commit()

for post in posts:
    db.refresh(post)

# -----------------------
# Comments & Likes (FIXED)
# -----------------------
for post in posts:
    # Comments
    for _ in range(random.randint(1, 4)):
        commenter = random.choice(users)
        comment = Comment(
            post_id=post.id,
            user_id=commenter.id,
            content=fake.sentence()
        )
        comments.append(comment)

    # Likes (NO DUPLICATES)
    liked_users = set()
    for _ in range(random.randint(1, 6)):
        liker = random.choice(users)

        if liker.id in liked_users:
            continue

        liked_users.add(liker.id)

        like = Like(
            post_id=post.id,
            user_id=liker.id
        )
        likes.append(like)

db.add_all(comments)
db.add_all(likes)
db.commit()

# -----------------------
# Mentorship (connections)
# -----------------------
for student in students:
    alumni = random.choice(alumni_list)
    mentorship = MentorshipRequest(
        student_id=student.id,
        alumni_id=alumni.id,
        status=random.choice(["pending", "accepted", "rejected"]),
        message="Looking for guidance!"
    )
    mentorships.append(mentorship)

db.add_all(mentorships)
db.commit()

# -----------------------
# Messages (chat)
# -----------------------
for _ in range(50):
    sender = random.choice(users)
    receiver = random.choice(users)

    if sender.id != receiver.id:
        msg = Message(
            sender_id=sender.id,
            receiver_id=receiver.id,
            content=fake.sentence()
        )
        messages.append(msg)

db.add_all(messages)
db.commit()

db.close()

print("🔥 Advanced dataset created successfully!")