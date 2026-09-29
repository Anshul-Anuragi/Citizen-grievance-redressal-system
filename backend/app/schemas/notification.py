from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    recipient_user_id: str
    complaint_id: Optional[str] = None
    type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime
