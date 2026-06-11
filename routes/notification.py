from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from core.database import get_db
from models.notification import Notification
from schemas.notification import NotificationOut, NotificationUpdate

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("/{user_id}", response_model=List[NotificationOut])
async def get_notifications(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
    )
    notifications = result.scalars().all()
    return notifications

@router.patch("/{notification_id}/read", response_model=NotificationOut)
async def mark_notification_as_read(notification_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Notification).where(Notification.id == notification_id))
    notification = result.scalars().first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    notification.is_read = True
    await db.commit()
    await db.refresh(notification)
    return notification

@router.patch("/read-all/{user_id}", response_model=dict)
async def mark_all_as_read(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Notification).where(Notification.user_id == user_id, Notification.is_read == False))
    notifications = result.scalars().all()
    
    for notification in notifications:
        notification.is_read = True
        
    await db.commit()
    return {"message": f"All notifications for user {user_id} marked as read"}

@router.delete("/{notification_id}", response_model=dict)
async def delete_notification(notification_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Notification).where(Notification.id == notification_id))
    notification = result.scalars().first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    await db.delete(notification)
    await db.commit()
    return {"message": "Notification deleted"}