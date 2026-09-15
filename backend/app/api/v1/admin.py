"""Admin-only operations: platform stats, user directory, account controls."""

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from ...core.deps import get_current_admin
from ...db.session import get_db
from ...models.account import Account
from ...models.transaction import Transaction, TransactionType
from ...models.user import User
from ...schemas.account import AccountStatusUpdate
from ...schemas.transaction import TransactionOut
from ...schemas.user import UserOut

router = APIRouter(prefix="/admin", tags=["Admin"])


class AdminStats(BaseModel):
    total_users: int
    total_accounts: int
    total_balance: float
    transactions_today: int
    volume_7d: float


class AdminUserRow(BaseModel):
    user: UserOut
    accounts_count: int
    total_balance: float


class AdminAccountRow(BaseModel):
    id: int
    account_number: str
    account_name: str
    account_type: str
    balance: float
    currency: str
    status: str
    owner_email: str
    owner_name: str


@router.get("/stats", response_model=AdminStats)
def stats(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - dt.timedelta(days=7)
    return AdminStats(
        total_users=db.query(func.count(User.id)).scalar() or 0,
        total_accounts=db.query(func.count(Account.id)).scalar() or 0,
        total_balance=float(
            db.query(func.coalesce(func.sum(Account.balance), 0)).scalar() or 0
        ),
        transactions_today=(
            db.query(func.count(Transaction.id))
            .filter(Transaction.created_at >= start_of_day)
            .scalar()
            or 0
        ),
        volume_7d=float(
            db.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(Transaction.created_at >= week_ago)
            .scalar()
            or 0
        ),
    )


@router.get("/users", response_model=list[AdminUserRow])
def list_users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: str | None = None,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    q = db.query(User).order_by(User.id)
    if search:
        like = f"%{search}%"
        q = q.filter((User.email.ilike(like)) | (User.full_name.ilike(like)))
    users = q.limit(limit).offset(offset).all()
    rows = []
    for u in users:
        accounts = db.query(Account).filter(Account.user_id == u.id).all()
        rows.append(
            AdminUserRow(
                user=UserOut.model_validate(u),
                accounts_count=len(accounts),
                total_balance=round(sum(float(a.balance) for a in accounts), 2),
            )
        )
    return rows


@router.get("/accounts", response_model=list[AdminAccountRow])
def list_accounts(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: str | None = None,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    q = db.query(Account).order_by(Account.id)
    if search:
        like = f"%{search}%"
        q = q.filter(
            (Account.account_number.ilike(like))
            | (Account.account_name.ilike(like))
        )
    accounts = q.limit(limit).offset(offset).all()
    return [
        AdminAccountRow(
            id=a.id,
            account_number=a.account_number,
            account_name=a.account_name,
            account_type=a.account_type,
            balance=float(a.balance),
            currency=a.currency,
            status=a.status,
            owner_email=a.owner.email,
            owner_name=a.owner.full_name,
        )
        for a in accounts
    ]


@router.get("/transactions", response_model=list[TransactionOut])
def all_transactions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return (
        db.query(Transaction)
        .order_by(desc(Transaction.created_at), desc(Transaction.id))
        .limit(limit)
        .offset(offset)
        .all()
    )


@router.patch("/accounts/{account_id}/status")
def set_account_status(
    account_id: int,
    data: AccountStatusUpdate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    account.status = data.status
    db.commit()
    return {"account_id": account.id, "status": account.status}
