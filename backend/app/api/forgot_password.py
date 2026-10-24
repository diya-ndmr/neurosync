import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.database.connection import get_db
from app.models.user import PasswordResetToken, User
from app.schemas.user_schema import ForgotPasswordRequest, ResetPasswordRequest
from app.services.authentication_service import hash_password
from app.services.email_service import EmailDeliveryError, send_password_reset_email

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)
RESET_TOKEN_LIFETIME = timedelta(minutes=30)
GENERIC_RESPONSE = {"message": "If an account with that email exists, a reset link has been sent."}


@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Send a password reset link to the user's email."""
    if not settings.resend_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Password reset email is not configured.",
        )

    email = str(data.email).strip().lower()
    user = db.query(User).filter(func.lower(User.email) == email).first()
    if not user:
        return GENERIC_RESPONSE

    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).delete(synchronize_session=False)
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + RESET_TOKEN_LIFETIME,
    )
    db.add(reset_token)
    db.commit()

    reset_url = f"{settings.frontend_url.rstrip('/')}/reset-password?token={quote(token)}"
    try:
        send_password_reset_email(user.email, reset_url)
    except EmailDeliveryError as error:
        db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).delete(
            synchronize_session=False
        )
        db.commit()
        logger.error("password_reset_email_failed", extra={"error": str(error)})
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to send the password reset email. Please try again later.",
        ) from error

    return GENERIC_RESPONSE


@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    token_hash = hashlib.sha256(data.token.encode("utf-8")).hexdigest()
    reset_token = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).first()
    if not reset_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset link is invalid or expired.")

    expires_at = reset_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        db.delete(reset_token)
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset link is invalid or expired.")

    user = db.get(User, reset_token.user_id)
    if not user:
        db.delete(reset_token)
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset link is invalid or expired.")

    user.password_hash = hash_password(data.new_password)
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).delete(synchronize_session=False)
    db.commit()
    return {"message": "Password updated. You can now sign in."}
