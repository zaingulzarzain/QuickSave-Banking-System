"""Account schemas."""

import datetime as dt
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from .common import OutMixin


class AccountCreate(BaseModel):
    account_type: Literal["savings", "checking"] = "savings"
    account_name: str = Field(default="My Account", min_length=2, max_length=100)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    initial_deposit: Decimal = Field(default=Decimal("0"), ge=0, le=1_000_000)


class AccountOut(OutMixin):
    id: int
    account_number: str
    account_name: str
    account_type: str
    balance: float
    currency: str
    status: str
    created_at: dt.datetime


class MoneyIn(BaseModel):
    amount: Decimal = Field(gt=0, le=1_000_000)
    description: str = Field(default="", max_length=255)


class AccountStatusUpdate(BaseModel):
    status: Literal["active", "frozen"]


class AccountLookupOut(BaseModel):
    account_number: str
    account_name: str
    account_type: str
    owner_display: str
