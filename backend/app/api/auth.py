import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.database.connection import get_db
from app.models.user import EmailVerificationToken, User, UserRole
from app.schemas.user_schema import (
    EmailVerificationRequest,
    ResendVerificationRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services.authentication_service import hash_password, verify_password, create_access_token
from app.services.audit_service import record_audit_event
from app.services.email_service import EmailDeliveryError, send_verification_email
from app.middleware.security import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)
VERIFICATION_TOKEN_LIFETIME = timedelta(hours=24)
VERIFICATION_EMAIL_RESPONSE = {
    "message": "If the account needs verification, a confirmation email has been sent."
}
PUBLIC_REGISTRATION_ROLES = ("student", "lecturer", "advisor")


@router.get("/registration-options")
def registration_options():
    roles = (
        PUBLIC_REGISTRATION_ROLES
        if settings.environment in {"development", "test"}
        else ("student",)
    )
    return {"roles": list(roles)}


def _create_verification_token(db: Session, user_id: str) -> str:
    db.query(EmailVerificationToken).filter(EmailVerificationToken.user_id == user_id).delete(
        synchronize_session=False
    )
    token = secrets.token_urlsafe(32)
    db.add(EmailVerificationToken(
        user_id=user_id,
        token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
        expires_at=datetime.now(timezone.utc) + VERIFICATION_TOKEN_LIFETIME,
    ))
    db.commit()
    return token


def _send_verification_link(email: str, token: str) -> None:
    verification_url = f"{settings.frontend_url.rstrip('/')}/verify-email?token={quote(token)}"
    send_verification_email(email, verification_url)


def _is_email_verified(db: Session, user_id: str) -> bool:
    return db.query(EmailVerificationToken.id).filter(
        EmailVerificationToken.user_id == user_id
    ).first() is None


@router.post("/register", response_model=dict)
def register(data: UserRegister, db: Session = Depends(get_db)):
    if settings.environment not in {"development", "test"} and data.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Lecturer and advisor accounts must be provisioned by an administrator.",
        )
    if not settings.resend_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email verification is not configured. Please try again later.",
        )

    email = str(data.email).strip().lower()
    existing = db.query(User).filter(func.lower(User.email) == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        id=str(uuid.uuid4()),
        email=email,
        name=data.name,
        password_hash=hash_password(data.password),
        role=UserRole(data.role),
    )
    db.add(user)
    db.flush()
    token = _create_verification_token(db, user.id)
    db.refresh(user)

    try:
        _send_verification_link(user.email, token)
    except EmailDeliveryError as error:
        logger.error("registration_verification_email_failed", extra={"user_id": user.id, "error": str(error)})
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Account created, but the confirmation email could not be sent. Request a new link to continue.",
        ) from error

    return {
        "message": "Account created. Check your email for a confirmation link before signing in.",
        "user_id": user.id,
        "role": user.role.value,
    }


@router.post("/verify-email")
def verify_email(data: EmailVerificationRequest, db: Session = Depends(get_db)):
    token_hash = hashlib.sha256(data.token.encode("utf-8")).hexdigest()
    verification = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.token_hash == token_hash
    ).first()
    if not verification:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Confirmation link is invalid or expired.")

    expires_at = verification.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        db.delete(verification)
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Confirmation link is invalid or expired.")

    db.delete(verification)
    db.commit()
    return {"message": "Email confirmed. You can now sign in."}


@router.post("/verify-email/resend")
def resend_verification_email(data: ResendVerificationRequest, db: Session = Depends(get_db)):
    if not settings.resend_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email verification is not configured. Please try again later.",
        )

    email = str(data.email).strip().lower()
    user = db.query(User).filter(func.lower(User.email) == email).first()
    if not user or _is_email_verified(db, user.id):
        return VERIFICATION_EMAIL_RESPONSE

    token = _create_verification_token(db, user.id)
    try:
        _send_verification_link(user.email, token)
    except EmailDeliveryError as error:
        logger.error("verification_resend_email_failed", extra={"user_id": user.id, "error": str(error)})
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not send the confirmation email. Please try again later.",
        ) from error
    return VERIFICATION_EMAIL_RESPONSE


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, request: Request, db: Session = Depends(get_db)):
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
    user = db.query(User).filter(func.lower(User.email) == str(data.email).strip().lower()).first()
    if not user or not verify_password(data.password, user.password_hash):
        record_audit_event(
            db,
            action="AUTH_LOGIN",
            outcome="FAILURE",
            actor_reference=data.email.strip().lower(),
            request_id=request_id,
            source_ip=request.client.host if request.client else None,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not _is_email_verified(db, user.id):
        record_audit_event(
            db,
            action="AUTH_LOGIN",
            outcome="FAILURE",
            actor_reference=user.email.lower(),
            actor_id=user.id,
            request_id=request_id,
            source_ip=request.client.host if request.client else None,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Confirm your email address before signing in.",
        )

    token = create_access_token(user.id)
    record_audit_event(
        db,
        action="AUTH_LOGIN",
        outcome="SUCCESS",
        actor_reference=user.email.lower(),
        actor_id=user.id,
        request_id=request_id,
        source_ip=request.client.host if request.client else None,
    )
    db.commit()

    return TokenResponse(
        token=token,
        user_id=user.id,
        name=user.name,
        role=user.role.value,
        email=user.email,
    )


class MicrosoftMockSignIn(BaseModel):
    email: str


@router.post("/sso/microsoft/mock", response_model=TokenResponse)
def microsoft_mock_sign_in(data: MicrosoftMockSignIn, request: Request, db: Session = Depends(get_db)):
    """Prototype stand-in for the Microsoft Entra ID callback.

    A real integration would validate an OIDC id_token from Microsoft; here the
    chosen account is trusted so the flow can be demonstrated end to end.
    """
    if not settings.mock_sso_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    email = data.email.strip().lower()
    user = db.query(User).filter(func.lower(User.email) == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This Microsoft account is not linked to a NeuroSync user",
        )
    if not _is_email_verified(db, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Confirm your email address before signing in.",
        )
    record_audit_event(
        db,
        action="AUTH_LOGIN_MICROSOFT_MOCK",
        outcome="SUCCESS",
        actor_reference=user.email.lower(),
        actor_id=user.id,
        request_id=getattr(request.state, "request_id", None) or str(uuid.uuid4()),
        source_ip=request.client.host if request.client else None,
    )
    db.commit()
    return TokenResponse(
        token=create_access_token(user.id),
        user_id=user.id,
        name=user.name,
        role=user.role.value,
        email=user.email,
    )


@router.get("/me", response_model=UserResponse)
def get_me(token_user: User = Depends(get_current_user)):
    return UserResponse(
        id=token_user.id,
        name=token_user.name,
        email=token_user.email,
        role=token_user.role.value,
        created_at=token_user.created_at.isoformat() if token_user.created_at else "",
    )
