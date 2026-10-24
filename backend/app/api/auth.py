import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.database.connection import get_db
from app.models.user import User, UserRole
from app.schemas.user_schema import (
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services.authentication_service import hash_password, verify_password, create_access_token
from app.services.audit_service import record_audit_event
from app.services.firebase_auth import InvalidFirebaseToken, verify_firebase_id_token
from app.middleware.security import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
PUBLIC_REGISTRATION_ROLES = ("student", "lecturer", "advisor")


class FirebaseSessionRequest(BaseModel):
    id_token: str = Field(min_length=1)


def _session_response(user: User) -> TokenResponse:
    return TokenResponse(
        token=create_access_token(user.id),
        user_id=user.id,
        name=user.name,
        role=user.role.value,
        email=user.email,
    )


@router.get("/registration-options")
def registration_options():
    roles = (
        PUBLIC_REGISTRATION_ROLES
        if settings.environment in {"development", "test"}
        else ("student",)
    )
    return {"roles": list(roles)}


@router.post("/register", response_model=dict)
def register(data: UserRegister, db: Session = Depends(get_db)):
    if settings.environment not in {"development", "test"}:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Use Firebase Authentication to create accounts.",
        )
    if data.role not in PUBLIC_REGISTRATION_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Lecturer and advisor accounts must be provisioned by an administrator.",
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
    db.commit()

    return {
        "message": "Development account created.",
        "user_id": user.id,
        "role": user.role.value,
    }


@router.post("/firebase-session", response_model=TokenResponse)
def firebase_session(data: FirebaseSessionRequest, request: Request, db: Session = Depends(get_db)):
    try:
        claims = verify_firebase_id_token(data.id_token)
    except InvalidFirebaseToken as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate Firebase credentials.",
        ) from error

    email = claims.get("email")
    uid = claims.get("uid")
    if (
        claims.get("email_verified") is not True
        or not isinstance(email, str)
        or not email.strip()
        or not isinstance(uid, str)
        or not uid
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A verified Firebase email account is required.",
        )

    normalized_email = email.strip().lower()
    user = db.query(User).filter(func.lower(User.email) == normalized_email).first()
    if user is None:
        user = User(
            id=str(uuid.uuid4()),
            email=normalized_email,
            name=str(claims.get("name") or normalized_email.split("@", 1)[0]),
            password_hash=hash_password(secrets.token_urlsafe(48)),
            role=UserRole.student,
        )
        db.add(user)
        db.flush()

    record_audit_event(
        db,
        action="AUTH_LOGIN_FIREBASE",
        outcome="SUCCESS",
        actor_reference=user.email.lower(),
        actor_id=user.id,
        request_id=getattr(request.state, "request_id", None) or str(uuid.uuid4()),
        source_ip=request.client.host if request.client else None,
    )
    db.commit()
    return _session_response(user)


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, request: Request, db: Session = Depends(get_db)):
    if settings.environment not in {"development", "test"}:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Use Firebase Authentication to sign in.",
        )
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

    return TokenResponse(token=token, user_id=user.id, name=user.name, role=user.role.value, email=user.email)


class MicrosoftMockSignIn(BaseModel):
    email: str


@router.post("/sso/microsoft/mock", response_model=TokenResponse)
def microsoft_mock_sign_in(data: MicrosoftMockSignIn, request: Request, db: Session = Depends(get_db)):
    """Prototype stand-in for the Microsoft Entra ID callback.

    A real integration would validate an OIDC id_token from Microsoft; here the
    chosen account is trusted so the flow can be demonstrated end to end.
    """
    if settings.environment not in {"development", "test"} or not settings.mock_sso_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    email = data.email.strip().lower()
    user = db.query(User).filter(func.lower(User.email) == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This Microsoft account is not linked to a NeuroSync user",
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
