"""Core banking operations.

All balance mutations go through this module so transfers stay atomic
(debit + credit + both ledger rows commit together or not at all).
"""

import secrets
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models.account import Account, AccountStatus
from ..models.transaction import Transaction, TransactionType
from ..models.user import User
from ..schemas.account import AccountCreate
from .ai_service import categorize

_CENTS = Decimal("0.01")


def _q2(value: Decimal) -> Decimal:
    return Decimal(value).quantize(_CENTS)


def generate_account_number(db: Session) -> str:
    for _ in range(25):
        number = "QS" + "".join(secrets.choice("0123456789") for _ in range(10))
        if not db.query(Account).filter_by(account_number=number).first():
            return number
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Could not generate a unique account number",
    )


def get_owned_account(db: Session, user: User, account_id: int) -> Account:
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    if account.user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not your account")
    return account


def _ensure_active(account: Account) -> None:
    if account.status != AccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account {account.account_number} is {account.status}",
        )


def _record(
    db: Session,
    account: Account,
    type: str,
    amount: Decimal,
    description: str,
    category: str | None = None,
    related_account_id: int | None = None,
) -> Transaction:
    if category is None:
        signed = float(amount) if type in TransactionType.INCOME_TYPES else -float(amount)
        category, _ = categorize(description, signed)
    txn = Transaction(
        account_id=account.id,
        type=type,
        amount=_q2(amount),
        balance_after=_q2(account.balance),
        description=description or type.replace("_", " ").title(),
        category=category,
        related_account_id=related_account_id,
    )
    db.add(txn)
    return txn


def create_account(db: Session, user: User, data: AccountCreate) -> Account:
    account = Account(
        user_id=user.id,
        account_number=generate_account_number(db),
        account_name=data.account_name,
        account_type=data.account_type,
        currency=data.currency.upper(),
        balance=Decimal("0.00"),
        status=AccountStatus.ACTIVE,
    )
    db.add(account)
    db.flush()  # assign id before ledger row
    if data.initial_deposit > 0:
        account.balance = _q2(data.initial_deposit)
        _record(
            db,
            account,
            TransactionType.DEPOSIT,
            _q2(data.initial_deposit),
            "Opening deposit",
            category="savings",
        )
    db.commit()
    db.refresh(account)
    return account


def deposit(
    db: Session,
    user: User,
    account_id: int,
    amount: Decimal,
    description: str = "",
) -> tuple[Account, Transaction]:
    account = get_owned_account(db, user, account_id)
    _ensure_active(account)
    account.balance = _q2(account.balance + _q2(amount))
    txn = _record(db, account, TransactionType.DEPOSIT, amount, description)
    db.commit()
    db.refresh(account)
    db.refresh(txn)
    return account, txn


def withdraw(
    db: Session,
    user: User,
    account_id: int,
    amount: Decimal,
    description: str = "",
) -> tuple[Account, Transaction]:
    account = get_owned_account(db, user, account_id)
    _ensure_active(account)
    amount = _q2(amount)
    if amount > account.balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient funds (available: {account.balance})",
        )
    account.balance = _q2(account.balance - amount)
    txn = _record(db, account, TransactionType.WITHDRAWAL, amount, description)
    db.commit()
    db.refresh(account)
    db.refresh(txn)
    return account, txn


def transfer(
    db: Session,
    user: User,
    from_account_id: int,
    to_account_number: str,
    amount: Decimal,
    description: str = "",
) -> tuple[Transaction, Transaction]:
    source = get_owned_account(db, user, from_account_id)
    _ensure_active(source)

    to_number = to_account_number.strip().upper()
    dest = db.query(Account).filter_by(account_number=to_number).first()
    if dest is None:
        raise HTTPException(status_code=404, detail="Destination account not found")
    if dest.id == source.id:
        raise HTTPException(
            status_code=400, detail="Cannot transfer to the same account"
        )
    _ensure_active(dest)

    amount = _q2(amount)
    if amount > source.balance:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient funds (available: {source.balance})",
        )

    note = description or f"Transfer to {dest.account_number}"
    # --- atomic: both legs + both ledger rows in ONE commit ---
    source.balance = _q2(source.balance - amount)
    dest.balance = _q2(dest.balance + amount)
    debit = _record(
        db,
        source,
        TransactionType.TRANSFER_OUT,
        amount,
        note,
        category="transfer",
        related_account_id=dest.id,
    )
    credit = _record(
        db,
        dest,
        TransactionType.TRANSFER_IN,
        amount,
        f"Transfer from {source.account_number}",
        category="transfer",
        related_account_id=source.id,
    )
    db.commit()
    db.refresh(debit)
    db.refresh(credit)
    return debit, credit
