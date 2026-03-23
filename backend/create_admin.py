#!/usr/bin/env python3
"""
create_admin.py — Interactive CLI to create an admin user.

Usage:
    python create_admin.py
    python create_admin.py --name "Admin" --email admin@college.edu --password secret123

This script bypasses the public registration API so that admin
accounts are never exposed through a public endpoint.
"""

import argparse
import sys
import os

# Make sure the project root is on the path when run from the project directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine, Base
from app.models import User
from app.auth import get_password_hash


def create_admin(name: str, email: str, password: str, college: str = "") -> None:
    """Insert an admin user into the database."""
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            if existing.role == "admin":
                print(f"✅  Admin account already exists for {email}")
            else:
                print(f"⚠️   A {existing.role} account already exists for {email}.")
                answer = input("    Upgrade to admin? [y/N] ").strip().lower()
                if answer == "y":
                    existing.role = "admin"
                    db.commit()
                    print(f"✅  {email} upgraded to admin.")
            return

        admin = User(
            name=name,
            email=email,
            password=get_password_hash(password),
            role="admin",
            college=college or None,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"\n✅  Admin account created successfully!")
        print(f"    ID     : {admin.id}")
        print(f"    Name   : {admin.name}")
        print(f"    Email  : {admin.email}")
        print(f"    Role   : {admin.role}")
        print(f"\n    Use these credentials to log in at POST /auth/login")
    finally:
        db.close()


def interactive_mode() -> tuple[str, str, str, str]:
    """Prompt the user for credentials interactively."""
    import getpass

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  Alumni Nexus — Create Admin Account")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    name    = input("Full name   : ").strip()
    email   = input("Email       : ").strip()
    college = input("College     : ").strip()

    while True:
        password = getpass.getpass("Password    : ")
        if len(password) < 6:
            print("  ⚠️  Password must be at least 6 characters.")
            continue
        confirm = getpass.getpass("Confirm pw  : ")
        if password != confirm:
            print("  ⚠️  Passwords do not match. Try again.")
            continue
        break

    return name, email, password, college


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create an admin user for Alumni Nexus"
    )
    parser.add_argument("--name",     help="Admin full name")
    parser.add_argument("--email",    help="Admin email address")
    parser.add_argument("--password", help="Admin password (min 6 chars)")
    parser.add_argument("--college",  help="College name (optional)", default="")
    args = parser.parse_args()

    # If all required args provided via flags, use them
    if args.name and args.email and args.password:
        create_admin(args.name, args.email, args.password, args.college)
    else:
        # Fall back to interactive mode
        name, email, password, college = interactive_mode()
        if not name or not email or not password:
            print("❌  Name, email, and password are required.")
            sys.exit(1)
        create_admin(name, email, password, college)


if __name__ == "__main__":
    main()
