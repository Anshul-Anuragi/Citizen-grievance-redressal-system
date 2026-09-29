from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.config import settings
from app.core.security import create_access_token, hash_token, generate_random_token, decode_token
from app.core.permissions import get_current_user, get_current_user_optional, enforce_district_isolation, security_scheme
from fastapi.security import HTTPAuthorizationCredentials
from app.models.user import User, UserRole, DistrictAdminProfile
from app.models.grievance import Category, Department, CategoryDepartmentMapping, District
from app.models.complaint import (
    Complaint, AnonymousAccessSession, ComplaintStatus, ComplaintAttachment,
    ComplaintStatusHistory, ComplaintMessage, Feedback, Escalation, ReopenRequest
)
from app.schemas.complaint import (
    ComplaintCreateRequest, AnonymousComplaintCreateRequest, AnonymousTrackRequest,
    AnonymousTrackResponse, ComplaintResponse, ComplaintDetailResponse,
    MessageCreateRequest, FeedbackCreateRequest, ReopenRequestCreateRequest, EscalationCreateRequest
)
from app.schemas.grievance import SimpleCategoryResponse, DistrictResponse, DepartmentResponse, CategoryResponse
from app.services.complaint_service import ComplaintService
from app.services.notification_service import NotificationService
from app.services.ai_service import AIService

router = APIRouter(prefix="/complaints", tags=["Complaints"])


def _authorize_complaint_access(
    complaint: Complaint,
    current_user: Optional[User],
    credentials: Optional[HTTPAuthorizationCredentials],
) -> str:
    """Authorize a user or an anonymous tracking token for one complaint."""
    if current_user:
        if current_user.role == UserRole.CITIZEN:
            if complaint.citizen_id != current_user.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access to this complaint")
        elif current_user.role in [UserRole.DISTRICT_ADMIN, UserRole.OFFICER]:
            enforce_district_isolation(current_user, complaint.district_code)
            if current_user.role == UserRole.OFFICER and complaint.assigned_officer_id != current_user.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Complaint is not assigned to this officer")
        return current_user.role.value

    payload = decode_token(credentials.credentials) if credentials else None
    if (
        complaint.is_anonymous
        and payload
        and payload.get("type") == "access"
        and payload.get("role") == "ANONYMOUS"
        and payload.get("sub") == complaint.id
    ):
        return "ANONYMOUS"

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication or a valid anonymous tracking session is required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def _validate_submission_location(db: AsyncSession, district_code: str) -> None:
    district = await db.execute(
        select(District).where(District.code == district_code.upper(), District.is_active == True)
    )
    if not district.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Selected district not found or inactive")

@router.get("/categories", response_model=List[CategoryResponse])
async def get_public_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.mappings).selectinload(CategoryDepartmentMapping.department))
        .where(Category.is_active == True)
        .order_by(Category.name_en)
    )
    return result.scalars().all()

@router.get("/districts", response_model=List[DistrictResponse])
async def get_public_districts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(District).where(District.is_active == True).order_by(District.name_en))
    return result.scalars().all()

@router.get("/departments", response_model=List[DepartmentResponse])
async def get_public_departments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Department).where(Department.is_active == True).order_by(Department.name_en))
    return result.scalars().all()


@router.post("/submit", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)
async def submit_registered_complaint(
    data: ComplaintCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != UserRole.CITIZEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only registered citizens can submit registered complaints"
        )

    await _validate_submission_location(db, data.district_code)

    # 1. Validate Category
    cat_res = await db.execute(select(Category).where(Category.id == data.category_id, Category.is_active == True))
    category = cat_res.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Selected Category not found or inactive")

    # 2. Get Category -> Department Mapping
    mapping_res = await db.execute(
        select(CategoryDepartmentMapping)
        .where(CategoryDepartmentMapping.category_id == category.id, CategoryDepartmentMapping.is_active == True)
    )
    mapping = mapping_res.scalar_one_or_none()
    department_id = mapping.department_id if mapping else None
    if not department_id:
        # Fallback to first active department
        dept_res = await db.execute(select(Department).where(Department.is_active == True).limit(1))
        dept = dept_res.scalar_one_or_none()
        department_id = dept.id if dept else None
    if not department_id:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No active department is available to receive this complaint")

    # 3. Generate Complaint ID & Tracking Code
    complaint_no = await ComplaintService.generate_complaint_no(db, data.district_code)
    tracking_code = ComplaintService.generate_tracking_code()

    # 4. Calculate SLA Deadline
    deadline, _ = await ComplaintService.calculate_sla_deadline(db, category.id, data.priority)

    # 5. Create Complaint DB Object
    complaint = Complaint(
        complaint_no=complaint_no,
        tracking_code=tracking_code,
        citizen_id=current_user.id,
        is_anonymous=False,
        contact_email=data.contact_email or current_user.email,
        contact_mobile=data.contact_mobile or current_user.mobile,
        subject=data.subject,
        description=data.description,
        district_code=data.district_code.upper(),
        location_address=data.location_address,
        category_id=category.id,
        department_id=department_id,
        priority=data.priority,
        status=ComplaintStatus.SUBMITTED,
        sla_deadline=deadline,
        is_overdue=False
    )
    db.add(complaint)
    await db.commit()
    await db.refresh(complaint)

    # Record initial timeline history
    await ComplaintService.record_status_history(
        db, complaint.id, None, ComplaintStatus.SUBMITTED.value, current_user.id, "CITIZEN", "Complaint submitted by citizen."
    )

    # Optional AI suggestion generation in background
    try:
        await AIService.recommend_category_and_priority(db, complaint.id, complaint.description, complaint.subject)
    except Exception:
        pass

    # Notify District Admin
    admin_profile_res = await db.execute(
        select(DistrictAdminProfile).where(DistrictAdminProfile.district_code == complaint.district_code)
    )
    admin_profile = admin_profile_res.scalar_one_or_none()
    if admin_profile:
        await NotificationService.create_notification(
            db, recipient_user_id=admin_profile.user_id,
            type="NEW_COMPLAINT",
            title=f"New Grievance {complaint.complaint_no}",
            message=f"New grievance submitted in {complaint.district_code}: {complaint.subject}",
            complaint_id=complaint.id
        )

    # Re-fetch full relationships
    res = await db.execute(
        select(Complaint)
        .options(selectinload(Complaint.district), selectinload(Complaint.department), selectinload(Complaint.category))
        .where(Complaint.id == complaint.id)
    )
    return res.scalar_one()

@router.post("/submit-anonymous", status_code=status.HTTP_201_CREATED)
async def submit_anonymous_complaint(
    data: AnonymousComplaintCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    await _validate_submission_location(db, data.district_code)

    # Validate Category
    cat_res = await db.execute(select(Category).where(Category.id == data.category_id, Category.is_active == True))
    category = cat_res.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    mapping_res = await db.execute(
        select(CategoryDepartmentMapping).where(CategoryDepartmentMapping.category_id == category.id, CategoryDepartmentMapping.is_active == True)
    )
    mapping = mapping_res.scalar_one_or_none()
    department_id = mapping.department_id if mapping else None
    if not department_id:
        dept_res = await db.execute(select(Department).where(Department.is_active == True).limit(1))
        dept = dept_res.scalar_one_or_none()
        department_id = dept.id if dept else None
    if not department_id:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No active department is available to receive this complaint")

    complaint_no = await ComplaintService.generate_complaint_no(db, data.district_code)
    tracking_code = ComplaintService.generate_tracking_code()
    deadline, _ = await ComplaintService.calculate_sla_deadline(db, category.id, data.priority)

    complaint = Complaint(
        complaint_no=complaint_no,
        tracking_code=tracking_code,
        citizen_id=None,
        is_anonymous=True,
        contact_email=data.contact_email,
        contact_mobile=data.contact_mobile,
        subject=data.subject,
        description=data.description,
        district_code=data.district_code.upper(),
        location_address=data.location_address,
        category_id=category.id,
        department_id=department_id,
        priority=data.priority,
        status=ComplaintStatus.SUBMITTED,
        sla_deadline=deadline,
        is_overdue=False
    )
    db.add(complaint)
    await db.commit()
    await db.refresh(complaint)

    # Issue Secure Anonymous Token
    raw_token = generate_random_token(36)
    token_hash = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.ANONYMOUS_SESSION_EXPIRE_DAYS)

    session_rec = AnonymousAccessSession(
        complaint_id=complaint.id,
        token_hash=token_hash,
        expires_at=expires_at
    )
    db.add(session_rec)
    
    await ComplaintService.record_status_history(
        db, complaint.id, None, ComplaintStatus.SUBMITTED.value, None, "ANONYMOUS", "Anonymous complaint submitted."
    )

    try:
        await AIService.recommend_category_and_priority(db, complaint.id, complaint.description, complaint.subject)
    except Exception:
        pass

    return {
        "id": complaint.id,
        "complaint_no": complaint_no,
        "tracking_code": tracking_code,
        "anonymous_access_token": raw_token,
        "message": "Anonymous grievance submitted successfully. Save your Complaint ID and Tracking Code for secure access."
    }

@router.post("/track-anonymous", response_model=AnonymousTrackResponse)
async def track_anonymous_complaint(data: AnonymousTrackRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Complaint).where(
            Complaint.complaint_no == data.complaint_no.strip().upper(),
            Complaint.tracking_code == data.tracking_code.strip()
        )
    )
    complaint = result.scalar_one_or_none()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid Complaint ID or Tracking Code")
    if not complaint.is_anonymous:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Anonymous tracking is only available for anonymous complaints")

    raw_token = generate_random_token(36)
    token_hash = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.ANONYMOUS_SESSION_EXPIRE_DAYS)

    session_rec = AnonymousAccessSession(
        complaint_id=complaint.id,
        token_hash=token_hash,
        expires_at=expires_at,
        last_used_at=datetime.now(timezone.utc)
    )
    db.add(session_rec)
    await db.commit()

    # Create temporary JWT token for anonymous session
    jwt_token = create_access_token(
        subject=complaint.id,
        role="ANONYMOUS",
        expires_delta=timedelta(days=settings.ANONYMOUS_SESSION_EXPIRE_DAYS),
    )

    return AnonymousTrackResponse(
        access_token=jwt_token,
        complaint_no=complaint.complaint_no,
        tracking_code=complaint.tracking_code
    )

@router.get("/my-complaints", response_model=List[ComplaintResponse])
async def get_my_complaints(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Complaint)
        .options(selectinload(Complaint.district), selectinload(Complaint.department), selectinload(Complaint.category))
        .where(Complaint.citizen_id == current_user.id)
        .order_by(Complaint.created_at.desc())
    )
    return result.scalars().all()

@router.get("/{complaint_id}", response_model=ComplaintDetailResponse)
async def get_complaint_detail(
    complaint_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Complaint)
        .options(
            selectinload(Complaint.district),
            selectinload(Complaint.department),
            selectinload(Complaint.category),
            selectinload(Complaint.assigned_officer),
            selectinload(Complaint.attachments),
            selectinload(Complaint.status_history),
            selectinload(Complaint.messages),
            selectinload(Complaint.feedback),
            selectinload(Complaint.reopen_requests),
            selectinload(Complaint.escalations)
        )
        .where(or_(Complaint.id == complaint_id, Complaint.complaint_no == complaint_id.upper()))
    )
    complaint = result.scalar_one_or_none()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")

    _authorize_complaint_access(complaint, current_user, credentials)

    detail = ComplaintDetailResponse.model_validate(complaint)
    if complaint.assigned_officer:
        detail.assigned_officer_name = complaint.assigned_officer.full_name
    return detail

@router.post("/{complaint_id}/messages", response_model=ComplaintDetailResponse)
async def add_complaint_message(
    complaint_id: str,
    data: MessageCreateRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Complaint).where(Complaint.id == complaint_id))
    complaint = result.scalar_one_or_none()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")

    actor_role = _authorize_complaint_access(complaint, current_user, credentials)
    msg = ComplaintMessage(
        complaint_id=complaint.id,
        sender_user_id=current_user.id if current_user else None,
        sender_role=actor_role,
        message=data.message
    )
    db.add(msg)
    await db.commit()

    # Return refreshed detail
    return await get_complaint_detail(complaint.id, current_user, credentials, db)

@router.post("/{complaint_id}/feedback")
async def submit_feedback(
    complaint_id: str,
    data: FeedbackCreateRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Complaint).where(Complaint.id == complaint_id))
    complaint = result.scalar_one_or_none()
    if not complaint or complaint.status not in [ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Feedback can only be submitted for resolved/closed complaints")
    _authorize_complaint_access(complaint, current_user, credentials)

    existing = await db.execute(select(Feedback).where(Feedback.complaint_id == complaint.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Feedback has already been submitted for this complaint")

    fb = Feedback(
        complaint_id=complaint.id,
        rating=data.rating,
        comments=data.comments,
        is_satisfied=data.is_satisfied
    )
    db.add(fb)
    # Update verification status on complaint based on citizen feedback
    if data.is_satisfied:
        complaint.verification_status = "VERIFIED_SATISFACTORY"
    else:
        complaint.verification_status = "VERIFIED_UNSATISFACTORY"
    complaint.verified_by_user_id = current_user.id if current_user else None
    complaint.verified_at = datetime.now(timezone.utc)
    complaint.verification_remarks = f"Citizen Feedback: rating={data.rating}, comments={data.comments or 'None'}"
    await db.commit()
    return {"message": "Feedback submitted successfully."}

@router.post("/{complaint_id}/reopen")
async def request_reopen_complaint(
    complaint_id: str,
    data: ReopenRequestCreateRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    Submits a ReopenRequest for RESOLVED or CLOSED complaints.
    The request is set to PENDING for District Admin review and approval.
    Citizen NEVER directly mutates the status string without admin approval.
    """
    result = await db.execute(select(Complaint).where(Complaint.id == complaint_id))
    complaint = result.scalar_one_or_none()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
    actor_role = _authorize_complaint_access(complaint, current_user, credentials)

    if complaint.status not in [ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only RESOLVED or CLOSED complaints can be requested to reopen")

    existing_pending = await db.execute(
        select(ReopenRequest).where(
            ReopenRequest.complaint_id == complaint.id,
            ReopenRequest.status == "PENDING"
        )
    )
    if existing_pending.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A pending reopen request already exists for this complaint")

    req = ReopenRequest(
        complaint_id=complaint.id,
        justification=data.justification,
        evidence_attachment_id=getattr(data, 'evidence_attachment_id', None),
        status="PENDING"
    )
    db.add(req)
    await ComplaintService.record_status_history(
        db, complaint.id, complaint.status.value, complaint.status.value,
        current_user.id if current_user else None, actor_role, f"Reopen Request Submitted: {data.justification}"
    )
    await db.commit()

    admin_profile_res = await db.execute(
        select(DistrictAdminProfile).where(DistrictAdminProfile.district_code == complaint.district_code)
    )
    admin_profile = admin_profile_res.scalar_one_or_none()
    if admin_profile:
        await NotificationService.create_notification(
            db, recipient_user_id=admin_profile.user_id,
            type="REOPEN_REQUEST",
            title=f"Reopen Request for {complaint.complaint_no}",
            message=f"A reopen request was submitted for grievance {complaint.complaint_no}: {data.justification[:100]}",
            complaint_id=complaint.id
        )

    return {"message": "Reopen request submitted successfully for District Admin review.", "status": "PENDING"}

@router.post("/{complaint_id}/escalate")
async def escalate_complaint(
    complaint_id: str,
    data: EscalationCreateRequest,
    current_user: User = Depends(get_current_user),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Complaint).where(Complaint.id == complaint_id))
    complaint = result.scalar_one_or_none()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
    _authorize_complaint_access(complaint, current_user, credentials)

    # Check if a pending escalation already exists for this complaint
    existing_esc = await db.execute(
        select(Escalation).where(
            Escalation.complaint_id == complaint.id,
            Escalation.status == "PENDING"
        )
    )
    if existing_esc.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pending escalation already exists for this complaint"
        )

    escalation = Escalation(
        complaint_id=complaint.id,
        reason=data.reason,
        escalated_by_user_id=current_user.id,
        status="PENDING"
    )
    db.add(escalation)
    await db.commit()
    return {"message": "Escalation logged successfully for District Admin review."}
