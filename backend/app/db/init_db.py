"""Database bootstrap + deterministic demo-data seeder.

Seeded accounts use FIXED account numbers so the demo is reproducible and
documentable (see README for the accounts you can transfer between).
"""

import datetime as dt
import os
import random
from decimal import Decimal

from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.security import get_password_hash
from ..db.base import Base
from ..db.session import SessionLocal, engine
from ..models import Account, Transaction, User  # noqa: F401  (register tables)
from ..models.account import AccountStatus
from ..models.transaction import TransactionType
from ..services.ai_service import categorize

# Fixed demo account numbers (documented in README)
DEMO_SAVINGS = "QS1000000001"
DEMO_CHECKING = "QS1000000002"
ALEX_CHECKING = "QS1000000003"


def init_db() -> None:
    if os.environ.get("QUICKSAVE_TESTING") == "1":
        return
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if settings.SEED_DEMO_DATA and db.query(User).count() == 0:
            seed_demo_data(db)
    finally:
        db.close()


# ------------------------------------------------------------------ seeding

def _add_txn(
    db: Session,
    account: Account,
    type: str,
    amount: Decimal,
    description: str,
    days_ago: int,
    category: str | None = None,
) -> Transaction:
    """Append a backdated ledger entry, keeping the running balance coherent."""
    if type in TransactionType.EXPENSE_TYPES:
        account.balance = (Decimal(account.balance) - amount).quantize(
            Decimal("0.01")
        )
    else:
        account.balance = (Decimal(account.balance) + amount).quantize(
            Decimal("0.01")
        )
    if category is None:
        signed = float(amount) if type in TransactionType.INCOME_TYPES else -float(amount)
        category, _ = categorize(description, signed)
    txn = Transaction(
        account_id=account.id,
        type=type,
        amount=amount,
        balance_after=account.balance,
        description=description,
        category=category,
        created_at=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
        - dt.timedelta(days=days_ago),
    )
    db.add(txn)
    return txn


def _make_account(
    db: Session,
    user: User,
    number: str,
    name: str,
    type: str,
) -> Account:
    account = Account(
        user_id=user.id,
        account_number=number,
        account_name=name,
        account_type=type,
        balance=Decimal("0.00"),
        currency="USD",
        status=AccountStatus.ACTIVE,
    )
    db.add(account)
    db.flush()
    return account


def seed_demo_data(db: Session) -> None:
    rng = random.Random(42)  # deterministic demo

    demo = User(
        email="demo@quicksave.io",
        full_name="Demo Customer",
        hashed_password=get_password_hash("demo1234"),
    )
    admin = User(
        email="admin@quicksave.io",
        full_name="Ayesha Admin",
        hashed_password=get_password_hash("admin1234"),
        is_admin=True,
    )
    alex = User(
        email="alex.carter@example.com",
        full_name="Alex Carter",
        hashed_password=get_password_hash("alex1234"),
    )
    db.add_all([demo, admin, alex])
    db.flush()

    # ---------------- Demo: savings ----------------
    savings = _make_account(db, demo, DEMO_SAVINGS, "Long-Term Savings", "savings")
    _add_txn(
        db, savings, TransactionType.DEPOSIT, Decimal("10000.00"),
        "Opening deposit", days_ago=90,
    )
    for i, ago in enumerate([60, 30, 7]):
        _add_txn(
            db, savings, TransactionType.DEPOSIT, Decimal("500.00"),
            "Auto-save from checking", days_ago=ago,
        )
    _add_txn(
        db, savings, TransactionType.DEPOSIT, Decimal("84.50"),
        "Quarterly interest payout", days_ago=2,
    )

    # ---------------- Demo: checking (90 days of life) ----------------
    checking = _make_account(
        db, demo, DEMO_CHECKING, "Everyday Checking", "checking"
    )
    _add_txn(
        db, checking, TransactionType.DEPOSIT, Decimal("1500.00"),
        "Opening deposit", days_ago=90,
    )
    events: list[tuple[int, str, Decimal, str]] = []  # (days_ago, type, amount, desc)
    for month_offset, salary_ago in enumerate([85, 55, 25]):
        events.append(
            (salary_ago, TransactionType.DEPOSIT, Decimal("4200.00"),
             "Monthly salary — Acme Corp")
        )
        events.append(
            (salary_ago - 2, TransactionType.WITHDRAWAL, Decimal("1450.00"),
             "Monthly apartment rent")
        )
        events.append(
            (salary_ago - 3, TransactionType.WITHDRAWAL, Decimal("120.00"),
             "Electric + internet bill")
        )
        events.append(
            (salary_ago - 3, TransactionType.WITHDRAWAL, Decimal("500.00"),
             "Auto-save transfer to savings")
        )

    groceries = [
        "Whole Foods grocery run", "Trader Joe's groceries",
        "Carrefour weekly groceries", "Walmart grocery haul",
    ]
    dining = [
        "Starbucks cappuccino", "Pizza night with friends", "KFC family bucket",
        "Cafe brunch", "Burger lab dinner",
    ]
    transport = ["Uber ride downtown", "Careem to office", "Shell fuel refill"]
    fun = ["Netflix subscription", "Spotify subscription", "Cinema tickets"]
    shopping = ["Amazon order — headphones", "Daraz electronics", "Zara outlet"]

    for week in range(12):
        ago = 84 - week * 7
        events.append(
            (ago, TransactionType.WITHDRAWAL,
             Decimal(str(rng.randint(55, 140))), rng.choice(groceries))
        )
        events.append(
            (ago - 2, TransactionType.WITHDRAWAL,
             Decimal(str(rng.randint(8, 45))), rng.choice(dining))
        )
        if week % 2 == 0:
            events.append(
                (ago - 4, TransactionType.WITHDRAWAL,
                 Decimal(str(rng.randint(12, 30))), rng.choice(transport))
            )
    for i, desc in enumerate(fun):
        events.append(
            (80 - i * 27, TransactionType.WITHDRAWAL,
             Decimal(str([15.99, 9.99, 24.00][i])), desc)
        )
    events.append(
        (40, TransactionType.WITHDRAWAL, Decimal("189.00"), shopping[0])
    )
    events.append(
        (12, TransactionType.WITHDRAWAL, Decimal("64.50"), shopping[1])
    )
    events.append(
        (5, TransactionType.WITHDRAWAL, Decimal("2200.00"),
         "MacBook Pro — freelance setup")
    )
    events.append(
        (3, TransactionType.DEPOSIT, Decimal("850.00"),
         "Freelance payout — Upwork")
    )
    events.append(
        (1, TransactionType.WITHDRAWAL, Decimal("18.50"), "Starbucks latte")
    )

    # Apply oldest → newest so balances stay coherent.
    for ago, type, amount, desc in sorted(events, key=lambda e: -e[0]):
        _add_txn(db, checking, type, amount, desc, days_ago=ago)

    # ---------------- Alex: transfer target ----------------
    alex_acc = _make_account(db, alex, ALEX_CHECKING, "Everyday Checking", "checking")
    _add_txn(
        db, alex_acc, TransactionType.DEPOSIT, Decimal("3200.00"),
        "Monthly salary — Globex", days_ago=25,
    )
    _add_txn(
        db, alex_acc, TransactionType.WITHDRAWAL, Decimal("950.00"),
        "Monthly apartment rent", days_ago=23,
    )
    _add_txn(
        db, alex_acc, TransactionType.WITHDRAWAL, Decimal("72.40"),
        "Whole Foods grocery run", days_ago=6,
    )

    db.commit()
    print(
        "\n✅ QuickSave demo data seeded:\n"
        "   customer  demo@quicksave.io  / demo1234\n"
        "   admin     admin@quicksave.io / admin1234\n"
        f"   transfer target: {ALEX_CHECKING} (Alex Carter)\n"
    )


if __name__ == "__main__":  # python -m backend.app.db.init_db
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        if session.query(User).count() == 0:
            seed_demo_data(session)
        else:
            print("Users already exist — skipping seed.")
    finally:
        session.close()
