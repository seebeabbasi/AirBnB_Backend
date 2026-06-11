from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class NotificationBase(BaseModel):
    title: str
    message: str
    type: str
    link: Optional[str] = None

class NotificationCreate(NotificationBase):
    user_id: int
    sender_id: Optional[int] = None

class NotificationUpdate(BaseModel):
    is_read: bool

class NotificationOut(NotificationBase):
    id: int
    user_id: int
    sender_id: Optional[int] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True