from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from datetime import datetime

class AIRecommendationRequest(BaseModel):
    description: str
    subject: Optional[str] = None
    district_code: Optional[str] = None

class AIRecommendationResponse(BaseModel):
    suggested_category_id: Optional[str] = None
    suggested_category_name: Optional[str] = None
    suggested_department_id: Optional[str] = None
    suggested_department_name: Optional[str] = None
    suggested_priority: Optional[str] = None
    confidence: float
    reasoning: str
    provider: str  # 'gemini' or 'rule_fallback'
    model: str

class AIInsightResponse(BaseModel):
    insight_type: str
    summary_text: str
    highlights: List[str] = []
    recurring_themes: List[str] = []
    operational_suggestions: List[str] = []
    provider: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Phase 4 Step 3: District Admin AI Review Queue & Disposition Schemas
# ---------------------------------------------------------------------------

class AIAuditReviewDispositionRequest(BaseModel):
    action: str = Field(..., description="Review action: ACCEPTED, REJECTED, or AMENDED")
    reviewer_notes: str = Field(..., min_length=3, max_length=2000, description="Mandatory notes or justification")
    amended_severity: Optional[str] = Field(None, description="Optional amended severity (INFO, LOW, MEDIUM, HIGH, CRITICAL)")
    amended_explanation: Optional[str] = Field(None, min_length=5, max_length=2000, description="Optional amended explanation")
    amended_facts: Optional[List[str]] = Field(None, description="Optional amended empirical facts list")
    amended_interpretations: Optional[List[str]] = Field(None, description="Optional amended interpretations list")

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        upper_v = v.strip().upper()
        if upper_v not in {"ACCEPTED", "REJECTED", "AMENDED"}:
            raise ValueError(f"Action must be one of ACCEPTED, REJECTED, AMENDED. Received: '{v}'")
        return upper_v

    @field_validator("amended_severity")
    @classmethod
    def validate_amended_severity(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            upper_v = v.strip().upper()
            if upper_v not in {"INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"}:
                raise ValueError(f"amended_severity must be one of INFO, LOW, MEDIUM, HIGH, CRITICAL. Received: '{v}'")
            return upper_v
        return None

    @model_validator(mode="after")
    def validate_amendment(self) -> "AIAuditReviewDispositionRequest":
        if self.action == "AMENDED":
            has_amendment = any([
                self.amended_severity,
                self.amended_explanation,
                self.amended_facts,
                self.amended_interpretations
            ])
            if not has_amendment:
                raise ValueError(
                    "When action is AMENDED, at least one amendment field "
                    "(amended_severity, amended_explanation, amended_facts, or amended_interpretations) must be provided."
                )
        return self


class AIAuditFindingReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    finding_id: str
    reviewer_user_id: Optional[str] = None
    action: str
    reviewer_notes: str
    amended_severity: Optional[str] = None
    amended_explanation: Optional[str] = None
    amended_facts: Optional[List[str]] = None
    amended_interpretations: Optional[List[str]] = None
    created_at: datetime


class AIAuditFindingListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    complaint_id: str
    complaint_no: Optional[str] = None
    complaint_title: Optional[str] = None
    finding_type: str
    severity: str
    current_status: str
    facts: List[str] = []
    interpretations: List[str] = []
    unresolved_questions: List[str] = []
    explanation: str
    evidence_attachment_id: Optional[str] = None
    evidence_assessment: str
    rule_or_model_version: str
    confidence: float
    created_at: datetime
    latest_review: Optional[AIAuditFindingReviewResponse] = None


class AIAuditFindingDetailResponse(AIAuditFindingListItemResponse):
    reviews: List[AIAuditFindingReviewResponse] = []


class AIAuditReviewQueueResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[AIAuditFindingListItemResponse]
