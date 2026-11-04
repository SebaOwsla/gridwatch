"""Password login and administrator managed user accounts."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.api.dependencies import CurrentUser, SessionDep, require_roles
from app.core.security import DUMMY_HASH, create_access_token, hash_password, verify_password
from app.core.settings import get_settings
from app.db.models import User
from app.modules.audit import record_audit


router = APIRouter(prefix="/auth", tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=12, max_length=128)
    role: Literal["admin", "operator", "viewer"]

    @field_validator("full_name", mode="before")
    @classmethod
    def strip_full_name(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    role: Literal["admin", "operator", "viewer"]
    is_active: bool
    created_at: datetime


@router.post("/login", response_model=TokenResponse)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep) -> TokenResponse:
    email = form.username.strip().lower()
    user = session.scalar(sa.select(User).where(User.email == email))
    stored_hash = user.password_hash if user is not None else DUMMY_HASH
    valid_password = verify_password(form.password, stored_hash)
    if user is None or not user.is_active or not valid_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=create_access_token(user.id, get_settings()))


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> User:
    return user


@router.get("/users", response_model=list[UserRead])
def list_users(
    session: SessionDep,
    _admin: Annotated[User, Depends(require_roles("admin"))],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[User]:
    return list(session.scalars(sa.select(User).order_by(User.email).offset(offset).limit(limit)))


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    session: SessionDep,
    admin: Annotated[User, Depends(require_roles("admin"))],
) -> User:
    user = User(
        email=str(payload.email).lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    session.add(user)
    session.flush()
    record_audit(session, actor_id=admin.id, action="user.created", entity_type="user", entity_id=user.id)
    session.commit()
    session.refresh(user)
    return user
