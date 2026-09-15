"""AI assistant schemas."""

from typing import Literal

from pydantic import BaseModel, Field

from .transaction import TransactionOut


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=10)


class ChatResponse(BaseModel):
    reply: str
    provider: str
    model: str
    suggestions: list[str] = []


class CategorySlice(BaseModel):
    category: str
    amount: float
    count: int


class DailyPoint(BaseModel):
    date: str
    income: float
    expenses: float


class InsightsResponse(BaseModel):
    period_days: int
    income: float
    expenses: float
    net: float
    savings_rate: float
    by_category: list[CategorySlice]
    daily: list[DailyPoint]
    top_expenses: list[TransactionOut]
    anomalies: list[TransactionOut]
    narrative: str
    provider: str


class CategorizeRequest(BaseModel):
    description: str = Field(min_length=1, max_length=255)
    amount: float = 0


class CategorizeResponse(BaseModel):
    category: str
    confidence: float
