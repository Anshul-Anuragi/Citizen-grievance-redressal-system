import random
import string
import zlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Set, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text

from app.models.grievance import Category, SLARule, PriorityEnum
from app.models.complaint import Complaint, ComplaintStatus, ComplaintStatusHistory
from app.models.audit import AuditLog

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Permitted Status Transitions State Machine (Phase 3)
# ---------------------------------------------------------------------------

PERMITTED_TRANSITIONS: Dict[ComplaintStatus, Set[ComplaintStatus]] = {
    ComplaintStatus.SUBMITTED: {
        ComplaintStatus.RECEIVED,
        ComplaintStatus.ASSIGNED,
        ComplaintStatus.REJECTED,
    },
    ComplaintStatus.RECEIVED: {
        ComplaintStatus.ASSIGNED,
        ComplaintStatus.REJECTED,
    },
    ComplaintStatus.ASSIGNED: {
        ComplaintStatus.IN_PROGRESS,
        ComplaintStatus.ASSIGNED,  # Reassignment to another officer
        ComplaintStatus.REJECTED,
    },
    ComplaintStatus.IN_PROGRESS: {
        ComplaintStatus.ON_HOLD,
        ComplaintStatus.RESOLVED,
        ComplaintStatus.ASSIGNED,  # Reassignment
    },
    ComplaintStatus.ON_HOLD: {
        ComplaintStatus.IN_PROGRESS,
        ComplaintStatus.RESOLVED,
        ComplaintStatus.ASSIGNED,  # Reassignment
    },
    ComplaintStatus.RESOLVED: {
        ComplaintStatus.CLOSED,
        ComplaintStatus.REOPENED,
    },
    ComplaintStatus.REOPENED: {
        ComplaintStatus.ASSIGNED,
        ComplaintStatus.IN_PROGRESS,
    },
    ComplaintStatus.CLOSED: {
        ComplaintStatus.REOPENED,  # Through approved reopen request
    },
    ComplaintStatus.REJECTED: {
        ComplaintStatus.REOPENED,  # Upon successful appeal / admin reconsideration
    },
}


class ComplaintService:
    @staticmethod
    def is_transition_permitted(current_status: ComplaintStatus, new_status: ComplaintStatus) -> bool:
        if current_status == new_status:
            return True
        allowed = PERMITTED_TRANSITIONS.get(current_status, set())
        return new_status in allowed

    @staticmethod
    async def transition_complaint_status(
        db: AsyncSession,
        complaint: Complaint,
        new_status: ComplaintStatus,
        actor_user_id: Optional[str],
        actor_role: str,
        remarks: Optional[str] = None,
        evidence_attachment_id: Optional[str] = None,
    ) -> ComplaintStatusHistory:
        """
        Validates lifecycle transition and records status history and audit log.
        Caller controls the transaction boundary (no internal db.commit()).
        """
        if not ComplaintService.is_transition_permitted(complaint.status, new_status):
            raise ValueError(
                f"Invalid complaint status transition from {complaint.status.value} to {new_status.value}."
            )

        prev_status = complaint.status.value
        complaint.status = new_status

        if new_status == ComplaintStatus.CLOSED and not complaint.closed_at:
            complaint.closed_at = datetime.now(timezone.utc)
        elif new_status == ComplaintStatus.RESOLVED and not complaint.resolved_at:
            complaint.resolved_at = datetime.now(timezone.utc)

        db.add(complaint)

        history = await ComplaintService.record_status_history(
            db=db,
            complaint_id=complaint.id,
            previous_status=prev_status,
            new_status=new_status.value,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            remarks=remarks,
            evidence_attachment_id=evidence_attachment_id
        )
        return history

    @staticmethod
    async def generate_complaint_no(db: AsyncSession, district_code: str) -> str:
        year = datetime.now(timezone.utc).year
        prefix = f"{district_code.upper()}-GRV-{year}-"

        bind = db.get_bind()
        dialect_name = bind.dialect.name if bind else "sqlite"

        if dialect_name == "postgresql":
            lock_str = f"complaint_no:{district_code.upper()}:{year}".encode("utf-8")
            lock_key = zlib.crc32(lock_str)
            await db.execute(text("SELECT pg_advisory_xact_lock(:lock_key)"), {"lock_key": lock_key})

        result = await db.execute(
            select(func.count(Complaint.id)).where(Complaint.complaint_no.like(f"{prefix}%"))
        )
        count = result.scalar() or 0
        sequence_num = count + 1

        while True:
            complaint_no = f"{prefix}{sequence_num:06d}"
            existing = await db.execute(select(Complaint.id).where(Complaint.complaint_no == complaint_no))
            if not existing.scalar_one_or_none():
                return complaint_no
            sequence_num += 1

    @staticmethod
    def generate_tracking_code() -> str:
        chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"TRK-{chars}"

    @staticmethod
    async def calculate_sla_deadline(
        db: AsyncSession,
        category_id: str,
        priority: PriorityEnum
    ) -> Tuple[datetime, float]:
        cat_result = await db.execute(select(Category).where(Category.id == category_id))
        category = cat_result.scalar_one_or_none()
        default_hours = category.default_sla_hours if category else 48.0

        multiplier = 1.0
        if priority == PriorityEnum.HIGH:
            multiplier = 0.5
        elif priority == PriorityEnum.LOW:
            multiplier = 1.5

        rule_res = await db.execute(
            select(SLARule).where(SLARule.category_id == category_id, SLARule.priority == priority)
        )
        rule = rule_res.scalar_one_or_none()
        if rule:
            effective_hours = rule.resolution_deadline_hours
        else:
            effective_hours = default_hours * multiplier

        deadline = datetime.now(timezone.utc) + timedelta(hours=effective_hours)
        return deadline, effective_hours

    @staticmethod
    async def record_status_history(
        db: AsyncSession,
        complaint_id: str,
        previous_status: Optional[str],
        new_status: str,
        actor_user_id: Optional[str],
        actor_role: str,
        remarks: Optional[str] = None,
        evidence_attachment_id: Optional[str] = None
    ) -> ComplaintStatusHistory:
        history = ComplaintStatusHistory(
            complaint_id=complaint_id,
            previous_status=previous_status,
            new_status=new_status,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            remarks=remarks,
            evidence_attachment_id=evidence_attachment_id
        )
        db.add(history)

        audit = AuditLog(
            action=f"COMPLAINT_STATUS_{new_status}",
            actor_user_id=actor_user_id,
            resource_type="COMPLAINT",
            resource_id=complaint_id,
            details=f"Status changed from {previous_status} to {new_status}. Remarks: {remarks or 'None'}"
        )
        db.add(audit)
        return history

    @staticmethod
    async def update_overdue_statuses(db: AsyncSession, district_code: Optional[str] = None) -> int:
        now = datetime.now(timezone.utc)
        query = select(Complaint).where(
            Complaint.sla_deadline < now,
            Complaint.status.notin_([ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED, ComplaintStatus.REJECTED]),
            Complaint.is_overdue == False
        )
        if district_code:
            query = query.where(Complaint.district_code == district_code)

        result = await db.execute(query)
        overdue_complaints = result.scalars().all()

        for c in overdue_complaints:
            c.is_overdue = True
            db.add(c)
            await ComplaintService.record_status_history(
                db,
                complaint_id=c.id,
                previous_status=c.status.value,
                new_status=c.status.value,
                actor_user_id=None,
                actor_role="SYSTEM",
                remarks="SLA deadline passed. Complaint marked OVERDUE by system monitor."
            )
        if overdue_complaints:
            await db.commit()
        return len(overdue_complaints)
