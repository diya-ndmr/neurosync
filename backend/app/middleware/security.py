from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.config.settings import settings
from app.models.student import StudentProfile
from app.models.user import EmailVerificationToken, User, UserRole

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Authenticate using JWT Bearer token."""
    if credentials is None or not credentials.credentials:
        # HTTPBearer's default is 403 "Not authenticated"; an absent or malformed
        # credential is an authentication problem, so answer 401 with the standard
        # WWW-Authenticate challenge.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials

    # Allow demo tokens to skip JWT verification (offline demo mode). Disabled by
    # setting ALLOW_DEMO_TOKENS=0 in production.
    if token.startswith("demo-token-"):
        if not settings.allow_demo_tokens:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Demo tokens are disabled on this deployment",
            )
        # Expected shape: demo-token-{role}-{timestamp}. A malformed header used to
        # raise IndexError/ValueError here and answer 500 instead of 401.
        parts = token.split("-")
        role_token = parts[2].lower() if len(parts) > 2 else ""
        try:
            demo_role = UserRole(role_token)
        except ValueError:
            demo_role = None
        user = (
            db.query(User)
            .filter(
                User.role == demo_role,
                ~User.id.in_(db.query(EmailVerificationToken.user_id)),
            )
            .first()
            if demo_role
            else None
        )
        if user:
            return user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid demo token",
        )

    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        user_id = payload.get("sub")
        if not isinstance(user_id, str) or not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


def require_role(*allowed_roles: UserRole):
    """Require the user to have one of the specified roles."""

    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return role_checker


def require_own_student_record(current_user: User, student_id: str, db: Session) -> None:
    """Stop students from reading or writing another student's academic records.

    Staff roles keep their existing scope checks; a student account may only ever
    address the profile linked to its own user account.
    """
    if current_user.role != UserRole.student:
        return

    profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
    if profile is None or profile.id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students may only access their own academic records",
        )
