import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload, joinedload

from app.core.database import get_db
from app.core.security import get_password_hash
from app.core.permissions import require_district_admin, enforce_district_isolation
from app.models.user import User, UserRole, OfficerProfile, DistrictAdminProfile
from app.models.grievance import Category, Department, CategoryDepartmentMapping, SLARule
from app.models.complaint import Complaint, ComplaintStatus, ReopenRequest, ComplaintStatusHistory, Escalation
from app.models.ai import AIAuditFinding, AIAuditFindingReview
from app.models.audit import AuditLog
from app.schemas.complaint import (
    ComplaintResponse, ComplaintDetailResponse, StatusUpdateRequest,
    AssignOfficerRequest, ComplaintCorrectionRequest, ResolutionVerificationRequest,
    EscalationAdminResponse, EscalationReviewRequest
)
from app.schemas.officer import OfficerCreateRequest, OfficerUpdateRequest, OfficerResponse
from app.schemas.grievance import CategoryResponse, CategoryCreateRequest, CategoryUpdateRequest
from app.schemas.ai import (
    AIAuditReviewQueueResponse, AIAuditFindingListItemResponse,
    AIAuditFindingDetailResponse, AIAuditFindingReviewResponse,
    AIAuditReviewDispositionRequest
)
from app.services.complaint_service import ComplaintService
from app.services.assignment_service import AssignmentService
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/district-admin", tags=["District Admin"])


@router.get("/dashboard")
async def get_district_dashboard(
    current_user: User = Depends(require_district_admin),
    db: AsyncSession = Depends(get_db)
):
    district_code = current_user.district_admin_profile.district_code

    status_counts = {}
    for st in ComplaintStatus:
        res = await db.execute(
            select(func.count(Complaint.id)).where(Complaint.district_code == district_code, Complaint.status == st)
        )
        status_counts[st.value] = res.scalar() or 0

    overdue_res = await db.execute(
        select(func.count(Complaint.id)).where(Complaint.district_code == district_code, Complaint.is_overdue == True)
    )
    overdue_count = overdue_res.scalar() or 0

    officers_res = await db.execute(
        select(func.count(OfficerProfile.id)).where(OfficerProfile.district_code == district_code)
    )
    total_officers = officers_res.scalar() or 0

    reopen_pending_res = await db.execute(
        select(func.count(ReopenRequest.id))
        .join(Complaint, ReopenRequest.complaint_id == Complaint.id)
        .where(Complaint.district_code == district_code, ReopenRequest.status == "PENDING")
    )
    pending_reopens = reopen_pending_res.scalar() or 0

    escalation_pending_res = await db.execute(
        select(func.count(Escalation.id))
        .join(Complaint, Escalation.complaint_id == Complaint.id)
        .where(Complaint.district_code == district_code, Escalation.status == "PENDING")
    )
    pending_escalations = escalation_pending_res.scalar() or 0

    return {
        "district_code": district_code,
        "total_complaints": sum(status_counts.values()),
        "status_breakdown": status_counts,
        "overdue_complaints": overdue_count,
        "total_officers": total_officers,
        "pending_reopen_requests": pending_reopens,
        "pending_escalations": pending_escalations
    }


@router.get("/complaints", response_model=List[ComplaintResponse])
async def list_district_complaints(
    status_filter: Optional[ComplaintStatus] = None,
    department_id: Optional[str] = None,
    is_overdue: Optional[bool] = None,
    search: Optional[str] = None,
    current_user: User = Depends(require_district_admin),
    db: AsyncSession = Depends(get_db)
):
    district_code = current_user.district_admin_profile.district_code

    query = (
        select(Complaint)
        .options(selectinload(Complaint.district), selectinload(Complaint.department), selectinload(Complaint.category))
        .where(Complaint.district_code == district_code)
        .order_by(Complaint.created_at.desc())
    )

    if status_filter:
        query = query.where(Complaint.status == status_filter)
    if department_id:
        query = query.where(Complaint.department_id == department_id)
    if is_overdue is not None:
        query = query.where(Complaint.is_overdue == is_overdue)
    if search:
        search_filter = or_(
            Complaint.complaint_no.ilike(f"%{search}%"),
            Complaint.subject.ilike(f"%{search}%"),
            Complaint.location_address.ilike(f"%{search}%")
        )
        query = query.where(search_filter)

    result = await db.execute(query)
    return result.scalars().all()


@router.patch("/complaints/{complaint_id}/correct")
async def correct_complaint_metadata(
    complaint_id: str,
    data: ComplaintCorrectionRequest,
    current_user: User = Depends(require_district_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Complaint).where(Complaint.id == complaint_id))
    complaint = result.scalar_one_or_none()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
    enforce_district_isolation(current_user, complaint.district_code)

    changes = []
    if data.category_id and data.category_id != complaint.category_id:
        cat_check = await db.execute(select(Category).where(Category.id == data.category_id, Category.is_active == True))
        if not cat_check.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target category invalid or inactive")
        changes.append(f"Category changed from {complaint.category_id} to {data.category_id}")
        complaint.category_id = data.category_id

    if data.department_id and data.department_id != complaint.department_id:
        dept_check = await db.execute(select(Department).where(Department.id == data.department_id, Department.is_active == True))
        if not dept_check.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target department invalid or inactive")
        changes.append(f"Department changed from {complaint.department_id} to {data.department_id}")
        complaint.department_id = data.department_id

    if data.priority and data.priority != complaint.priority:
        changes.append(f"Priority changed from {complaint.priority.value} to {data.priority.value}")
        complaint.priority = data.priority
        new_deadline, _ = await ComplaintService.calculate_sla_deadline(db, complaint.category_id, complaint.priority)
        complaint.sla_deadline = new_deadline

    if not changes:
        return {"message": "No metadata changes detected."}

    db.add(complaint)
    await ComplaintService.record_status_history(
        db, complaint.id, complaint.status.value, complaint.status.value,
        current_user.id, "DISTRICT_ADMIN", f"Metadata correction: {', '.join(changes)}. Remarks: {data.remarks or 'None'}"
    )

    await db.commit()
    return {"message": f"Complaint metadata corrected: {', '.join(changes)}."}


@router.post("/complaints/{complaint_id}/assign")
async def assign_officer_to_complaint(
    complaint_id: str,
    data: AssignOfficerRequest,
    current_user: User = Depends(require_district_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Complaint).where(Complaint.id == complaint_id))
    complaint = result.scalar_one_or_none()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
    enforce_district_isolation(current_user, complaint.district_code)

    if complaint.status in [ComplaintStatus.CLOSED, ComplaintStatus.RESOLVED, ComplaintStatus.REJECTED]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Closed, resolved, or rejected complaints cannot be assigned")

    off_res = await db.execute(
        select(User)
        .options(selectinload(User.officer_profile))
        .where(User.id == data.officer_id, User.role == UserRole.OFFICER)
    )
    officer_user = off_res.scalar_one_or_none()
    if not officer_user or not officer_user.officer_profile or officer_user.officer_profile.district_code != complaint.district_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selected officer does not belong to this district")

    prev_officer_id = complaint.assigned_officer_id
    if prev_officer_id:
        await AssignmentService.update_officer_workload(db, prev_officer_id, -1)

    complaint.assigned_officer_id = officer_user.id

    try:
        await ComplaintService.transition_complaint_status(
            db=db,
            complaint=complaint,
            new_status=ComplaintStatus.ASSIGNED,
            actor_user_id=current_user.id,
            actor_role="DISTRICT_ADMIN",
            remarks=f"Assigned to Officer {officer_user.full_name}. Remarks: {data.remarks or 'None'}"
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    await AssignmentService.update_officer_workload(db, officer_user.id, +1)

    await NotificationService.create_notification(
        db, recipient_user_id=officer_user.id,
        type="ASSIGNMENT",
        title=f"New Assignment: {complaint.complaint_no}",
        message=f"You have been assigned grievance {complaint.complaint_no}: {complaint.subject}",
        complaint_id=complaint.id,
        recipient_email=officer_user.email
    )

    await db.commit()
    return {"message": f"Assigned to {officer_user.full_name} successfully."}


@router.get("/recommend-officer/{complaint_id}")
async def recommend_officer_for_complaint(
    complaint_id: str,
    current_user: User = Depends(require_district_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Complaint).where(Complaint.id == complaint_id))
    complaint = result.scalar_one_or_none()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
    enforce_district_isolation(current_user, complaint.district_code)

    officer_profile = await AssignmentService.recommend_officer(db, complaint.district_code, complaint.department_id)
    if not officer_profile:
        return {"recommended": False, "message": "No eligible active officer found for this department."}

    return {
        "recommended": True,
        "officer_user_id": officer_profile.user_id,
        "officer_name": officer_profile.user.full_name,
        "officer_code": officer_profile.officer_id,
        "active_workload": officer_profile.active_workload
    }


@router.post("/complaints/{complaint_id}/status")
async def update_complaint_status_admin(
    complaint_id: str,
    data: StatusUpdateRequest,
    current_user: User = Depends(require_district_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Complaint).where(Complaint.id == complaint_id))
    complaint = result.scalar_one_or_none()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
    enforce_district_isolation(current_user, complaint.district_code)

    prev_status = complaint.status.value

    try:
        await ComplaintService.transition_complaint_status(
            db=db,
            complaint=complaint,
            new_status=data.status,
            actor_user_id=current_user.id,
            actor_role="DISTRICT_ADMIN",
            remarks=data.remarks or f"Status set to {data.status.value}"
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    if data.status == ComplaintStatus.CLOSED and prev_status != ComplaintStatus.CLOSED.value:
        complaint.closed_at = datetime.now(timezone.utc)
        if complaint.verification_status == "UNVERIFIED":
            complaint.verification_status = "VERIFIED_SATISFACTORY"
            complaint.verified_by_user_id = current_user.id
            complaint.verified_at = datetime.now(timezone.utc)
            complaint.verification_remarks = f"Administrative verification on closure: {data.remarks or 'Closed by admin'}"
        if complaint.assigned_officer_id and prev_status != ComplaintStatus.RESOLVED.value:
            await AssignmentService.update_officer_workload(db, complaint.assigned_officer_id, -1)

    db.add(complaint)
    await db.commit()
    return {"message": f"Status updated to {data.status.value}"}


@router.post("/complaints/{complaint_id}/verify-resolution")
async def verify_complaint_resolution(
    complaint_id: str,
    data: ResolutionVerificationRequest,
    current_user: User = Depends(require_district_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Complaint).where(Complaint.id == complaint_id))
    complaint = result.scalar_one_or_none()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
    enforce_district_isolation(current_user, complaint.district_code)

    if complaint.status != ComplaintStatus.RESOLVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only complaints with status RESOLVED can undergo resolution verification")

    complaint.verification_status = data.verification_status
    complaint.verified_by_user_id = current_user.id
    complaint.verified_at = datetime.now(timezone.utc)
    complaint.verification_remarks = data.remarks or f"District Admin verification: {data.verification_status}"
    db.add(complaint)

    await ComplaintService.record_status_history(
        db=db,
        complaint_id=complaint.id,
        previous_status=complaint.status.value,
        new_status=complaint.status.value,
        actor_user_id=current_user.id,
        actor_role="DISTRICT_ADMIN",
        remarks=f"Resolution Verification: {data.verification_status}. Remarks: {data.remarks or 'None'}"
    )

    await db.commit()
    return {
        "message": f"Resolution claim verified as {data.verification_status}.",
        "verification_status": data.verification_status
    }


# Reopen Request Admin Management Endpoints
@router.get("/reopen-requests")
async def list_district_reopen_requests(
    status_filter: Optional[str] = "PENDING",
    current_user: User = Depends(require_district_admin),
    db: AsyncSession = Depends(get_db)
):
    district_code = current_user.district_admin_profile.district_code
    query = (
        select(ReopenRequest)
        .join(Complaint, ReopenRequest.complaint_id == Complaint.id)
        .options(selectinload(ReopenRequest.complaint))
        .where(Complaint.district_code == district_code)
        .order_by(ReopenRequest.created_at.desc())
    )
    if status_filter and status_filter.upper() != "ALL":
        query = query.where(ReopenRequest.status == status_filter.upper())

    result = await db.execute(query)
    reqs = result.scalars().all()
    return [
        {
            "id": r.id,
            "complaint_id": r.complaint_id,
            "complaint_no": r.complaint.complaint_no if r.complaint else None,
            "subject": r.complaint.subject if r.complaint else None,
            "justification": r.justification,
            "status": r.status,
            "evidence_attachment_id": r.evidence_attachment_id,
            "created_at": r.created_at
        }
        for r in reqs
    ]


@router.post("/reopen-requests/{request_id}/approve")
async def approve_reopen_request(
    request_id: str,
    remarks: Optional[str] = None,
    current_user: User = Depends(require_district_admin),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(ReopenRequest)
        .options(selectinload(ReopenRequest.complaint))
        .where(ReopenRequest.id == request_id)
    )
    req = res.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reopen request not found")

    complaint = req.complaint
    enforce_district_isolation(current_user, complaint.district_code)

    if req.status != "PENDING":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Reopen request is already {req.status}")

    req.status = "APPROVED"
    req.reviewed_by_admin_id = current_user.id
    db.add(req)

    try:
        await ComplaintService.transition_complaint_status(
            db=db,
            complaint=complaint,
            new_status=ComplaintStatus.REOPENED,
            actor_user_id=current_user.id,
            actor_role="DISTRICT_ADMIN",
            remarks=f"Reopen request approved by Admin. Remarks: {remarks or 'Approved'}"
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    if complaint.assigned_officer_id:
        await AssignmentService.update_officer_workload(db, complaint.assigned_officer_id, +1)

    if complaint.citizen_id:
        await NotificationService.create_notification(
            db, recipient_user_id=complaint.citizen_id,
            type="REOPEN_APPROVED",
            title=f"Reopen Approved: {complaint.complaint_no}",
            message=f"Your reopen request for grievance {complaint.complaint_no} has been APPROVED.",
            complaint_id=complaint.id
        )

    if complaint.assigned_officer_id:
        await NotificationService.create_notification(
            db, recipient_user_id=complaint.assigned_officer_id,
            type="REOPEN_ASSIGNMENT",
            title=f"Reopened Grievance {complaint.complaint_no}",
            message=f"Reopened grievance {complaint.complaint_no} has been assigned back to you for action.",
            complaint_id=complaint.id
        )

    await db.commit()
    return {"message": "Reopen request approved successfully. Complaint status set to REOPENED."}


@router.post("/reopen-requests/{request_id}/reject")
async def reject_reopen_request(
    request_id: str,
    remarks: Optional[str] = None,
    current_user: User = Depends(require_district_admin),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(ReopenRequest)
        .options(selectinload(ReopenRequest.complaint))
        .where(ReopenRequest.id == request_id)
    )
    req = res.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reopen request not found")

    complaint = req.complaint
    enforce_district_isolation(current_user, complaint.district_code)

    if req.status != "PENDING":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Reopen request is already {req.status}")

    req.status = "REJECTED"
    req.reviewed_by_admin_id = current_user.id
    db.add(req)

    await ComplaintService.record_status_history(
        db, complaint.id, complaint.status.value, complaint.status.value,
        current_user.id, "DISTRICT_ADMIN", f"Reopen request rejected by Admin. Reason: {remarks or 'Rejected'}"
    )

    if complaint.citizen_id:
        await NotificationService.create_notification(
            db, recipient_user_id=complaint.citizen_id,
            type="REOPEN_REJECTED",
            title=f"Reopen Request Rejected: {complaint.complaint_no}",
            message=f"Your reopen request for grievance {complaint.complaint_no} was rejected. Remarks: {remarks or 'None'}",
            complaint_id=complaint.id
        )

    await db.commit()
    return {"message": "Reopen request rejected."}


# Escalation Management Endpoints
@router.get("/escalations", response_model=List[EscalationAdminResponse])
async def list_district_escalations(
    status_filter: Optional[str] = "PENDING",
    current_user: User = Depends(require_district_admin),
    db: AsyncSession = Depends(get_db)
):
    district_code = current_user.district_admin_profile.district_code
    query = (
        select(Escalation)
        .join(Complaint, Escalation.complaint_id == Complaint.id)
        .options(selectinload(Escalation.complaint))
        .where(Complaint.district_code == district_code)
        .order_by(Escalation.created_at.desc())
    )
    if status_filter and status_filter.upper() != "ALL":
        query = query.where(Escalation.status == status_filter.upper())

    result = await db.execute(query)
    escalations = result.scalars().all()

    return [
        EscalationAdminResponse(
            id=esc.id,
            complaint_id=esc.complaint_id,
            complaint_no=esc.complaint.complaint_no if esc.complaint else None,
            district_code=esc.complaint.district_code if esc.complaint else None,
            reason=esc.reason,
            status=esc.status,
            admin_remarks=esc.admin_remarks,
            escalated_by_user_id=esc.escalated_by_user_id,
            reviewed_by_user_id=esc.reviewed_by_user_id,
            reviewed_at=esc.reviewed_at,
            created_at=esc.created_at
        )
        for esc in escalations
    ]


@router.post("/escalations/{escalation_id}/review")
async def review_escalation(
    escalation_id: str,
    data: EscalationReviewRequest,
    current_user: User = Depends(require_district_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Escalation)
        .options(selectinload(Escalation.complaint))
        .where(Escalation.id == escalation_id)
    )
    esc = result.scalar_one_or_none()
    if not esc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escalation record not found")

    complaint = esc.complaint
    enforce_district_isolation(current_user, complaint.district_code)

    esc.status = data.status
    esc.admin_remarks = data.admin_remarks
    esc.reviewed_by_user_id = current_user.id
    esc.reviewed_at = datetime.now(timezone.utc)
    db.add(esc)

    await ComplaintService.record_status_history(
        db=db,
        complaint_id=complaint.id,
        previous_status=complaint.status.value,
        new_status=complaint.status.value,
        actor_user_id=current_user.id,
        actor_role="DISTRICT_ADMIN",
        remarks=f"Escalation {data.status} by Admin. Remarks: {data.admin_remarks}"
    )

    await db.commit()
    return {"message": f"Escalation marked as {data.status}."}


# SLA Scan Trigger Endpoint
@router.post("/sla/scan-overdue")
async def trigger_sla_overdue_scan(
    current_user: User = Depends(require_district_admin),
    db: AsyncSession = Depends(get_db)
):
    district_code = current_user.district_admin_profile.district_code
    updated_count = await ComplaintService.update_overdue_statuses(db, district_code=district_code)
    return {
        "message": f"SLA scan completed for district {district_code}.",
        "overdue_complaints_flagged": updated_count
    }


# Officer Management Endpoints
@router.get("/officers", response_model=List[OfficerResponse])
async def list_district_officers(
    department_id: Optional[str] = None,
    is_available: Optional[bool] = None,
    current_user: User = Depends(require_district_admin),
    db: AsyncSession = Depends(get_db)
):
    district_code = current_user.district_admin_profile.district_code
    query = (
        select(OfficerProfile)
        .join(User, OfficerProfile.user_id == User.id)
        .options(selectinload(OfficerProfile.user), selectinload(OfficerProfile.department), selectinload(OfficerProfile.district))
        .where(OfficerProfile.district_code == district_code)
        .order_by(OfficerProfile.active_workload.asc())
    )
    if department_id:
        query = query.where(OfficerProfile.department_id == department_id)
    if is_available is not None:
        query = query.where(OfficerProfile.is_available == is_available)

    result = await db.execute(query)
    profiles = result.scalars().all()

    out = []
    for p in profiles:
        out.append(OfficerResponse(
            id=p.id,
            user_id=p.user_id,
            officer_id=p.officer_id,
            district_code=p.district_code,
            department_id=p.department_id,
            is_available=p.is_available,
            is_active=p.user.is_active,
            active_workload=p.active_workload,
            department=p.department,
            district=p.district
        ))
    return out


@router.post("/officers", response_model=OfficerResponse, status_code=status.HTTP_201_CREATED)
async def create_district_officer(
    data: OfficerCreateRequest,
    current_user: User = Depends(require_district_admin),
    db: AsyncSession = Depends(get_db)
):
    admin_district = current_user.district_admin_profile.district_code
    enforce_district_isolation(current_user, data.district_code)

    existing = await db.execute(select(User.id).where(User.email == data.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A user with this email address already exists")

    department = await db.execute(select(Department).where(Department.id == data.department_id, Department.is_active == True))
    if not department.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Selected department not found or inactive")

    count_res = await db.execute(
        select(func.count(OfficerProfile.id)).where(OfficerProfile.district_code == admin_district)
    )
    officer_seq = (count_res.scalar() or 0) + 1
    officer_code = f"OFF-{admin_district}-{officer_seq:03d}"

    user = User(
        email=data.email.lower(),
        password_hash=get_password_hash(data.password),
        full_name=data.full_name,
        mobile=data.mobile,
        role=UserRole.OFFICER,
        is_active=True,
        is_verified=True
    )
    db.add(user)
    await db.flush()

    profile = OfficerProfile(
        user_id=user.id,
        officer_id=officer_code,
        district_code=admin_district,
        department_id=data.department_id,
        is_available=True,
        active_workload=0
    )
    db.add(profile)
    await db.commit()

    res = await db.execute(
        select(OfficerProfile)
        .options(selectinload(OfficerProfile.user), selectinload(OfficerProfile.department), selectinload(OfficerProfile.district))
        .where(OfficerProfile.id == profile.id)
    )
    saved_profile = res.scalar_one()

    return OfficerResponse(
        id=saved_profile.id,
        user_id=saved_profile.user_id,
        officer_id=saved_profile.officer_id,
        district_code=saved_profile.district_code,
        department_id=saved_profile.department_id,
        is_available=saved_profile.is_available,
        is_active=saved_profile.user.is_active,
        active_workload=saved_profile.active_workload,
        department=saved_profile.department,
        district=saved_profile.district
    )


# ---------------------------------------------------------------------------
# Phase 4 Step 3: District Admin AI Review Queue Endpoints
# ---------------------------------------------------------------------------

@router.get("/ai-reviews", response_model=AIAuditReviewQueueResponse)
async def list_ai_audit_reviews(
    severity: Optional[str] = Query(None, description="Filter by severity: INFO, LOW, MEDIUM, HIGH, CRITICAL"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by review status: PENDING_REVIEW, ACCEPTED, REJECTED, AMENDED"),
    limit: int = Query(20, ge=1, le=100, description="Page size (max 100)"),
    offset: int = Query(0, ge=0, description="Page offset"),
    current_user: User = Depends(require_district_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Lists AI audit findings strictly isolated to complaints within the District Admin's district.
    Supports filtering by severity and current human review status.
    Uses bounded pagination and deterministic ordering with tie-breaker.
    """
    if not current_user.district_admin_profile or not current_user.district_admin_profile.district_code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="District Admin has no assigned district"
        )
    district_code = current_user.district_admin_profile.district_code

    valid_severities = {"INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"}
    if severity and severity.upper() not in valid_severities:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid severity filter '{severity}'. Allowed: {', '.join(sorted(valid_severities))}"
        )

    valid_statuses = {"PENDING_REVIEW", "ACCEPTED", "REJECTED", "AMENDED"}
    if status_filter and status_filter.upper() not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status filter '{status_filter}'. Allowed: {', '.join(sorted(valid_statuses))}"
        )

    # Base query strictly joins on complaint.district_code == admin district_code
    base_query = (
        select(AIAuditFinding)
        .join(Complaint, AIAuditFinding.complaint_id == Complaint.id)
        .where(Complaint.district_code == district_code)
    )

    if severity:
        base_query = base_query.where(AIAuditFinding.severity == severity.upper())

    if status_filter:
        latest_action_subq = (
            select(AIAuditFindingReview.action)
            .where(AIAuditFindingReview.finding_id == AIAuditFinding.id)
            .order_by(
                AIAuditFindingReview.created_at.desc(),
                AIAuditFindingReview.id.desc()
            )
            .limit(1)
            .scalar_subquery()
        )
        if status_filter.upper() == "PENDING_REVIEW":
            base_query = base_query.where(latest_action_subq.is_(None))
        else:
            base_query = base_query.where(latest_action_subq == status_filter.upper())

    # Count query
    count_query = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Deterministic query with eager loading to prevent N+1 and lazy-load issues
    items_query = (
        base_query
        .options(
            selectinload(AIAuditFinding.reviews),
            joinedload(AIAuditFinding.complaint)
        )
        .order_by(AIAuditFinding.created_at.desc(), AIAuditFinding.id.desc())
        .offset(offset)
        .limit(limit)
    )
    findings = (await db.execute(items_query)).scalars().all()

    items: List[AIAuditFindingListItemResponse] = []
    for f in findings:
        latest_rev_dto = None
        if f.latest_review:
            latest_rev_dto = AIAuditFindingReviewResponse(
                id=f.latest_review.id,
                finding_id=f.latest_review.finding_id,
                reviewer_user_id=f.latest_review.reviewer_user_id,
                action=f.latest_review.action,
                reviewer_notes=f.latest_review.reviewer_notes,
                amended_severity=f.latest_review.amended_severity,
                amended_explanation=f.latest_review.amended_explanation,
                amended_facts=json.loads(f.latest_review.amended_facts) if f.latest_review.amended_facts else None,
                amended_interpretations=json.loads(f.latest_review.amended_interpretations) if f.latest_review.amended_interpretations else None,
                created_at=f.latest_review.created_at
            )
        items.append(
            AIAuditFindingListItemResponse(
                id=f.id,
                complaint_id=f.complaint_id,
                complaint_no=f.complaint.complaint_no if f.complaint else None,
                complaint_title=f.complaint.subject if f.complaint else None,
                finding_type=f.finding_type,
                severity=f.severity,
                current_status=latest_rev_dto.action if latest_rev_dto else "PENDING_REVIEW",
                facts=f.facts_list,
                interpretations=f.interpretations_list,
                unresolved_questions=f.unresolved_questions_list,
                explanation=f.explanation,
                evidence_attachment_id=f.evidence_attachment_id,
                evidence_assessment=f.evidence_assessment,
                rule_or_model_version=f.rule_or_model_version,
                confidence=f.confidence,
                created_at=f.created_at,
                latest_review=latest_rev_dto
            )
        )

    return AIAuditReviewQueueResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=items
    )


@router.post("/ai-reviews/{finding_id}/disposition", response_model=AIAuditFindingDetailResponse)
async def submit_ai_audit_review_disposition(
    finding_id: str,
    data: AIAuditReviewDispositionRequest,
    current_user: User = Depends(require_district_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Submits a human review disposition (ACCEPTED, REJECTED, or AMENDED) for an AI audit finding.
    Appends a new review record to the immutable review history without altering the original finding.
    Does NOT modify the underlying complaint lifecycle, verification, assignment, workload, or SLA state.
    """
    if not current_user.district_admin_profile or not current_user.district_admin_profile.district_code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="District Admin has no assigned district"
        )
    district_code = current_user.district_admin_profile.district_code

    # Verify finding exists and belongs to a complaint in administrator's district
    finding_query = (
        select(AIAuditFinding)
        .join(Complaint, AIAuditFinding.complaint_id == Complaint.id)
        .options(
            selectinload(AIAuditFinding.reviews),
            joinedload(AIAuditFinding.complaint)
        )
        .where(
            AIAuditFinding.id == finding_id,
            Complaint.district_code == district_code
        )
    )
    res = await db.execute(finding_query)
    finding = res.scalar_one_or_none()
    if not finding:
        # Returns 404 for out-of-district findings without leaking cross-district existence
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI audit finding not found"
        )

    now_utc = datetime.now(timezone.utc)
    review = AIAuditFindingReview(
        finding_id=finding.id,
        reviewer_user_id=current_user.id,
        action=data.action,
        reviewer_notes=data.reviewer_notes.strip(),
        amended_severity=data.amended_severity,
        amended_explanation=data.amended_explanation.strip() if data.amended_explanation else None,
        amended_facts=json.dumps(data.amended_facts) if data.amended_facts else None,
        amended_interpretations=json.dumps(data.amended_interpretations) if data.amended_interpretations else None,
        created_at=now_utc
    )
    db.add(review)

    # Append system audit log entry
    audit_log = AuditLog(
        action="AI_AUDIT_FINDING_REVIEW",
        actor_user_id=current_user.id,
        resource_type="AI_AUDIT_FINDING",
        resource_id=finding.id,
        details=f"Action: {data.action}, Notes: {data.reviewer_notes.strip()[:200]}",
        timestamp=now_utc
    )
    db.add(audit_log)

    await db.commit()
    await db.refresh(review)
    db.expire_all()

    # Re-query finding with reviews populated to ensure deterministic latest-review and current_status
    updated_query = (
        select(AIAuditFinding)
        .options(
            selectinload(AIAuditFinding.reviews),
            joinedload(AIAuditFinding.complaint)
        )
        .where(AIAuditFinding.id == finding_id)
    )
    updated_finding = (await db.execute(updated_query)).scalar_one()

    reviews_dto: List[AIAuditFindingReviewResponse] = []
    for r in updated_finding.reviews:
        reviews_dto.append(
            AIAuditFindingReviewResponse(
                id=r.id,
                finding_id=r.finding_id,
                reviewer_user_id=r.reviewer_user_id,
                action=r.action,
                reviewer_notes=r.reviewer_notes,
                amended_severity=r.amended_severity,
                amended_explanation=r.amended_explanation,
                amended_facts=json.loads(r.amended_facts) if r.amended_facts else None,
                amended_interpretations=json.loads(r.amended_interpretations) if r.amended_interpretations else None,
                created_at=r.created_at
            )
        )

    latest_rev_dto = reviews_dto[0] if reviews_dto else None

    return AIAuditFindingDetailResponse(
        id=updated_finding.id,
        complaint_id=updated_finding.complaint_id,
        complaint_no=updated_finding.complaint.complaint_no if updated_finding.complaint else None,
        complaint_title=updated_finding.complaint.subject if updated_finding.complaint else None,
        finding_type=updated_finding.finding_type,
        severity=updated_finding.severity,
        current_status=latest_rev_dto.action if latest_rev_dto else "PENDING_REVIEW",
        facts=updated_finding.facts_list,
        interpretations=updated_finding.interpretations_list,
        unresolved_questions=updated_finding.unresolved_questions_list,
        explanation=updated_finding.explanation,
        evidence_attachment_id=updated_finding.evidence_attachment_id,
        evidence_assessment=updated_finding.evidence_assessment,
        rule_or_model_version=updated_finding.rule_or_model_version,
        confidence=updated_finding.confidence,
        created_at=updated_finding.created_at,
        latest_review=latest_rev_dto,
        reviews=reviews_dto
    )
