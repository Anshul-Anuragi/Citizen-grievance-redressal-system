import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Float, ForeignKey, Enum, Text, Integer
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.grievance import PriorityEnum


class ComplaintStatus(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    RECEIVED = "RECEIVED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    ON_HOLD = "ON_HOLD"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"
    REOPENED = "REOPENED"


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    complaint_no = Column(String(50), unique=True, nullable=False, index=True)
    tracking_code = Column(String(50), nullable=False, index=True)
    citizen_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    is_anonymous = Column(Boolean, default=False, nullable=False)
    contact_email = Column(String(255), nullable=True)
    contact_mobile = Column(String(20), nullable=True)

    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    district_code = Column(String(10), ForeignKey("districts.code"), nullable=False, index=True)
    location_address = Column(Text, nullable=False)

    category_id = Column(String(36), ForeignKey("categories.id"), nullable=False, index=True)
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=False, index=True)
    priority = Column(Enum(PriorityEnum), default=PriorityEnum.MEDIUM, nullable=False, index=True)
    status = Column(Enum(ComplaintStatus), default=ComplaintStatus.SUBMITTED, nullable=False, index=True)

    assigned_officer_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    sla_deadline = Column(DateTime(timezone=True), nullable=False, index=True)
    is_overdue = Column(Boolean, default=False, nullable=False, index=True)

    # Resolution Claim details
    resolution_summary = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_claimed_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolution_evidence_attachment_id = Column(String(36), ForeignKey("complaint_attachments.id", ondelete="SET NULL"), nullable=True)

    # Verification details (separates claim from outcome)
    verification_status = Column(String(50), default="UNVERIFIED", nullable=False)  # UNVERIFIED, VERIFIED_SATISFACTORY, VERIFIED_UNSATISFACTORY
    verified_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_remarks = Column(Text, nullable=True)

    closed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    citizen = relationship("User", foreign_keys=[citizen_id])
    district = relationship("District")
    category = relationship("Category")
    department = relationship("Department")
    assigned_officer = relationship("User", foreign_keys=[assigned_officer_id])
    resolution_claimed_by = relationship("User", foreign_keys=[resolution_claimed_by_id])
    resolution_evidence = relationship("ComplaintAttachment", foreign_keys=[resolution_evidence_attachment_id])
    verified_by = relationship("User", foreign_keys=[verified_by_user_id])

    anonymous_sessions = relationship("AnonymousAccessSession", back_populates="complaint", cascade="all, delete-orphan")
    attachments = relationship("ComplaintAttachment", back_populates="complaint", foreign_keys="ComplaintAttachment.complaint_id", cascade="all, delete-orphan")
    status_history = relationship("ComplaintStatusHistory", back_populates="complaint", cascade="all, delete-orphan")
    messages = relationship("ComplaintMessage", back_populates="complaint", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="complaint", uselist=False, cascade="all, delete-orphan")
    escalations = relationship("Escalation", back_populates="complaint", cascade="all, delete-orphan")
    reopen_requests = relationship("ReopenRequest", back_populates="complaint", cascade="all, delete-orphan")
    audit_findings = relationship("AIAuditFinding", back_populates="complaint", cascade="all, delete-orphan", lazy="selectin")


class AnonymousAccessSession(Base):
    __tablename__ = "anonymous_access_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    complaint_id = Column(String(36), ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    complaint = relationship("Complaint", back_populates="anonymous_sessions")


class ComplaintAttachment(Base):
    __tablename__ = "complaint_attachments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    complaint_id = Column(String(36), ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    uploaded_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    complaint = relationship("Complaint", back_populates="attachments", foreign_keys=[complaint_id])


class ComplaintStatusHistory(Base):
    __tablename__ = "complaint_status_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    complaint_id = Column(String(36), ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=False)
    actor_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_role = Column(String(50), nullable=False)  # CITIZEN, ANONYMOUS, DISTRICT_ADMIN, OFFICER, SYSTEM
    remarks = Column(Text, nullable=True)
    evidence_attachment_id = Column(String(36), ForeignKey("complaint_attachments.id", ondelete="SET NULL"), nullable=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    complaint = relationship("Complaint", back_populates="status_history")
    evidence_attachment = relationship("ComplaintAttachment", foreign_keys=[evidence_attachment_id])


class ComplaintMessage(Base):
    __tablename__ = "complaint_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    complaint_id = Column(String(36), ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    sender_role = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    attachment_id = Column(String(36), ForeignKey("complaint_attachments.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    complaint = relationship("Complaint", back_populates="messages")
    attachment = relationship("ComplaintAttachment")


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    complaint_id = Column(String(36), ForeignKey("complaints.id", ondelete="CASCADE"), unique=True, nullable=False)
    rating = Column(Integer, nullable=False)  # 1 to 5
    comments = Column(Text, nullable=True)
    is_satisfied = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    complaint = relationship("Complaint", back_populates="feedback")


class Escalation(Base):
    __tablename__ = "escalations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    complaint_id = Column(String(36), ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    escalated_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(50), default="PENDING", nullable=False)  # PENDING, REVIEWED, DISMISSED
    admin_remarks = Column(Text, nullable=True)
    reviewed_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    complaint = relationship("Complaint", back_populates="escalations")
    escalated_by = relationship("User", foreign_keys=[escalated_by_user_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_user_id])


class ReopenRequest(Base):
    __tablename__ = "reopen_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    complaint_id = Column(String(36), ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True)
    justification = Column(Text, nullable=False)
    evidence_attachment_id = Column(String(36), ForeignKey("complaint_attachments.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(50), default="PENDING", nullable=False)  # PENDING, APPROVED, REJECTED
    reviewed_by_admin_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    complaint = relationship("Complaint", back_populates="reopen_requests")
