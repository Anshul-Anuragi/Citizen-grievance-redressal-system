import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.user import User, OfficerProfile, UserRole

logger = logging.getLogger(__name__)


class AssignmentService:
    @staticmethod
    async def recommend_officer(
        db: AsyncSession,
        district_code: str,
        department_id: str
    ) -> Optional[OfficerProfile]:
        """
        Recommends an eligible officer based on:
        - Same district
        - Matching department
        - Active user status & is_available == True
        - Lowest active workload (round-robin fairness)
        """
        result = await db.execute(
            select(OfficerProfile)
            .join(User, OfficerProfile.user_id == User.id)
            .where(
                OfficerProfile.district_code == district_code,
                OfficerProfile.department_id == department_id,
                OfficerProfile.is_available == True,
                User.is_active == True,
                User.role == UserRole.OFFICER
            )
            .options(selectinload(OfficerProfile.user))
            .order_by(OfficerProfile.active_workload.asc())
        )
        officers = result.scalars().all()
        if officers:
            return officers[0]
        return None

    @staticmethod
    async def update_officer_workload(db: AsyncSession, officer_user_id: str, delta: int) -> None:
        """
        Adjusts the active workload counter for an officer profile.

        Phase 2 fix (H-4): This method no longer calls db.commit() internally.
        The commit responsibility belongs to the calling route handler so that
        the workload update and the complaint status change are part of the
        same transaction, preventing counter drift on partial failures.
        """
        result = await db.execute(
            select(OfficerProfile).where(OfficerProfile.user_id == officer_user_id)
        )
        profile = result.scalar_one_or_none()
        if profile:
            profile.active_workload = max(0, profile.active_workload + delta)
            db.add(profile)
            # NOTE: No db.commit() here — caller owns the transaction.
        else:
            logger.warning(
                "update_officer_workload: no OfficerProfile found for user_id=%s",
                officer_user_id,
            )
