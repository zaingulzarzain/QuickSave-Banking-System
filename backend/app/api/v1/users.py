"""Current-user profile + dashboard summary."""

import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ...core.deps import get_current_user
from ...db.session import get_db
from ...models.account import Account
from ...models.transaction import Transaction, TransactionType
from ...models.user import User
from ...schemas.user import UserOut, UserSummary, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(
    data: UserUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user.full_name = data.full_name.strip()
    db.commit()
    db.refresh(user)
    return user


@router.get("/me/summary", response_model=UserSummary)
def my_summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    account_ids = [
        row[0]
        for row in db.query(Account.id).filter(Account.user_id == user.id).all()
    ]
    total_balance = (
        db.query(func.coalesce(func.sum(Account.balance), 0))
        .filter(Account.user_id == user.id)
        .scalar()
    )
    month_start = dt.datetime.now(dt.timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=None
    )
    month_rows = (
        db.query(Transaction.type, func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.account_id.in_(account_ids or [-1]),
            Transaction.created_at >= month_start,
        )
        .group_by(Transaction.type)
        .all()
    )
    by_type = {t: float(v) for t, v in month_rows}
    income = sum(by_type.get(t, 0) for t in TransactionType.INCOME_TYPES)
    expenses = sum(by_type.get(t, 0) for t in TransactionType.EXPENSE_TYPES)
    return UserSummary(
        user=UserOut.model_validate(user),
        total_balance=float(total_balance or 0),
        accounts_count=len(account_ids),
        month_income=round(income, 2),
        month_expenses=round(expenses, 2),
    )
