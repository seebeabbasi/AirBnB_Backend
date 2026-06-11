from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
from core.database import get_db
from models.booking import BookingRequest, BookingConfirmation
from models.property import Property
from models.user import User
from models.review import Review
from models.notification import Notification
from schemas.booking import BookingCreate, BookingRequestResponse, BookingConfirmationResponse
router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_booking(booking: BookingCreate, db: AsyncSession = Depends(get_db)):
    # Fetch property
    result = await db.execute(select(Property).where(Property.id == booking.property_id))
    property_obj = result.scalars().first()
    
    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found")
        
    if property_obj.user_id == booking.guest_id:
        raise HTTPException(status_code=400, detail="Owners cannot book their own properties")

    # Fetch guest
    guest_result = await db.execute(select(User).where(User.id == booking.guest_id))
    guest = guest_result.scalars().first()
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")

    # Habit Matching Logic
    pets_data = property_obj.pets_and_habits or {}
    allowed_habits = pets_data.get("habits", [])
    must_match = pets_data.get("habitsAllowed", False)

    if must_match and allowed_habits:
        guest_habits = guest.habbits or []
        allowed_habits = [h for h in allowed_habits if h and h.strip()]
        
        if allowed_habits:
            has_match = False
            for g_habit in guest_habits:
                g_norm = g_habit.lower().strip()
                for a_habit in allowed_habits:
                    a_norm = a_habit.lower().strip()
                    if g_norm in a_norm or a_norm in g_norm:
                        has_match = True
                        break
                if has_match:
                    break
            
            if not has_match:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Habit Mismatch: This property requires matching habits. Allowed: {', '.join(allowed_habits)}. Your habits: {', '.join(guest_habits) if guest_habits else 'None'}"
                )

    # Token deduction
    if booking.tokens_used > 0:
        if guest.tokens < booking.tokens_used:
            raise HTTPException(status_code=400, detail="Insufficient tokens")
        guest.tokens -= booking.tokens_used

    # ─── FIXED: "instant" match karta hai Flutter ke sath ─────────────────────
    policies = property_obj.policies or {}
    booking_type = policies.get("bookingType", "instant")

    if booking_type == "instant":
        reward = 200 if guest.gender and guest.gender.lower() == "female" else 100
        guest.tokens += reward
        
        new_booking = BookingConfirmation(
            property_id=booking.property_id,
            guest_id=booking.guest_id,
            check_in=booking.check_in,
            check_out=booking.check_out,
            guests_details=booking.guests_details,
            total_price=booking.total_price,
            tokens_used=booking.tokens_used,
            booking_type="instant",
            status="confirmed"
        )
        db.add(new_booking)
        
        host_notification = Notification(
            user_id=property_obj.user_id,
            sender_id=booking.guest_id,
            type="booking_confirmed",
            title="New Instant Booking!",
            message=f"{guest.fullname} just booked your property '{property_obj.name}' instantly.",
            link=f"/hosting/bookings"
        )
        db.add(host_notification)
        
        await db.commit()
        await db.refresh(new_booking)
        return {
            "message": f"Booking confirmed instantly. You earned {reward} tokens!",
            "type": "Instant Book",
            "data": new_booking.id
        }
    else:
        new_request = BookingRequest(
            property_id=booking.property_id,
            guest_id=booking.guest_id,
            check_in=booking.check_in,
            check_out=booking.check_out,
            guests_details=booking.guests_details,
            total_price=booking.total_price,
            tokens_used=booking.tokens_used,
            status="pending"
        )
        db.add(new_request)
        
        host_notification = Notification(
            user_id=property_obj.user_id,
            sender_id=booking.guest_id,
            type="booking_request",
            title="New Booking Request",
            message=f"{guest.fullname} has sent a booking request for your property '{property_obj.name}'.",
            link=f"/hosting/bookings"
        )
        db.add(host_notification)
        
        await db.commit()
        await db.refresh(new_request)
        return {
            "message": "Booking request sent to host",
            "type": "Booking Request",
            "data": new_request.id
        }
    

@router.post("/{request_id}/approve", response_model=dict)
async def approve_booking_request(request_id: int, host_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BookingRequest).where(BookingRequest.id == request_id))
    booking_request = result.scalars().first()
    
    if not booking_request:
        raise HTTPException(status_code=404, detail="Booking request not found")
        
    prop_result = await db.execute(select(Property).where(Property.id == booking_request.property_id))
    property_obj = prop_result.scalars().first()
    
    if property_obj.user_id != host_id:
        raise HTTPException(status_code=403, detail="Not authorized to approve this booking")
        
    if booking_request.status != "pending":
        raise HTTPException(status_code=400, detail="Booking is not pending")
        
    booking_request.status = "approved"
    
    # Reward tokens to guest
    guest_result = await db.execute(select(User).where(User.id == booking_request.guest_id))
    guest = guest_result.scalars().first()
    reward = 0
    if guest:
        reward = 200 if guest.gender and guest.gender.lower() == "female" else 100
        guest.tokens += reward

    new_booking = BookingConfirmation(
        request_id=booking_request.id,
        property_id=booking_request.property_id,
        guest_id=booking_request.guest_id,
        check_in=booking_request.check_in,
        check_out=booking_request.check_out,
        guests_details=booking_request.guests_details,
        total_price=booking_request.total_price,
        tokens_used=booking_request.tokens_used,
        booking_type="Booking Request",
        status="confirmed"
    )
    db.add(new_booking)
    
    # Notify Guest about Approval
    guest_notification = Notification(
        user_id=booking_request.guest_id,
        sender_id=host_id,
        type="booking_accepted",
        title="Booking Approved!",
        message=f"Your booking request for '{property_obj.name}' has been approved by the host.",
        link=f"/trips"
    )
    db.add(guest_notification)
    await db.commit()
    return {"message": f"Booking request approved and confirmed. Guest earned {reward} tokens."}


@router.get("/host/{host_id}")
async def get_host_bookings(host_id: int, db: AsyncSession = Depends(get_db)):
    # Get all properties for the host
    prop_result = await db.execute(select(Property).where(Property.user_id == host_id))
    properties = prop_result.scalars().all()
    property_ids = [p.id for p in properties]
    
    if not property_ids:
        return {"requests": [], "confirmations": []}
    
    # Get all pending requests
    req_result = await db.execute(
        select(BookingRequest)
        .options(selectinload(BookingRequest.property), selectinload(BookingRequest.guest))
        .where(BookingRequest.property_id.in_(property_ids))
    )
    requests = req_result.scalars().all()
    
    # Get all confirmations
    conf_result = await db.execute(
        select(BookingConfirmation)
        .options(selectinload(BookingConfirmation.property), selectinload(BookingConfirmation.guest))
        .where(BookingConfirmation.property_id.in_(property_ids))
    )
    confirmations_objs = conf_result.scalars().all()
    
    # Check review status for each confirmation
    confirmations = []
    for c in confirmations_objs:
        review_result = await db.execute(select(Review).where(Review.booking_id == c.id))
        review = review_result.scalars().first()
        
        # Convert to dict and add reviewed flags
        c_dict = {
            "id": c.id,
            "property_id": c.property_id,
            "guest_id": c.guest_id,
            "check_in": c.check_in,
            "check_out": c.check_out,
            "guests_details": c.guests_details,
            "total_price": c.total_price,
            "status": c.status,
            "property": c.property,
            "guest": c.guest,
            "guest_reviewed": bool(review and review.property_rating),
            "host_reviewed": bool(review and review.guest_rating)
        }
        confirmations.append(c_dict)
    
    return {
        "requests": requests,
        "confirmations": confirmations
    }


@router.post("/{request_id}/decline", response_model=dict)
async def decline_booking_request(request_id: int, host_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BookingRequest).where(BookingRequest.id == request_id))
    booking_request = result.scalars().first()
    
    if not booking_request:
        raise HTTPException(status_code=404, detail="Booking request not found")
        
    prop_result = await db.execute(select(Property).where(Property.id == booking_request.property_id))
    property_obj = prop_result.scalars().first()
    
    if property_obj.user_id != host_id:
        raise HTTPException(status_code=403, detail="Not authorized to decline this booking")
        
    if booking_request.status != "pending":
        raise HTTPException(status_code=400, detail="Booking is not pending")
    
    booking_request.status = "declined"
    # Refund tokens if used
    if booking_request.tokens_used > 0:
        guest_result = await db.execute(select(User).where(User.id == booking_request.guest_id))
        guest = guest_result.scalars().first()
        if guest:
            guest.tokens += booking_request.tokens_used
    # Notify Guest about Decline
    guest_notification = Notification(
        user_id=booking_request.guest_id,
        sender_id=host_id,
        type="booking_declined",
        title="Booking Declined",
        message=f"Your booking request for '{property_obj.name}' was declined by the host.",
        link=f"/trips"
    )
    db.add(guest_notification)
    await db.commit()
    return {"message": "Booking request declined and tokens refunded if any"}


@router.get("/guest/{guest_id}")
async def get_guest_bookings(guest_id: int, db: AsyncSession = Depends(get_db)):
    # Get all booking requests for guest
    req_result = await db.execute(
        select(BookingRequest)
        .options(selectinload(BookingRequest.property), selectinload(BookingRequest.guest))
        .where(BookingRequest.guest_id == guest_id)
    )
    requests = req_result.scalars().all()
    # Get all confirmed bookings for guest
    conf_result = await db.execute(
        select(BookingConfirmation)
        .options(selectinload(BookingConfirmation.property), selectinload(BookingConfirmation.guest))
        .where(BookingConfirmation.guest_id == guest_id)
    )
    confirmations_objs = conf_result.scalars().all()

    confirmations = []
    for c in confirmations_objs:
        review_result = await db.execute(select(Review).where(Review.booking_id == c.id))
        review = review_result.scalars().first()
        
        c_dict = {
            "id": c.id,
            "property_id": c.property_id,
            "guest_id": c.guest_id,
            "check_in": c.check_in,
            "check_out": c.check_out,
            "guests_details": c.guests_details,
            "total_price": c.total_price,
            "status": c.status,
            "property": c.property,
            "guest": c.guest,
            "reviewed": bool(review and review.property_rating)
        }
        confirmations.append(c_dict)
    
    return {
        "requests": requests,
        "confirmations": confirmations
    }


@router.get("/{booking_id}")
async def get_booking_detail(booking_id: int, is_request: bool = False, db: AsyncSession = Depends(get_db)):
    if is_request:
        result = await db.execute(
            select(BookingRequest)
            .options(selectinload(BookingRequest.property), selectinload(BookingRequest.guest))
            .where(BookingRequest.id == booking_id)
        )
    else:
        result = await db.execute(
            select(BookingConfirmation)
            .options(selectinload(BookingConfirmation.property), selectinload(BookingConfirmation.guest))
            .where(BookingConfirmation.id == booking_id)
        )
    booking = result.scalars().first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.get("/property/{property_id}/booked-dates")
async def get_property_booked_dates(property_id: int, db: AsyncSession = Depends(get_db)):
    # Fetch confirmed bookings for this property to block dates
    result = await db.execute(
        select(BookingConfirmation.check_in, BookingConfirmation.check_out)
        .where(BookingConfirmation.property_id == property_id)
    )
    bookings = result.all()
    # We also might want to include pending requests if those shouldn't be overridden
    # For now, let's include both pending requests and confirmed bookings
    req_result = await db.execute(
        select(BookingRequest.check_in, BookingRequest.check_out)
        .where(BookingRequest.property_id == property_id, BookingRequest.status == "pending")
    )
    requests = req_result.all()
    booked_ranges = []
    for b in bookings:
        booked_ranges.append({"start": b.check_in, "end": b.check_out})
        
    for r in requests:
        booked_ranges.append({"start": r.check_in, "end": r.check_out})
        
    return {"booked_dates": booked_ranges}

@router.put("/{booking_id}/complete", response_model=dict)
async def complete_booking(booking_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BookingConfirmation).where(BookingConfirmation.id == booking_id))
    booking = result.scalars().first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking.status = "Completed"
    await db.commit()
    return {"message": "Booking marked as completed", "status": "Completed"}


@router.post("/{booking_id}/cancel", response_model=dict)
async def cancel_booking(booking_id: int, user_id: int, is_request: bool = False, db: AsyncSession = Depends(get_db)):
    from datetime import datetime, timedelta
    
    if is_request:
        result = await db.execute(select(BookingRequest).where(BookingRequest.id == booking_id))
        booking = result.scalars().first()
    else:
        result = await db.execute(select(BookingConfirmation).where(BookingConfirmation.id == booking_id))
        booking = result.scalars().first()
        
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    if booking.guest_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this booking")
        
    if booking.status in ["cancelled", "declined", "completed"]:
        raise HTTPException(status_code=400, detail=f"Booking already {booking.status}")

    prop_result = await db.execute(select(Property).where(Property.id == booking.property_id))
    property_obj = prop_result.scalars().first()
    
    policies = property_obj.policies or {}
    cancellation_type = policies.get("cancellation", "Flexible")
    
    # ✅ FIX: Flutter se "2025-06-15T00:00:00.000" aata hai
    # pehle sirf "%Y-%m-%d" tha jo crash karta tha
    try:
        date_str = booking.check_in.split("T")[0]
        check_in_date = datetime.fromisoformat(date_str)
        days_until = (check_in_date - datetime.now()).days
    except Exception:
        days_until = 0

    message = ""
    if cancellation_type == "Flexible":
        if days_until >= 1:
            message = "Cancellation successful. You are eligible for a full refund as per the Flexible policy (cancelled > 24h before check-in)."
        else:
            message = "Cancellation successful. Since it's less than 24h before check-in, a partial charge may apply according to the Flexible policy."
    elif cancellation_type == "Moderate":
        if days_until >= 5:
            message = "Cancellation successful. You are eligible for a full refund as per the Moderate policy (cancelled > 5 days before check-in)."
        else:
            message = "Cancellation successful. Since it's less than 5 days before check-in, the first night and service fees are non-refundable."
    elif cancellation_type == "Strict":
        if days_until >= 7:
            message = "Cancellation successful. You are eligible for a 50% refund as per the Strict policy (cancelled > 1 week before check-in)."
        else:
            message = "Cancellation successful. This booking is non-refundable as it's less than 1 week before check-in under the Strict policy."
    else:
        message = "Booking cancelled successfully according to the property policy."

    booking.status = "cancelled"
    
    guest_result = await db.execute(select(User).where(User.id == booking.guest_id))
    guest = guest_result.scalars().first()
    if guest:
        if booking.tokens_used > 0:
            guest.tokens += booking.tokens_used
            
        if not is_request:
            earned = 200 if guest.gender and guest.gender.lower() == "female" else 100
            guest.tokens = max(0, guest.tokens - earned)

    host_notification = Notification(
        user_id=property_obj.user_id,
        sender_id=user_id,
        type="booking_cancelled",
        title="Booking Cancelled",
        message=f"{guest.fullname} has cancelled their booking for '{property_obj.name}'.",
        link=f"/hosting/bookings"
    )
    db.add(host_notification)
    await db.commit()
    return {"message": message, "status": "cancelled"}