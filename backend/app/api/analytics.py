from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.permissions import require_district_admin, enforce_district_isolation
from app.models.user import User
from app.models.grievance import Category, Department, District
from app.models.complaint import Complaint, ComplaintStatus

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/public")
async def get_public_analytics(db: AsyncSession = Depends(get_db)):
    """
    Returns aggregated & anonymized metrics for the public portal landing page.
    STRICT SECURITY REQUIREMENT: NEVER exposes citizen names, emails, phones, or private complaint text!
    """
    total_res = await db.execute(select(func.count(Complaint.id)))
    total_complaints = total_res.scalar() or 0

    resolved_res = await db.execute(
        select(func.count(Complaint.id)).where(Complaint.status.in_([ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED]))
    )
    resolved_count = resolved_res.scalar() or 0

    in_progress_res = await db.execute(
        select(func.count(Complaint.id)).where(Complaint.status == ComplaintStatus.IN_PROGRESS)
    )
    in_progress_count = in_progress_res.scalar() or 0

    # Category breakdown (Aggregated counts only)
    cat_res = await db.execute(
        select(Category.name_en, Category.name_hi, func.count(Complaint.id).label("count"))
        .join(Complaint, Complaint.category_id == Category.id)
        .group_by(Category.id, Category.name_en, Category.name_hi)
        .order_by(func.count(Complaint.id).desc())
        .limit(6)
    )
    categories_breakdown = [
        {"name_en": row[0], "name_hi": row[1], "count": row[2]}
        for row in cat_res.all()
    ]

    # District resolution performance (Aggregated percentages only)
    dist_res = await db.execute(
        select(District.name_en, func.count(Complaint.id).label("count"))
        .join(Complaint, Complaint.district_code == District.code)
        .group_by(District.code, District.name_en)
        .order_by(func.count(Complaint.id).desc())
        .limit(5)
    )
    top_districts = [{"district": row[0], "count": row[1]} for row in dist_res.all()]

    resolution_rate = round((resolved_count / total_complaints * 100), 1) if total_complaints > 0 else 0.0

    return {
        "total_complaints": total_complaints,
        "resolved_complaints": resolved_count,
        "in_progress_complaints": in_progress_count,
        "resolution_rate_percent": resolution_rate,
        "category_trends": categories_breakdown,
        "top_active_districts": top_districts
    }

@router.get("/district-admin")
async def get_district_admin_analytics(
    current_user: User = Depends(require_district_admin),
    db: AsyncSession = Depends(get_db)
):
    district_code = current_user.district_admin_profile.district_code

    # Category Distribution in District
    cat_res = await db.execute(
        select(Category.name_en, func.count(Complaint.id).label("count"))
        .join(Complaint, Complaint.category_id == Category.id)
        .where(Complaint.district_code == district_code)
        .group_by(Category.id, Category.name_en)
    )
    category_distribution = [{"category": r[0], "count": r[1]} for r in cat_res.all()]

    # Priority Breakdown
    prio_res = await db.execute(
        select(Complaint.priority, func.count(Complaint.id).label("count"))
        .where(Complaint.district_code == district_code)
        .group_by(Complaint.priority)
    )
    priority_distribution = [{"priority": r[0].value if hasattr(r[0], 'value') else str(r[0]), "count": r[1]} for r in prio_res.all()]

    # Department Workload
    dept_res = await db.execute(
        select(Department.name_en, func.count(Complaint.id).label("count"))
        .join(Complaint, Complaint.department_id == Department.id)
        .where(Complaint.district_code == district_code)
        .group_by(Department.id, Department.name_en)
    )
    department_workload = [{"department": r[0], "count": r[1]} for r in dept_res.all()]

    return {
        "district_code": district_code,
        "category_distribution": category_distribution,
        "priority_distribution": priority_distribution,
        "department_workload": department_workload
    }
