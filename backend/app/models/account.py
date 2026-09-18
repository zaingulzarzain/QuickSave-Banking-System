"""Bank account model."""

import datetime as dt
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base, utcnow


class AccountStatus:
    ACTIVE = "active"
    FROZEN = "frozen"
    CLOSED = "closed"


class AccountType:
    SAVINGS = "savings"
    CHECKING = "checking"


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    account_number: Mapped[str] = mapped_column(
        String(20), unique=True, index=True
    )
    account_name: Mapped[str] = mapped_column(String(100), default="My Account")
    account_type: Mapped[str] = mapped_column(String(20), default="savings")
    balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0.00")
    )
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[str] = mapped_column(String(20), default=AccountStatus.ACTIVE)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

    owner: Mapped["User"] = relationship("User", back_populates="accounts")
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="account", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Account {self.account_number} ({self.balance})>"
