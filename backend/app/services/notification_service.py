from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import Notification
from app.services.email_service import EmailService

class NotificationService:
    @staticmethod
    async def create_notification(
        db: AsyncSession,
        recipient_user_id: str,
        type: str,
        title: str,
        message: str,
        complaint_id: Optional[str] = None,
        recipient_email: Optional[str] = None
    ) -> Notification:
        """
        Creates an in-app notification in DB and triggers email notification if email exists.
        """
        notification = Notification(
            recipient_user_id=recipient_user_id,
            complaint_id=complaint_id,
            type=type,
            title=title,
            message=message,
            is_read=False
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)

        if recipient_email:
            await EmailService.send_email(
                to_email=recipient_email,
                subject=f"[MP Grievance Redressal] {title}",
                body_text=f"{message}\n\nThank you,\nDigital Grievance Redressal System\nGovernment of Madhya Pradesh"
            )

        return notification
