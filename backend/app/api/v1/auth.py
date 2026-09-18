"""Auth endpoints: register / login / token / me."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ...core.deps import get_current_user
from ...core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from ...db.session import get_db
from ...models.account import Account, AccountStatus
from ...models.transaction import TransactionType
from ...models.user import User
from ...schemas.account import AccountCreate
from ...schemas.user import Token, UserCreate, UserLogin, UserOut
from ...services.banking import create_account

router = APIRouter(prefix="/auth", tags=["Auth"])

WELCOME_BONUS = Decimal("100.00")


def _authenticate(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email.strip().lower()).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")
    return user


def _issue_token(user: User) -> Token:
    return Token(
        access_token=create_access_token(subject=str(user.id)),
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=Token, status_code=201)
def register(data: UserCreate, db: Session = Depends(get_db)):
    """Create an account — every new user gets a checking account + $100 bonus."""
    email = data.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email is already registered")
    user = User(
        email=email,
        full_name=data.full_name.strip(),
        hashed_password=get_password_hash(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    create_account(
        db,
        user,
        AccountCreate(
            account_type="checking",
            account_name="Everyday Checking",
            initial_deposit=WELCOME_BONUS,
        ),
    )
    # Label the bonus nicely
    bonus = (
        db.query(Account)
        .filter(Account.user_id == user.id)
        .order_by(Account.id)
        .first()
    )
    if bonus and bonus.transactions:
        bonus.transactions[0].description = "Welcome bonus 🎉"
        bonus.transactions[0].category = "savings"
        db.commit()
    db.refresh(user)
    return _issue_token(user)


@router.post("/token", response_model=Token)
def token(
    form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """OAuth2-compatible login (powers the Authorize button in /docs)."""
    user = _authenticate(db, form.username, form.password)
    return _issue_token(user)


@router.post("/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db)):
    """JSON login used by the web app."""
    user = _authenticate(db, data.email, data.password)
    return _issue_token(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
