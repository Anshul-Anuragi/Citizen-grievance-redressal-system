import uuid
import json
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Float, event
from sqlalchemy.orm import relationship
from app.core.database import Base


class AIRecommendation(Base):
    __tablename__ = "ai_recommendations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    complaint_id = Column(String(36), ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True)
    suggested_category_id = Column(String(36), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    suggested_department_id = Column(String(36), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    suggested_priority = Column(String(20), nullable=True)
    confidence = Column(Float, nullable=False, default=0.0)
    reasoning = Column(Text, nullable=True)
    provider = Column(String(50), nullable=False, default="gemini")  # gemini or rule_fallback
    model = Column(String(50), nullable=False, default="gemini-1.5-flash")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    complaint = relationship("Complaint")
    suggested_category = relationship("Category")
    suggested_department = relationship("Department")


class AIInsight(Base):
    __tablename__ = "ai_insights"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    district_code = Column(String(10), ForeignKey("districts.code"), nullable=True, index=True)
    insight_type = Column(String(50), nullable=False)  # TRENDS, BOTTLENECK, SUMMARY
    summary_text = Column(Text, nullable=False)
    payload = Column(Text, nullable=True)  # JSON string of detailed items
    provider = Column(String(50), nullable=False, default="gemini")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class AIAuditFinding(Base):
    """
    Preserves original, immutable AI and rule-generated audit findings for a complaint.
    Distinguishes observed facts, model interpretations, unresolved questions,
    and evidence corroboration assessments.
    """
    __tablename__ = "ai_audit_findings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    complaint_id = Column(String(36), ForeignKey("complaints.id", ondelete="RESTRICT"), nullable=False, index=True)
    finding_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)  # INFO, LOW, MEDIUM, HIGH, CRITICAL
    facts = Column(Text, nullable=False, default="[]")  # JSON list of observed empirical facts
    interpretations = Column(Text, nullable=False, default="[]")  # JSON list of AI / rule deductions
    unresolved_questions = Column(Text, nullable=False, default="[]")  # JSON list of unanswered questions / gaps
    explanation = Column(Text, nullable=False)
    evidence_attachment_id = Column(String(36), ForeignKey("complaint_attachments.id", ondelete="SET NULL"), nullable=True, index=True)
    evidence_assessment = Column(String(50), nullable=False, default="NOT_ASSESSED")
    # Allowed: NOT_ASSESSED, PRESENT_SUPPORTING, PRESENT_CONTRADICTING, PRESENT_IRRELEVANT, PRESENT_UNASSESSABLE, NOT_PRESENT
    rule_or_model_version = Column(String(100), nullable=False)
    confidence = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships: Deterministic order_by with id tie-breaker
    complaint = relationship("Complaint", back_populates="audit_findings", lazy="selectin")
    evidence_attachment = relationship("ComplaintAttachment", lazy="selectin")
    reviews = relationship(
        "AIAuditFindingReview",
        back_populates="finding",
        cascade="save-update, merge",
        passive_deletes="all",
        order_by="desc(AIAuditFindingReview.created_at), desc(AIAuditFindingReview.id)",
        lazy="selectin"
    )

    @property
    def current_status(self) -> str:
        """Derives current review status from append-only review history."""
        from sqlalchemy import inspect
        state = inspect(self)
        if "reviews" in state.dict and self.reviews:
            return self.reviews[0].action
        return "PENDING_REVIEW"

    @property
    def latest_review(self) -> Optional["AIAuditFindingReview"]:
        from sqlalchemy import inspect
        state = inspect(self)
        if "reviews" in state.dict and self.reviews:
            return self.reviews[0]
        return None

    @property
    def facts_list(self) -> List[str]:
        try:
            return json.loads(self.facts) if self.facts else []
        except Exception:
            return []

    @property
    def interpretations_list(self) -> List[str]:
        try:
            return json.loads(self.interpretations) if self.interpretations else []
        except Exception:
            return []

    @property
    def unresolved_questions_list(self) -> List[str]:
        try:
            return json.loads(self.unresolved_questions) if self.unresolved_questions else []
        except Exception:
            return []


class AIAuditFindingReview(Base):
    """
    Append-only disposition history for human reviews of AI audit findings.
    Preserves original finding and allows multiple review actions over time.
    Updates to existing rows are prohibited at the ORM layer.
    """
    __tablename__ = "ai_audit_finding_reviews"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    finding_id = Column(String(36), ForeignKey("ai_audit_findings.id", ondelete="RESTRICT"), nullable=False, index=True)
    reviewer_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(20), nullable=False, index=True)  # ACCEPTED, REJECTED, AMENDED
    reviewer_notes = Column(Text, nullable=False)
    amended_facts = Column(Text, nullable=True)  # JSON string, nullable
    amended_interpretations = Column(Text, nullable=True)  # JSON string, nullable
    amended_severity = Column(String(20), nullable=True)
    amended_explanation = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    finding = relationship("AIAuditFinding", back_populates="reviews", lazy="selectin")
    reviewer = relationship("User", lazy="selectin")


@event.listens_for(AIAuditFindingReview, "before_update")
def prevent_review_disposition_update(mapper, connection, target):
    raise ValueError("AIAuditFindingReview is strictly append-only: existing review dispositions cannot be updated.")
