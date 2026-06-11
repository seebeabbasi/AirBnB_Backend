from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import delete
from typing import List
from core.database import get_db
from models.wishlist import Wishlist
from models.property import Property
from schemas.wishlist import WishlistItem, WishlistToggle
router = APIRouter(prefix="/wishlist", tags=["Wishlist"])

@router.post("/toggle", response_model=dict)
async def toggle_wishlist(data: WishlistToggle, user_id: int, db: AsyncSession = Depends(get_db)):
    # Check if already in wishlist
    result = await db.execute(
        select(Wishlist).where(Wishlist.user_id == user_id, Wishlist.property_id == data.property_id)
    )
    wishlist_item = result.scalar_one_or_none()

    if wishlist_item:
        # Remove from wishlist
        await db.delete(wishlist_item)
        await db.commit()
        return {"message": "Removed from wishlist", "status": "removed"}
    else:
        # Add to wishlist
        new_item = Wishlist(user_id=user_id, property_id=data.property_id)
        db.add(new_item)
        await db.commit()
        return {"message": "Added to wishlist", "status": "added"}

@router.get("/{user_id}", response_model=List[dict])
async def get_user_wishlist(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Wishlist)
        .options(selectinload(Wishlist.property).selectinload(Property.owner))
        .where(Wishlist.user_id == user_id)
    )
    wishlist_items = result.scalars().all()
    
    # Format properties for display
    properties = []
    for item in wishlist_items:
        prop = item.property
        properties.append({
            "id": prop.id,
            "user_id": prop.user_id,
            "name": prop.name,
            "propertyType": prop.propertyType,
            "price": prop.price,
            "image": prop.image,
            "location": prop.location,
            "isActive": prop.isActive,
            "created_at": prop.created_at,
            "owner": {
                "id": prop.owner.id,
                "fullname": prop.owner.fullname,
                "profile_picture": prop.owner.profile_picture
            } if prop.owner else None
        })
    
    return properties

@router.get("/check/{user_id}/{property_id}")
async def check_wishlist_status(user_id: int, property_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Wishlist).where(Wishlist.user_id == user_id, Wishlist.property_id == property_id)
    )
    wishlist_item = result.scalar_one_or_none()
    return {"is_wishlisted": wishlist_item is not None}