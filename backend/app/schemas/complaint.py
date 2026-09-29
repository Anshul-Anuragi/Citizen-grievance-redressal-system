from typing import Optional, List
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from datetime import datetime
from app.models.grievance import PriorityEnum
from app.models.complaint import ComplaintStatus
from app.schemas.grievance import DistrictResponse, DepartmentResponse, SimpleCategoryResponse


class ComplaintCreateRequest(BaseModel):
    subject: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=10, max_length=5000)
    district_code: str
    location_address: str
    category_id: str
    priority: PriorityEnum = PriorityEnum.MEDIUM
    contact_email: Optional[EmailStr] = None
    contact_mobile: Optional[str] = None

    @field_validator('contact_email', mode='before')
    @classmethod
    def sanitize_contact_email(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return None
        return v

    @field_validator('contact_mobile', mode='before')
    @classmethod
    def sanitize_contact_mobile(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return None
        return v


class AnonymousComplaintCreateRequest(ComplaintCreateRequest):
    contact_email: Optional[EmailStr] = None
    contact_mobile: Optional[str] = None


class AnonymousTrackRequest(BaseModel):
    complaint_no: str
    tracking_code: str


class AnonymousTrackResponse(BaseModel):
    access_token: str
    complaint_no: str
    tracking_code: str
    token_type: str = "bearer"


class ComplaintAttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    file_name: str
    file_path: str
    file_type: str
    file_size: int
    uploaded_at: datetime


class ComplaintStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    previous_status: Optional[str] = None
    new_status: str
    actor_role: str
    remarks: Optional[str] = None
    evidence_attachment_id: Optional[str] = None
    timestamp: datetime


class ComplaintMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sender_role: str
    message: str
    created_at: datetime
    attachment: Optional[ComplaintAttachmentResponse] = None


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rating: int
    comments: Optional[str] = None
    is_satisfied: bool
    created_at: datetime


class ReopenRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    justification: str
    evidence_attachment_id: Optional[str] = None
    status: str
    created_at: datetime


class EscalationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reason: str
    status: str
    admin_remarks: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime


class EscalationAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    complaint_id: str
    complaint_no: Optional[str] = None
    district_code: Optional[str] = None
    reason: str
    status: str
    admin_remarks: Optional[str] = None
    escalated_by_user_id: Optional[str] = None
    reviewed_by_user_id: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime


class EscalationReviewRequest(BaseModel):
    status: str = Field(..., pattern="^(REVIEWED|DISMISSED)$")
    admin_remarks: str = Field(..., min_length=3, max_length=1000)


class ComplaintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    complaint_no: str
    tracking_code: str
    is_anonymous: bool
    subject: str
    description: str
    district_code: str
    location_address: str
    category_id: str
    department_id: str
    priority: PriorityEnum
    status: ComplaintStatus
    assigned_officer_id: Optional[str] = None
    assigned_officer_name: Optional[str] = None
    sla_deadline: datetime
    is_overdue: bool
    created_at: datetime
    updated_at: datetime

    # Resolution Claim & Verification fields
    resolution_summary: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_claimed_by_id: Optional[str] = None
    resolution_evidence_attachment_id: Optional[str] = None
    verification_status: str = "UNVERIFIED"
    verified_by_user_id: Optional[str] = None
    verified_at: Optional[datetime] = None
    verification_remarks: Optional[str] = None

    closed_at: Optional[datetime] = None

    district: Optional[DistrictResponse] = None
    department: Optional[DepartmentResponse] = None
    category: Optional[SimpleCategoryResponse] = None


class ComplaintDetailResponse(ComplaintResponse):
    attachments: List[ComplaintAttachmentResponse] = []
    status_history: List[ComplaintStatusHistoryResponse] = []
    messages: List[ComplaintMessageResponse] = []
    feedback: Optional[FeedbackResponse] = None
    reopen_requests: List[ReopenRequestResponse] = []
    escalations: List[EscalationResponse] = []


class StatusUpdateRequest(BaseModel):
    status: ComplaintStatus
    remarks: Optional[str] = None
    resolution_summary: Optional[str] = None


class ResolutionVerificationRequest(BaseModel):
    verification_status: str = Field(..., pattern="^(VERIFIED_SATISFACTORY|VERIFIED_UNSATISFACTORY)$")
    remarks: Optional[str] = None


class AssignOfficerRequest(BaseModel):
    officer_id: str
    remarks: Optional[str] = None


class ComplaintCorrectionRequest(BaseModel):
    category_id: Optional[str] = None
    department_id: Optional[str] = None
    priority: Optional[PriorityEnum] = None
    remarks: Optional[str] = None


class MessageCreateRequest(BaseModel):
    message: str = Field(..., min_length=1)


class FeedbackCreateRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comments: Optional[str] = None
    is_satisfied: bool


class ReopenRequestCreateRequest(BaseModel):
    justification: str = Field(..., min_length=10)
    evidence_attachment_id: Optional[str] = None


class EscalationCreateRequest(BaseModel):
    reason: str = Field(..., min_length=10)


class ResolveComplaintRequest(BaseModel):
    resolution_summary: Optional[str] = None
    remarks: Optional[str] = None
    evidence_attachment_id: Optional[str] = None


class HoldComplaintRequest(BaseModel):
    remarks: Optional[str] = None
