from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Literal


class UserRegister(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    # Public self-registration must never mint an administrator: admin accounts are
    # provisioned by the seeded dataset/an operator. Staff roles stay available so
    # the lecturer and advisor demo sign-up flows keep working.
    role: Literal["student", "lecturer", "advisor"] = "student"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    role: str
    created_at: str


class TokenResponse(BaseModel):
    token: str
    user_id: str
    name: str
    role: str
    email: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class EmailVerificationRequest(BaseModel):
    token: str = Field(min_length=1, max_length=256)


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=128)
