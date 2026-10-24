"""Create the first production administrator with an interactive password prompt.

Run from the backend directory with: python -m app.bootstrap_admin
"""

from getpass import getpass

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import func

from app.config.settings import settings
from app.database.connection import SessionLocal
from app.models.user import User, UserRole
from app.services.authentication_service import hash_password
from app.services.audit_service import record_audit_event


def create_initial_admin(email: str, name: str, password: str) -> str:
    if settings.environment != "production":
        raise RuntimeError("Initial administrator bootstrap is only available in production.")
    if len(password) < 16 or len(password.encode("utf-8")) > 72:
        raise ValueError("Password must be at least 16 characters and no more than 72 UTF-8 bytes.")

    normalized_email = str(TypeAdapter(EmailStr).validate_python(email)).strip().lower()
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("Name must not be blank.")

    with SessionLocal.begin() as db:
        if db.query(User.id).filter(User.role == UserRole.admin).first():
            raise RuntimeError("An administrator already exists; bootstrap is one-time only.")
        if db.query(User.id).filter(func.lower(User.email) == normalized_email).first():
            raise RuntimeError("An account with this email already exists.")

        user = User(
            email=normalized_email,
            name=normalized_name,
            password_hash=hash_password(password),
            role=UserRole.admin,
        )
        db.add(user)
        db.flush()
        record_audit_event(
            db,
            action="BOOTSTRAP_INITIAL_ADMIN",
            outcome="SUCCESS",
            actor_reference=normalized_email,
            actor_id=user.id,
        )
        return user.id


def main() -> None:
    if settings.environment != "production":
        raise SystemExit("Set ENVIRONMENT=production before bootstrapping the initial administrator.")
    name = input("Administrator name: ").strip()
    email = input("Administrator email: ").strip()
    try:
        password = getpass("Administrator password (16+ characters): ")
        confirmation = getpass("Confirm password: ")
    except (EOFError, KeyboardInterrupt):
        raise SystemExit("Administrator bootstrap cancelled.") from None
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    try:
        user_id = create_initial_admin(email, name, password)
    except (RuntimeError, ValueError, ValidationError) as error:
        raise SystemExit(str(error)) from error
    print(f"Initial administrator created (user ID: {user_id}).")


if __name__ == "__main__":
    main()
