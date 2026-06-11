from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from typing import List

from core.database import get_db
from models.review import Review
from models.booking import BookingConfirmation
from models.property import Property
from models.user import User
from schemas.review import ReviewCreateGuest, ReviewCreateHost, ReviewResponse, PropertyAverageRating

router = APIRouter(prefix="/reviews", tags=["Reviews"])

@router.post("/guest", response_model=ReviewResponse)
async def create_guest_review(review_in: ReviewCreateGuest, db: AsyncSession = Depends(get_db)):
    # Check if booking exists and is completed
    result = await db.execute(select(BookingConfirmation).where(BookingConfirmation.id == review_in.booking_id))
    booking = result.scalars().first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.status.lower() != "completed":
        raise HTTPException(status_code=400, detail="Reviews can only be submitted after checkout (status: Completed)")
    
    # Check if review already exists
    review_result = await db.execute(select(Review).where(Review.booking_id == review_in.booking_id))
    existing_review = review_result.scalars().first()
    
    if existing_review and existing_review.property_rating is not None:
        raise HTTPException(status_code=400, detail="Guest review already submitted for this booking")
    
    if existing_review:
        existing_review.property_rating = review_in.property_rating
        existing_review.property_review = review_in.property_review
        existing_review.host_rating = review_in.host_rating
        existing_review.host_review = review_in.host_review
        db.add(existing_review)
        await db.commit()
        await db.refresh(existing_review)
        return existing_review
    else:
        new_review = Review(
            booking_id=review_in.booking_id,
            guest_id=booking.guest_id,
            property_id=booking.property_id,
            property_rating=review_in.property_rating,
            property_review=review_in.property_review,
            host_rating=review_in.host_rating,
            host_review=review_in.host_review
        )
        db.add(new_review)
        await db.commit()
        await db.refresh(new_review)
        return new_review
    

@router.get("/guest/{guest_id}", response_model=List[ReviewResponse])
async def get_guest_received_reviews(guest_id: int, db: AsyncSession = Depends(get_db)):
        result = await db.execute(
            select(Review)
           .where(Review.guest_id == guest_id, Review.guest_rating != None)
    )
        return result.scalars().all()


@router.post("/host", response_model=ReviewResponse)
async def create_host_review(review_in: ReviewCreateHost, db: AsyncSession = Depends(get_db)):
    # Check if booking exists and is completed
    result = await db.execute(select(BookingConfirmation).where(BookingConfirmation.id == review_in.booking_id))
    booking = result.scalars().first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.status.lower() != "completed":
        raise HTTPException(status_code=400, detail="Reviews can only be submitted after checkout (status: Completed)")
    
    # Check if review already exists
    review_result = await db.execute(select(Review).where(Review.booking_id == review_in.booking_id))
    existing_review = review_result.scalars().first()
    
    if existing_review and existing_review.guest_rating is not None:
        raise HTTPException(status_code=400, detail="Host review already submitted for this booking")
    
    if existing_review:
        existing_review.guest_rating = review_in.guest_rating
        existing_review.guest_review = review_in.guest_review
        db.add(existing_review)
        await db.commit()
        await db.refresh(existing_review)
        return existing_review
    else:
        new_review = Review(
            booking_id=review_in.booking_id,
            guest_id=booking.guest_id,
            property_id=booking.property_id,
            guest_rating=review_in.guest_rating,
            guest_review=review_in.guest_review
        )
        db.add(new_review)
        await db.commit()
        await db.refresh(new_review)
        return new_review

@router.get("/host/{host_id}", response_model=List[ReviewResponse])
async def get_host_received_reviews(host_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Review)
        .options(selectinload(Review.guest))
        .where(
            Review.property_id.in_(
                select(Property.id).where(Property.user_id == host_id)
            ),
            Review.host_rating != None
        )
    )
    return result.scalars().all()


@router.get("/property/{property_id}", response_model=List[ReviewResponse])
async def get_property_reviews(property_id: int, db: AsyncSession = Depends(get_db)):
    # selectinload used to fetch guest info for display
    result = await db.execute(
        select(Review)
        .options(selectinload(Review.guest))
        .where(Review.property_id == property_id, Review.property_rating != None)
    )
    return result.scalars().all()

@router.get("/property/{property_id}/average", response_model=PropertyAverageRating)
async def get_property_average_rating(property_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            func.avg(Review.property_rating).label("average"),
            func.count(Review.id).label("count")
        ).where(Review.property_id == property_id, Review.property_rating != None)
    )
    stats = result.first()
    return {
        "average_property_rating": round(stats.average, 1) if stats.average else 0.0,
        "total_reviews": stats.count or 0
    }
