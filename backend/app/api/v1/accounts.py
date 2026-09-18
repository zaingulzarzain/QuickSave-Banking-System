"""Account management + deposits/withdrawals + history."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from ...core.deps import get_current_user
from ...db.session import get_db
from ...models.account import Account
from ...models.transaction import Transaction
from ...models.user import User
from ...schemas.account import (
    AccountCreate,
    AccountLookupOut,
    AccountOut,
    MoneyIn,
)
from ...schemas.transaction import TransactionOut, TransactionPage
from ...services.banking import (
    create_account,
    deposit,
    get_owned_account,
    withdraw,
)

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.get("", response_model=list[AccountOut])
def list_accounts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Account)
        .filter(Account.user_id == user.id)
        .order_by(Account.id)
        .all()
    )


@router.post("", response_model=AccountOut, status_code=201)
def open_account(
    data: AccountCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_account(db, user, data)


@router.get("/lookup/{account_number}", response_model=AccountLookupOut)
def lookup_account(
    account_number: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Resolve a destination account for transfers (privacy-safe preview)."""
    account = (
        db.query(Account)
        .filter_by(account_number=account_number.strip().upper())
        .first()
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    owner = account.owner
    parts = (owner.full_name or "?").split()
    display = parts[0] + (f" {parts[-1][0]}." if len(parts) > 1 else "")
    return AccountLookupOut(
        account_number=account.account_number,
        account_name=account.account_name,
        account_type=account.account_type,
        owner_display=display,
    )


@router.get("/{account_id}", response_model=AccountOut)
def get_account(
    account_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_owned_account(db, user, account_id)


@router.get("/{account_id}/transactions", response_model=TransactionPage)
def account_history(
    account_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    type: str | None = Query(None, description="deposit|withdrawal|transfer_in|transfer_out"),
    category: str | None = None,
    search: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = get_owned_account(db, user, account_id)
    q = db.query(Transaction).filter(Transaction.account_id == account.id)
    if type:
        q = q.filter(Transaction.type == type)
    if category:
        q = q.filter(Transaction.category == category)
    if search:
        like = f"%{search}%"
        q = q.filter(
            or_(
                Transaction.description.ilike(like),
                Transaction.category.ilike(like),
            )
        )
    total = q.count()
    items = (
        q.order_by(desc(Transaction.created_at), desc(Transaction.id))
        .limit(limit)
        .offset(offset)
        .all()
    )
    return TransactionPage(items=items, total=total, limit=limit, offset=offset)


@router.post("/{account_id}/deposit", response_model=TransactionOut)
def make_deposit(
    account_id: int,
    data: MoneyIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _, txn = deposit(db, user, account_id, data.amount, data.description)
    return txn


@router.post("/{account_id}/withdraw", response_model=TransactionOut)
def make_withdrawal(
    account_id: int,
    data: MoneyIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _, txn = withdraw(db, user, account_id, data.amount, data.description)
    return txn
