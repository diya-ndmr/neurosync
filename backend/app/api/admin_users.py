import secrets
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.middleware.security import require_role
from app.models.user import User, UserRole
from app.services.authentication_service import hash_password
from app.services.audit_service import record_audit_event

router = APIRouter(prefix="/api/admin/users", tags=["User administration"])


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
    db.add(user)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
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
        "message": (
            f"{data.role.title()} role reserved for {email}. "
            "Ask them to create a Supabase account with this verified email address."
        ),
        "user_id": user.id,
        "role": user.role.value,
    }
