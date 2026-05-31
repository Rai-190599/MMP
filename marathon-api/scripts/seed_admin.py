#!/usr/bin/env python3
"""
Usage: python scripts/seed_admin.py
Env vars required: ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_NAME
Reads DATABASE_URL from .env file.
Idempotent: safe to run multiple times.
"""
import os
import sys
import uuid

from dotenv import load_dotenv
from passlib.context import CryptContext
from sqlalchemy import create_engine, text

load_dotenv()

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
ADMIN_NAME = os.environ.get("ADMIN_NAME")

if not all([ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_NAME]):
    print("ERROR: ADMIN_EMAIL, ADMIN_PASSWORD, and ADMIN_NAME must be set.")
    sys.exit(1)

DATABASE_URL = os.environ.get("DATABASE_URL", "")
# Convert asyncpg URL to sync psycopg2 URL
sync_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

engine = create_engine(sync_url)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

with engine.connect() as conn:
    result = conn.execute(text("SELECT email FROM users WHERE role = 'admin' LIMIT 1"))
    existing = result.fetchone()
    if existing:
        print(f"Admin already exists: {existing[0]}")
        sys.exit(0)

    hashed = pwd_context.hash(ADMIN_PASSWORD)
    conn.execute(
        text(
            "INSERT INTO users (id, name, email, role, password_hash) "
            "VALUES (:id, :name, :email, 'admin', :password_hash)"
        ),
        {"id": str(uuid.uuid4()), "name": ADMIN_NAME, "email": ADMIN_EMAIL, "password_hash": hashed},
    )
    conn.commit()

print(f"✓ Admin created successfully: {ADMIN_EMAIL}")
