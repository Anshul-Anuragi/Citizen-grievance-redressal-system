from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.permissions import require_officer
from app.models.user import User
from app.models.complaint import Complaint, ComplaintStatus, ComplaintAttachment
from app.schemas.complaint import (
    ComplaintResponse, ComplaintDetailResponse,
    ResolveComplaintRequest, HoldComplaintRequest
)
from app.services.complaint_service import ComplaintService
from app.services.assignment_service import AssignmentService
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/officer", tags=["Grievance Officer Workspace"])


@router.get("/dashboard")
async def get_officer_dashboard(
    current_user: User = Depends(require_officer),
    db: AsyncSession = Depends(get_db)
):
    assigned_res = await db.execute(
        select(func.count(Complaint.id)).where(Complaint.assigned_officer_id == current_user.id)
    )
    total_assigned = assigned_res.scalar() or 0

    in_progress_res = await db.execute(
        select(func.count(Complaint.id)).where(
            Complaint.assigned_officer_id == current_user.id,
            Complaint.status == ComplaintStatus.IN_PROGRESS
        )
    )
    in_progress = in_progress_res.scalar() or 0

    on_hold_res = await db.execute(
        select(func.count(Complaint.id)).where(
            Complaint.assigned_officer_id == current_user.id,
            Complaint.status == ComplaintStatus.ON_HOLD
        )
    )
    on_hold = on_hold_res.scalar() or 0

    resolved_res = await db.execute(
        select(func.count(Complaint.id)).where(
            Complaint.assigned_officer_id == current_user.id,
            Complaint.status.in_([ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED])
        )
    )
    resolved = resolved_res.scalar() or 0

    return {
        "officer_name": current_user.full_name,
        "district_code": current_user.officer_profile.district_code if current_user.officer_profile else None,
        "department_id": current_user.officer_profile.department_id if current_user.officer_profile else None,
        "total_assigned": total_assigned,
        "in_progress": in_progress,
        "on_hold": on_hold,
        "resolved": resolved,
        "active_workload": current_user.officer_profile.active_workload if current_user.officer_profile else 0
    }


@router.get("/assigned-complaints", response_model=List[ComplaintResponse])
async def list_assigned_complaints(
    status_filter: Optional[ComplaintStatus] = None,
    current_user: User = Depends(require_officer),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Complaint)
        .options(selectinload(Complaint.district), selectinload(Complaint.department), selectinload(Complaint.category))
        .where(Complaint.assigned_officer_id == current_user.id)
        .order_by(Complaint.created_at.desc())
    )
    if status_filter:
        query = query.where(Complaint.status == status_filter)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/complaints/{complaint_id}/start")
async def start_complaint_resolution(
    complaint_id: str,
    remarks: Optional[str] = None,
    current_user: User = Depends(require_officer),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Complaint).where(Complaint.id == complaint_id))
    complaint = result.scalar_one_or_none()
    if not complaint or complaint.assigned_officer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned complaint not found")

    try:
        await ComplaintService.transition_complaint_status(
            db=db,
            complaint=complaint,
            new_status=ComplaintStatus.IN_PROGRESS,
            actor_user_id=current_user.id,
            actor_role="OFFICER",
            remarks=remarks or "Officer commenced resolution work."
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    await db.commit()
    return {"message": "Complaint status updated to IN_PROGRESS."}


@router.post("/complaints/{complaint_id}/hold")
async def put_complaint_on_hold(
    complaint_id: str,
    payload: Optional[HoldComplaintRequest] = None,
    remarks: Optional[str] = None,
    current_user: User = Depends(require_officer),
    db: AsyncSession = Depends(get_db)
):
    final_remarks = (payload.remarks if payload and payload.remarks else remarks) or ""
    if not final_remarks.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Remarks are required when placing a complaint on hold")

    result = await db.execute(select(Complaint).where(Complaint.id == complaint_id))
    complaint = result.scalar_one_or_none()
    if not complaint or complaint.assigned_officer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned complaint not found")

    try:
        await ComplaintService.transition_complaint_status(
            db=db,
            complaint=complaint,
            new_status=ComplaintStatus.ON_HOLD,
            actor_user_id=current_user.id,
            actor_role="OFFICER",
            remarks=f"On Hold: {final_remarks.strip()}"
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    await db.commit()
    return {"message": "Complaint placed ON_HOLD."}


@router.post("/complaints/{complaint_id}/resolve")
async def mark_complaint_resolved(
    complaint_id: str,
    payload: Optional[ResolveComplaintRequest] = None,
    resolution_summary: Optional[str] = None,
    remarks: Optional[str] = None,
    current_user: User = Depends(require_officer),
    db: AsyncSession = Depends(get_db)
):
    final_summary = (payload.resolution_summary if payload and payload.resolution_summary else resolution_summary) or ""
    final_remarks = (payload.remarks if payload and payload.remarks else remarks) or ""
    evidence_id = payload.evidence_attachment_id if payload else None

    if not final_summary.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Resolution summary is required")

    result = await db.execute(select(Complaint).where(Complaint.id == complaint_id))
    complaint = result.scalar_one_or_none()
    if not complaint or complaint.assigned_officer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned complaint not found")

    if evidence_id:
        att_res = await db.execute(
            select(ComplaintAttachment).where(
                ComplaintAttachment.id == evidence_id,
                ComplaintAttachment.complaint_id == complaint.id
            )
        )
        if not att_res.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Referenced evidence attachment does not belong to this complaint")

    try:
        await ComplaintService.transition_complaint_status(
            db=db,
            complaint=complaint,
            new_status=ComplaintStatus.RESOLVED,
            actor_user_id=current_user.id,
            actor_role="OFFICER",
            remarks=f"Resolution Claim: {final_summary.strip()}. Remarks: {final_remarks.strip()}",
            evidence_attachment_id=evidence_id
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    # Record resolution claim details (distinct from verification outcome)
    complaint.resolution_summary = final_summary.strip()
    complaint.resolution_claimed_by_id = current_user.id
    complaint.resolution_evidence_attachment_id = evidence_id
    complaint.verification_status = "UNVERIFIED"
    db.add(complaint)

    await AssignmentService.update_officer_workload(db, current_user.id, -1)

    if complaint.citizen_id:
        await NotificationService.create_notification(
            db, recipient_user_id=complaint.citizen_id,
            type="RESOLUTION_CLAIMED",
            title=f"Resolution Claimed: {complaint.complaint_no}",
            message=f"The assigned officer has submitted a resolution claim for grievance {complaint.complaint_no}. Please review and verify the outcome.",
            complaint_id=complaint.id
        )

    await db.commit()
    return {"message": "Resolution claim submitted successfully. Status updated to RESOLVED (UNVERIFIED)."}
