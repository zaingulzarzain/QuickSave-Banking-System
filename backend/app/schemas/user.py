"""User / auth schemas."""

import datetime as dt

from pydantic import BaseModel, EmailStr, Field

from .common import OutMixin


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=6, max_length=72)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)


class UserOut(OutMixin):
    id: int
    email: str
    full_name: str
    is_admin: bool
    is_active: bool
    created_at: dt.datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserSummary(BaseModel):
    user: UserOut
    total_balance: float
    accounts_count: int
    month_income: float
    month_expenses: float
