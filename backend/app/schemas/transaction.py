"""Transaction schemas."""

import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, Field

from .common import OutMixin


class TransferCreate(BaseModel):
    from_account_id: int
    to_account_number: str = Field(min_length=3, max_length=20)
    amount: Decimal = Field(gt=0, le=1_000_000)
    description: str = Field(default="", max_length=255)


class TransactionOut(OutMixin):
    id: int
    account_id: int
    type: str
    amount: float
    balance_after: float
    description: str
    category: str
    related_account_id: int | None
    created_at: dt.datetime


class TransactionPage(BaseModel):
    items: list[TransactionOut]
    total: int
    limit: int
    offset: int


class TransferOut(BaseModel):
    debit: TransactionOut
    credit: TransactionOut
