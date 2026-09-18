"""Transfers + cross-account transaction views."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ...core.deps import get_current_user
from ...db.session import get_db
from ...models.account import Account
from ...models.transaction import Transaction
from ...models.user import User
from ...schemas.transaction import TransferCreate, TransferOut, TransactionOut
from ...services.banking import transfer

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.post("/transfer", response_model=TransferOut)
def make_transfer(
    data: TransferCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    debit, credit = transfer(
        db, user, data.from_account_id, data.to_account_number,
        data.amount, data.description,
    )
    return TransferOut(
        debit=TransactionOut.model_validate(debit),
        credit=TransactionOut.model_validate(credit),
    )


@router.get("/recent", response_model=list[TransactionOut])
def recent_transactions(
    limit: int = Query(10, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account_ids = [
        row[0]
        for row in db.query(Account.id).filter(Account.user_id == user.id).all()
    ]
    return (
        db.query(Transaction)
        .filter(Transaction.account_id.in_(account_ids or [-1]))
        .order_by(desc(Transaction.created_at), desc(Transaction.id))
        .limit(limit)
        .all()
    )


@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction(
    transaction_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    txn = db.get(Transaction, transaction_id)
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if txn.account.user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not your transaction")
    return txn
