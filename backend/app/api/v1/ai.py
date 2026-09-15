"""AI endpoints: assistant chat, spending insights, categorization."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...core.deps import get_current_user
from ...db.session import get_db
from ...models.user import User
from ...schemas.ai import (
    CategorizeRequest,
    CategorizeResponse,
    ChatRequest,
    ChatResponse,
    InsightsResponse,
)
from ...services import ai_service

router = APIRouter(prefix="/ai", tags=["AI Assistant"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    data: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    history = [{"role": m.role, "content": m.content} for m in data.history]
    result = await ai_service.chat(db, user, data.message, history)
    return ChatResponse(**result)


@router.get("/insights", response_model=InsightsResponse)
async def insights(
    days: int = Query(30, ge=7, le=365),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = await ai_service.spending_insights(db, user, days)
    return InsightsResponse(
        period_days=result["period_days"],
        income=result["income"],
        expenses=result["expenses"],
        net=result["net"],
        savings_rate=result["savings_rate"],
        by_category=result["by_category"],
        daily=result["daily"],
        top_expenses=result["top_expenses"],
        anomalies=result["anomalies"],
        narrative=result["narrative"],
        provider=result["provider"],
    )


@router.post("/categorize", response_model=CategorizeResponse)
def categorize(
    data: CategorizeRequest, user: User = Depends(get_current_user)
):
    category, confidence = ai_service.categorize(data.description, data.amount)
    return CategorizeResponse(category=category, confidence=confidence)
