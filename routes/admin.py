from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from typing import List, Optional, Any
from pydantic import BaseModel

from core.database import get_db
from models.user import User
from models.booking import BookingRequest, BookingConfirmation
from models.property import Property
from schemas.user import UserOut

router = APIRouter(prefix="/admin", tags=["Admin"])

# Simplified nested schemas for Admin View
class AdminPropertyInfo(BaseModel):
    id: int
    name: Optional[str] = None
    description_data: Optional[Any] = None
    media: Optional[Any] = None

class AdminBookingItem(BaseModel):
    id: int
    property_id: int
    guest_id: int
    check_in: str
    check_out: str
    total_price: float
    status: str
    guests_details: Optional[Any] = None
    property: Optional[AdminPropertyInfo] = None
    guest: Optional[UserOut] = None

    class Config:
        from_attributes = True

class AdminUsersResponse(BaseModel):
    users: List[UserOut]

class AdminBookingsResponse(BaseModel):
    confirmations: List[AdminBookingItem]
    requests: List[AdminBookingItem]

class AdminStatsResponse(BaseModel):
    total_users: int
    total_properties: int
    total_bookings: int
    verifications: dict

@router.get("/users", response_model=AdminUsersResponse)
async def get_all_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).order_by(User.id.desc()))
    users = result.scalars().all()
    return {"users": users}

@router.get("/bookings", response_model=AdminBookingsResponse)
async def get_all_bookings(db: AsyncSession = Depends(get_db)):
    # Fetch confirmations with eager loading
    conf_result = await db.execute(
        select(BookingConfirmation)
        .options(selectinload(BookingConfirmation.property), selectinload(BookingConfirmation.guest))
        .order_by(BookingConfirmation.id.desc())
    )
    confirmations = conf_result.scalars().all()
    
    # Fetch requests with eager loading
    req_result = await db.execute(
        select(BookingRequest)
        .options(selectinload(BookingRequest.property), selectinload(BookingRequest.guest))
        .order_by(BookingRequest.id.desc())
    )
    requests = req_result.scalars().all()
    
    return {
        "confirmations": confirmations,
        "requests": requests
    }

@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(db: AsyncSession = Depends(get_db)):
    user_count_res = await db.execute(select(func.count(User.id)))
    property_count_res = await db.execute(select(func.count(Property.id)))
    booking_count_res = await db.execute(select(func.count(BookingConfirmation.id)))
    
    # Verification stats
    pending_v = await db.execute(select(func.count(User.id)).where(User.verification_status == "pending"))
    approved_v = await db.execute(select(func.count(User.id)).where(User.verification_status == "approved"))
    rejected_v = await db.execute(select(func.count(User.id)).where(User.verification_status == "rejected"))
    
    return {
        "total_users": user_count_res.scalar() or 0,
        "total_properties": property_count_res.scalar() or 0,
        "total_bookings": booking_count_res.scalar() or 0,
        "verifications": {
            "pending": pending_v.scalar() or 0,
            "approved": approved_v.scalar() or 0,
            "rejected": rejected_v.scalar() or 0
        }
    }

@router.put("/users/{user_id}/verify", response_model=dict)
async def verify_user(user_id: int, status: str, db: AsyncSession = Depends(get_db)):
    if status not in ["approved", "rejected", "pending"]:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.verification_status = status
    await db.commit()
    return {"message": f"User status updated to {status}", "user_id": user_id}