"""Register all models (importing this module loads every table)."""

from .account import Account, AccountStatus, AccountType  # noqa: F401
from .transaction import Transaction, TransactionType  # noqa: F401
from .user import User  # noqa: F401
