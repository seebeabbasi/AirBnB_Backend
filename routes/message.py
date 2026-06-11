from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, and_
from core.database import get_db
from models.message import Message
from models.user import User
from schemas.message import MessageCreate, MessageResponse
from typing import List
from datetime import datetime

router = APIRouter(prefix="/messages", tags=["Messages"])

@router.post("/send", response_model=MessageResponse)
async def send_message(sender_id: int, data: MessageCreate, db: AsyncSession = Depends(get_db)):
    try:
        new_message = Message(
            sender_id=sender_id,
            receiver_id=data.receiver_id,
            content=data.content
        )
        db.add(new_message)
        await db.commit()
        await db.refresh(new_message)
        return new_message
    except Exception as e:
        await db.rollback()
        print(f"Error in send_message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_id}/{other_id}", response_model=List[MessageResponse])
async def get_messages(user_id: int, other_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(Message)
            .where(
                or_(
                    and_(Message.sender_id == user_id, Message.receiver_id == other_id),
                    and_(Message.sender_id == other_id, Message.receiver_id == user_id)
                )
            )
            .order_by(Message.timestamp.asc())
        )
        messages = result.scalars().all()
        
        # Mark messages as read
        for msg in messages:
            if msg.receiver_id == user_id and not msg.is_read:
                msg.is_read = True
        
        await db.commit()
        return messages
    except Exception as e:
        await db.rollback()
        print(f"Error in get_messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations/{user_id}")
async def get_conversations(user_id: int, db: AsyncSession = Depends(get_db)):
    try:
        # Find all unique users this user has messaged or received messages from
        result = await db.execute(
            select(Message.sender_id, Message.receiver_id)
            .where(or_(Message.sender_id == user_id, Message.receiver_id == user_id))
        )
        rows = result.all()
        
        other_user_ids = set()
        for s_id, r_id in rows:
            if s_id != user_id:
                other_user_ids.add(s_id)
            if r_id != user_id:
                other_user_ids.add(r_id)
                
        if not other_user_ids:
            return []
            
        # Get user details for these IDs
        user_result = await db.execute(
            select(User).where(User.id.in_(list(other_user_ids)))
        )
        users = user_result.scalars().all()
        
        conversations = []
        for user in users:
            # Get last message
            last_msg_result = await db.execute(
                select(Message)
                .where(
                    or_(
                        and_(Message.sender_id == user_id, Message.receiver_id == user.id),
                        and_(Message.sender_id == user.id, Message.receiver_id == user_id)
                    )
                )
                .order_by(Message.timestamp.desc())
                .limit(1)
            )
            last_msg = last_msg_result.scalar_one_or_none()
            
            conversations.append({
                "user_id": user.id,
                "fullname": user.fullname,
                "profile_picture": user.profile_picture,
                "last_message": last_msg.content if last_msg else "",
                "last_timestamp": last_msg.timestamp if last_msg else None,
                "unread_count": 0 
            })
            
        # Fix sorting logic: use a dummy min date for missing timestamps to avoid TypeError
        return sorted(conversations, key=lambda x: x["last_timestamp"] or datetime.min, reverse=True)
    except Exception as e:
        print(f"Error in get_conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))