import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.database.connection import get_db
from app.middleware.security import require_role
from app.models.user import PasswordResetToken, User, UserRole
from app.services.authentication_service import hash_password
from app.services.audit_service import record_audit_event
from app.services.email_service import EmailDeliveryError, send_password_reset_email

router = APIRouter(prefix="/api/admin/users", tags=["User administration"])
logger = logging.getLogger(__name__)
PASSWORD_SETUP_TOKEN_LIFETIME = timedelta(minutes=30)


class StaffAccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    role: Literal["lecturer", "advisor"]

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Name must not be blank.")
        return normalized


@router.post("/provision", status_code=status.HTTP_201_CREATED)
def provision_staff_account(
    data: StaffAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    if not settings.resend_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Account setup email is not configured.",
        )

    email = str(data.email).strip().lower()
    if db.query(User.id).filter(func.lower(User.email) == email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.")

    user = User(
        id=str(uuid.uuid4()),
        email=email,
        name=data.name.strip(),
        password_hash=hash_password(secrets.token_urlsafe(48)),
        role=UserRole(data.role),
    )
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    db.add(user)
    db.add(PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + PASSWORD_SETUP_TOKEN_LIFETIME,
    ))
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from error

    setup_url = f"{settings.frontend_url.rstrip('/')}/reset-password?token={quote(token)}"
    try:
        send_password_reset_email(user.email, setup_url)
    except EmailDeliveryError as error:
        db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).delete(
            synchronize_session=False
        )
        db.delete(user)
        db.commit()
        logger.error("staff_account_setup_email_failed", extra={"actor_id": current_user.id, "role": data.role})
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The setup email could not be sent; no staff account was created.",
        ) from error

    record_audit_event(
        db,
        action="ADMIN_PROVISION_STAFF_ACCOUNT",
        outcome="SUCCESS",
        actor_reference=current_user.email.lower(),
        actor_id=current_user.id,
    )
    db.commit()
    return {
        "message": f"Account setup instructions were sent to {email}.",
        "user_id": user.id,
        "role": user.role.value,
    }
