"""
Auth Pydantic Schemas.
"""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Schema for login request."""

    username: str = Field(..., min_length=1, max_length=255, description="Username (email)")
    password: str = Field(..., min_length=1, max_length=128, description="Password")


class UserInfo(BaseModel):
    """Schema for user info included in login response."""

    user_id: str
    tenant_id: str
    role: str
    email: str
    name: str


class LoginResponse(BaseModel):
    """Schema for successful login response."""

    access_token: str
    token_type: str = "bearer"
    user: UserInfo
