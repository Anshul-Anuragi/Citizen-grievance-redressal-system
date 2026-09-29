from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.permissions import require_district_admin, get_current_user_optional
from app.models.user import User
from app.models.complaint import Complaint, ComplaintStatus
from app.models.grievance import Category
from app.schemas.ai import AIRecommendationRequest, AIRecommendationResponse, AIInsightResponse
from app.services.ai_service import AIService

router = APIRouter(prefix="/ai", tags=["AI Recommendation & Insights"])

@router.post("/recommend", response_model=AIRecommendationResponse)
async def get_ai_recommendation(
    data: AIRecommendationRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns category, department, and priority recommendations.
    Gemini API if available, or keyword rule-engine fallback.
    """
    rec = await AIService.recommend_category_and_priority(
        db,
        complaint_id=None,
        description=data.description,
        subject=data.subject
    )
    return AIRecommendationResponse(
        suggested_category_id=rec.get("suggested_category_id"),
        suggested_category_name=rec.get("suggested_category_name"),
        suggested_department_id=rec.get("suggested_department_id"),
        suggested_priority=rec.get("suggested_priority"),
        confidence=rec.get("confidence", 0.8),
        reasoning=rec.get("reasoning", ""),
        provider=rec.get("provider", "rule_fallback"),
        model=rec.get("model", "keyword-engine")
    )

@router.get("/insights", response_model=AIInsightResponse)
async def get_district_ai_insights(
    current_user: User = Depends(require_district_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Generates District Admin executive AI insights.
    Advisory layer only; never autonomously modifies records.
    """
    district_code = current_user.district_admin_profile.district_code

    total_res = await db.execute(select(func.count(Complaint.id)).where(Complaint.district_code == district_code))
    total = total_res.scalar() or 0

    overdue_res = await db.execute(select(func.count(Complaint.id)).where(Complaint.district_code == district_code, Complaint.is_overdue == True))
    overdue = overdue_res.scalar() or 0

    resolved_res = await db.execute(select(func.count(Complaint.id)).where(Complaint.district_code == district_code, Complaint.status.in_([ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED])))
    resolved = resolved_res.scalar() or 0

    cat_res = await db.execute(
        select(Category.name_en, func.count(Complaint.id).label("count"))
        .join(Complaint, Complaint.category_id == Category.id)
        .where(Complaint.district_code == district_code)
        .group_by(Category.id, Category.name_en)
        .order_by(func.count(Complaint.id).desc())
    )
    top_cats = [{"name": r[0], "count": r[1]} for r in cat_res.all()]

    insights = await AIService.generate_admin_insights(
        db, district_code, total, overdue, resolved, top_cats
    )
    return AIInsightResponse(
        insight_type=insights["insight_type"],
        summary_text=insights["summary_text"],
        highlights=insights["highlights"],
        recurring_themes=insights["recurring_themes"],
        operational_suggestions=insights["operational_suggestions"],
        provider=insights["provider"],
        created_at=insights["created_at"]
    )
