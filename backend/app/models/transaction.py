"""Transaction (ledger entry) model."""

import datetime as dt
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base, utcnow


class TransactionType:
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"

    INCOME_TYPES = (DEPOSIT, TRANSFER_IN)
    EXPENSE_TYPES = (WITHDRAWAL, TRANSFER_OUT)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"), index=True
    )
    type: Mapped[str] = mapped_column(String(20), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    balance_after: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    description: Mapped[str] = mapped_column(String(255), default="")
    category: Mapped[str] = mapped_column(String(50), default="general", index=True)
    related_account_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=utcnow, index=True
    )

    account: Mapped["Account"] = relationship("Account", back_populates="transactions")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Transaction {self.type} {self.amount}>"
