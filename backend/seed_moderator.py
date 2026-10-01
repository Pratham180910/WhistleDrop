import os
import sys
from pathlib import Path

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.core.database import get_sessionmaker
from app.core.security import hash_password
from app.models.moderator import Moderator


def seed_moderator():
    username = (os.getenv("MODERATOR_USERNAME") or os.getenv("SEED_MODERATOR_USERNAME") or "").strip()
    password = (os.getenv("MODERATOR_PASSWORD") or os.getenv("SEED_MODERATOR_PASSWORD") or "").strip()

    if not username:
        print("ERROR: MODERATOR_USERNAME environment variable is required.")
        sys.exit(1)

    if not password:
        print("ERROR: MODERATOR_PASSWORD environment variable is required.")
        sys.exit(1)

    if len(password) < 8:
        print("ERROR: MODERATOR_PASSWORD must be at least 8 characters long.")
        sys.exit(1)

    SessionLocal = get_sessionmaker()
    db = SessionLocal()
    try:
        existing = db.query(Moderator).filter(Moderator.username == username).first()
        if existing:
            print(f"Moderator '{username}' already exists. No action taken.")
            return

        new_moderator = Moderator(
            username=username,
            password_hash=hash_password(password),
            is_active=True,
        )
        db.add(new_moderator)
        db.commit()
        db.refresh(new_moderator)
        print(f"Successfully created active moderator: '{username}' (ID: {new_moderator.id})")
    except Exception as e:
        db.rollback()
        print(f"Database error while seeding moderator: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed_moderator()
