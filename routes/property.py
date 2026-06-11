from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_, cast, Text, Integer, Boolean
from typing import List, Optional, Any, Dict
from pydantic import BaseModel
from models.booking import BookingConfirmation, BookingRequest
from datetime import datetime, date
from datetime import datetime
import base64
import uuid
import os
from core.database import get_db
from models.property import Property
from models.review import Review
from sqlalchemy import func

router = APIRouter(prefix="/properties", tags=["Properties"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

class PropertyCreate(BaseModel):
    user_id: int
    name: str
    propertyType: str
    structure: Optional[str] = None
    placeType: Optional[str] = None
    status: Optional[str] = "active"
    isActive: Optional[bool] = True
    price: float
    image: Optional[str] = None
    guests: Dict[str, Any]
    rooms: List[Dict[str, Any]]
    amenities: List[str]
    location: Dict[str, Any]
    media: Dict[str, Any]
    description_data: Optional[Dict[str, Any]] = None
    pets_and_habits: Optional[Dict[str, Any]] = None
    policies: Optional[Dict[str, Any]] = None
    pricing: Dict[str, Any]
    safety: Optional[Dict[str, Any]] = None
    services: Optional[List[Dict[str, Any]]] = None
    available_from: Optional[str] = None
    available_to: Optional[str] = None
    floors: Optional[int] = 0
    gender: Optional[str] = "Mixed"

class SearchFilters(BaseModel):
    minPrice: Optional[float] = None
    maxPrice: Optional[float] = None
    propertyTypes: Optional[List[str]] = None
    amenities: Optional[List[str]] = None
    highlights: Optional[List[str]] = None
    roomTypes: Optional[List[str]] = None
    cancellationPolicies: Optional[List[str]] = None
    safetyFeatures: Optional[List[str]] = None
    petsAllowed: Optional[bool] = None
    habitsAllowed: Optional[bool] = None
    habits: Optional[List[str]] = None
    guests: Optional[Dict[str, int]] = None
    location: Optional[str] = None
    checkIn: Optional[str] = None
    checkOut: Optional[str] = None
    services: Optional[List[str]] = None
    bedTypes: Optional[List[str]] = None
    numRooms: Optional[int] = None
    bookingType: Optional[str] = None
    gender: Optional[str] = None

def save_base64_image(base64_str: str) -> str:
    if not base64_str or not base64_str.startswith("data:image"):
        return base64_str
    try:
        format, imgstr = base64_str.split(';base64,')
        ext = format.split('/')[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(base64.b64decode(imgstr))
        return f"/uploads/{filename}"
    except Exception as e:
        print(f"Error saving image: {e}")
        return base64_str


def calculate_occupancy(total_booked_days: int, created_at) -> float:
    try:
        if created_at is None:
            total_days = 30
        else:
            if isinstance(created_at, datetime):
                listed_date = created_at.date()
            elif isinstance(created_at, date):
                listed_date = created_at
            else:
                listed_date = datetime.fromisoformat(str(created_at)).date()

            total_days = (date.today() - listed_date).days
        total_days = max(total_days, 30)
        occ = round((total_booked_days / total_days) * 100, 1)
        return min(100.0, occ)
    except Exception:
        return 0.0



def normalize(value: str) -> str:
    return (value or "").strip().lower().replace(" ", "").replace("_", "").replace("-", "")


def get_service_identifier(s) -> str:
    if isinstance(s, dict):
        return (
            s.get("id") or
            s.get("name") or
            s.get("title") or
            s.get("type") or
            s.get("label") or
            ""
        )
    return str(s)


def get_active_safety_keys(safety_data) -> list:
    if isinstance(safety_data, list):
        return [normalize(k) for k in safety_data]
    if isinstance(safety_data, dict):
        return [normalize(k) for k, v in safety_data.items() if v is True]
    return []


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_property(prop: PropertyCreate, db: AsyncSession = Depends(get_db)):
    try:
        if prop.image:
            prop.image = save_base64_image(prop.image)

        if prop.media:
            if "coverImage" in prop.media and prop.media["coverImage"]:
                prop.media["coverImage"] = save_base64_image(prop.media["coverImage"])
            if "houseImages" in prop.media and isinstance(prop.media["houseImages"], list):
                prop.media["houseImages"] = [save_base64_image(img) for img in prop.media["houseImages"]]

        if prop.rooms and isinstance(prop.rooms, list):
            for room in prop.rooms:
                if "images" in room and isinstance(room["images"], dict):
                    if "room" in room["images"] and room["images"]["room"]:
                        room["images"]["room"] = save_base64_image(room["images"]["room"])
                    if "bathroom" in room["images"] and room["images"]["bathroom"]:
                        room["images"]["bathroom"] = save_base64_image(room["images"]["bathroom"])
                    if "beds" in room and isinstance(room["beds"], list):
                        for bed in room["beds"]:
                            if "image" in bed and bed["image"]:
                                bed["image"] = save_base64_image(bed["image"])

        new_prop = Property(
            user_id=prop.user_id,
            name=prop.name,
            propertyType=prop.propertyType,
            structure=prop.structure,
            placeType=prop.placeType,
            status=prop.status,
            isActive=prop.isActive,
            price=prop.price,
            image=prop.image,
            guests=prop.guests,
            rooms=prop.rooms,
            amenities=prop.amenities,
            location=prop.location,
            media=prop.media,
            description_data=prop.description_data,
            pets_and_habits=prop.pets_and_habits,
            policies=prop.policies,
            pricing=prop.pricing,
            safety=prop.safety,
            services=prop.services,
            available_from=prop.available_from,
            available_to=prop.available_to,
            floors=prop.floors,
            gender=prop.gender or "Mixed"
        )
        db.add(new_prop)
        await db.flush()
        prop_id = new_prop.id
        await db.commit()
        return {"message": "Property created successfully", "property_id": prop_id}
    except Exception as e:
        import traceback
        traceback.print_exc()
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[dict])
async def get_all_properties(user_id: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    try:
        rating_stmt = select(
            Review.property_id,
            func.avg(Review.property_rating).label("avg_rating"),
            func.count(Review.id).label("review_count")
        ).where(Review.property_rating != None).group_by(Review.property_id).subquery()

        query = select(Property, rating_stmt.c.avg_rating, rating_stmt.c.review_count).outerjoin(
            rating_stmt, Property.id == rating_stmt.c.property_id
        ).options(selectinload(Property.owner)).order_by(Property.created_at.desc())

        if user_id:
            query = query.where(Property.user_id == user_id)

        db_result = await db.execute(query)
        rows = db_result.all()

        property_ids = [prop.id for prop, _, _ in rows]

        # ─── Confirmations ─────────────────────────────────────────────────────
        confirmations_result = await db.execute(
            select(BookingConfirmation).where(BookingConfirmation.property_id.in_(property_ids))
        )
        all_confirmations = confirmations_result.scalars().all()

        # ─── Booking Requests (approved + pending) ─────────────────────────────
        requests_result = await db.execute(
            select(BookingRequest).where(
                BookingRequest.property_id.in_(property_ids),
                BookingRequest.status.in_(["approved", "pending"])
            )
        )
        all_requests = requests_result.scalars().all()

        # ─── Dono merge karo ───────────────────────────────────────────────────
        bookings_map = {}
        for b in all_confirmations + all_requests:
            if b.property_id not in bookings_map:
                bookings_map[b.property_id] = []
            bookings_map[b.property_id].append(b)

        today_date = date.today()

        result = []
        for prop, avg_rating, review_count in rows:
            prop_bookings = bookings_map.get(prop.id, [])
            total_booked_days = 0
            is_live = False

            for b in prop_bookings:
                try:
                    # ─── FIXED DATE PARSING ONLY ───
                    if isinstance(b.check_in, datetime):
                        b_in = b.check_in.date()
                    else:
                        b_in = datetime.fromisoformat(str(b.check_in)).date()

                    if isinstance(b.check_out, datetime):
                        b_out = b.check_out.date()
                    else:
                        b_out = datetime.fromisoformat(str(b.check_out)).date()

                    days = (b_out - b_in).days
                    if days > 0:
                        total_booked_days += days

                    if b_in <= today_date < b_out:
                        is_live = True

                except:
                    continue
            avg_rating_f = float(avg_rating) if avg_rating else 0.0
            occ_rate = calculate_occupancy(total_booked_days, prop.created_at)
            p_score = round((avg_rating_f * 10) + (occ_rate / 2), 1)

            try:
                p_gender = getattr(prop, 'gender', 'Mixed') or 'Mixed'
            except:
                p_gender = 'Mixed'

            result.append({
                "id": prop.id,
                "user_id": prop.user_id,
                "name": prop.name,
                "propertyType": prop.propertyType,
                "structure": prop.structure,
                "placeType": prop.placeType,
                "status": prop.status,
                "isActive": prop.isActive,
                "price": prop.price,
                "image": prop.image,
                "guests": prop.guests,
                "rooms": prop.rooms,
                "amenities": prop.amenities,
                "location": prop.location,
                "media": prop.media,
                "description_data": prop.description_data,
                "pets_and_habits": prop.pets_and_habits,
                "policies": prop.policies,
                "pricing": prop.pricing,
                "safety": prop.safety,
                "services": prop.services,
                "available_from": prop.available_from,
                "available_to": prop.available_to,
                "floors": prop.floors,
                "gender": p_gender,
                "created_at": prop.created_at,
                "updated_at": prop.updated_at,
                "rating": round(avg_rating_f, 1),
                "occupancy_rate": occ_rate,
                "property_score": p_score,
                "review_count": review_count or 0,
                "is_live_occupied": is_live,
                "owner": {
                    "id": prop.owner.id,
                    "fullname": prop.owner.fullname,
                    "email": prop.owner.email,
                    "profile_picture": prop.owner.profile_picture,
                    "created_at": prop.owner.created_at
                } if prop.owner else None
            })
        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{property_id}", response_model=dict)
async def get_property(property_id: int, db: AsyncSession = Depends(get_db)):

    db_result = await db.execute(
        select(Property)
        .options(selectinload(Property.owner))
        .where(Property.id == property_id)
    )
    prop = db_result.scalar_one_or_none()

    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    # ─── Rating ─────────────────────────────
    rating_result = await db.execute(
        select(func.avg(Review.property_rating))
        .where(
            Review.property_id == property_id,
            Review.property_rating != None
        )
    )
    avg_rating = float(rating_result.scalar() or 0)

    # ─── Confirmations ──────────────────────
    confirmations_result = await db.execute(
        select(BookingConfirmation).where(
            BookingConfirmation.property_id == property_id
        )
    )
    confirmations = confirmations_result.scalars().all()

    # ─── Requests ───────────────────────────
    requests_result = await db.execute(
        select(BookingRequest).where(
            BookingRequest.property_id == property_id,
            BookingRequest.status.in_(["approved", "pending"])
        )
    )
    approved_requests = requests_result.scalars().all()

    # ─── Merge bookings ─────────────────────
    bookings = confirmations + approved_requests

    total_booked_days = 0
    is_live_occupied = False
    today = date.today()

    print("TOTAL BOOKINGS:", len(bookings))

    for b in bookings:
        try:
            start = b.check_in
            end = b.check_out

            # ---- SAFE PARSING ----
            if isinstance(start, datetime):
                start = start.date()
            elif isinstance(start, str):
                start = datetime.fromisoformat(start).date()

            if isinstance(end, datetime):
                end = end.date()
            elif isinstance(end, str):
                end = datetime.fromisoformat(end).date()

            if not start or not end:
                continue

            days = (end - start).days
            if days > 0:
                total_booked_days += days

            if start <= today < end:
                is_live_occupied = True

        except Exception as e:
            print("Booking parse error:", e)
            continue

    # ─── Occupancy ─────────────────────────
    occ_rate = calculate_occupancy(total_booked_days, prop.created_at)
    p_score = round((avg_rating * 10) + (occ_rate / 2), 1)

    # ─── Host stats ─────────────────────────
    host_id = prop.user_id

    host_ratings_res = await db.execute(
        select(func.avg(Review.property_rating), func.count(Review.id))
        .where(
            Review.property_id.in_(
                select(Property.id).where(Property.user_id == host_id)
            )
        )
    )
    host_stats = host_ratings_res.first()

    avg_host_rating = float(host_stats[0] or 0)
    host_review_count = host_stats[1] or 0

    host_booking_count = await db.execute(
        select(func.count(BookingConfirmation.id))
        .where(
            BookingConfirmation.property_id.in_(
                select(Property.id).where(Property.user_id == host_id)
            )
        )
    )
    host_booking_count = host_booking_count.scalar() or 0

    host_occupancy = min(100, (host_booking_count / 10) * 100)
    host_score = round((avg_host_rating * 10) + (host_occupancy / 2), 1)

    return {
        "id": prop.id,
        "user_id": prop.user_id,
        "name": prop.name,
        "propertyType": prop.propertyType,
        "structure": prop.structure,
        "placeType": prop.placeType,
        "status": prop.status,
        "isActive": prop.isActive,
        "price": prop.price,
        "image": prop.image,
        "guests": prop.guests,
        "rooms": prop.rooms,
        "amenities": prop.amenities,
        "location": prop.location,
        "media": prop.media,
        "description_data": prop.description_data,
        "pets_and_habits": prop.pets_and_habits,
        "policies": prop.policies,
        "pricing": prop.pricing,
        "safety": prop.safety,
        "services": prop.services,
        "available_from": prop.available_from,
        "available_to": prop.available_to,
        "gender": getattr(prop, "gender", "Mixed") or "Mixed",
        "floors": prop.floors,
        "created_at": prop.created_at,
        "updated_at": prop.updated_at,

        "rating": round(avg_rating, 1),
        "occupancy_rate": occ_rate,
        "property_score": p_score,
        "is_live_occupied": is_live_occupied,

        "owner": {
            "id": prop.owner.id,
            "fullname": prop.owner.fullname,
            "email": prop.owner.email,
            "profile_picture": prop.owner.profile_picture,
            "created_at": prop.owner.created_at,
            "stats": {
                "rating": round(avg_host_rating, 1),
                "occupancy": round(host_occupancy, 1),
                "score": host_score,
                "total_reviews": host_review_count
            }
        } if prop.owner else None
    }
    

@router.put("/{property_id}", response_model=dict)
async def update_property(property_id: int, prop_data: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    db_result = await db.execute(select(Property).options(selectinload(Property.owner)).where(Property.id == property_id))
    db_prop = db_result.scalar_one_or_none()
    if not db_prop:
        raise HTTPException(status_code=404, detail="Property not found")

    try:
        if "image" in prop_data and prop_data["image"] and prop_data["image"].startswith("data:image"):
            prop_data["image"] = save_base64_image(prop_data["image"])

        if "media" in prop_data and prop_data["media"]:
            media = prop_data["media"]
            if "coverImage" in media and media["coverImage"] and media["coverImage"].startswith("data:image"):
                media["coverImage"] = save_base64_image(media["coverImage"])
            if "houseImages" in media and isinstance(media["houseImages"], list):
                media["houseImages"] = [save_base64_image(img) for img in media["houseImages"]]
            prop_data["media"] = media

        if "rooms" in prop_data and isinstance(prop_data["rooms"], list):
            for room in prop_data["rooms"]:
                if "images" in room and isinstance(room["images"], dict):
                    if "room" in room["images"] and room["images"]["room"]:
                        room["images"]["room"] = save_base64_image(room["images"]["room"])
                    if "bathroom" in room["images"] and room["images"]["bathroom"]:
                        room["images"]["bathroom"] = save_base64_image(room["images"]["bathroom"])
                    if "beds" in room and isinstance(room["beds"], list):
                        for bed in room["beds"]:
                            if "image" in bed and bed["image"]:
                                bed["image"] = save_base64_image(bed["image"])

        readonly_fields = ["id", "created_at", "updated_at", "user_id", "owner"]

        for key, value in prop_data.items():
            if key not in readonly_fields and hasattr(db_prop, key):
                setattr(db_prop, key, value)

        await db.commit()
        return {"message": "Property updated successfully", "property_id": property_id}
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{property_id}", status_code=status.HTTP_200_OK)
async def delete_property(property_id: int, db: AsyncSession = Depends(get_db)):
    db_result = await db.execute(select(Property).where(Property.id == property_id))
    db_prop = db_result.scalar_one_or_none()
    if not db_prop:
        raise HTTPException(status_code=404, detail="Property not found")

    try:
        await db.delete(db_prop)
        await db.commit()
        return {"message": "Property deleted successfully"}
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=List[dict])
async def search_properties(filters: SearchFilters, db: AsyncSession = Depends(get_db)):
    try:
        rating_stmt = select(
            Review.property_id,
            func.avg(Review.property_rating).label("avg_rating"),
            func.count(Review.id).label("review_count")
        ).where(Review.property_rating != None).group_by(Review.property_id).subquery()

        query = select(Property, rating_stmt.c.avg_rating, rating_stmt.c.review_count).outerjoin(
            rating_stmt, Property.id == rating_stmt.c.property_id
        ).options(selectinload(Property.owner)).where(Property.isActive == True)

        if filters.minPrice is not None:
            query = query.where(Property.price >= filters.minPrice)
        if filters.maxPrice is not None:
            query = query.where(Property.price <= filters.maxPrice)

        if filters.propertyTypes and len(filters.propertyTypes) > 0:
            query = query.where(Property.propertyType.in_(filters.propertyTypes))

        if filters.roomTypes and len(filters.roomTypes) > 0:
            query = query.where(Property.placeType.in_(filters.roomTypes))

        if filters.gender:
            if filters.gender == "Mixed":
                query = query.where(or_(
                    Property.gender == "Mixed",
                    Property.gender == None,
                    Property.gender == ""
                ))
            else:
                query = query.where(Property.gender == filters.gender)

        if filters.location and filters.location.strip() != "":
            search_term = f"%{filters.location}%"
            query = query.where(or_(
    Property.name.ilike(search_term),

    cast(Property.location['city'], Text).ilike(search_term),
    cast(Property.location['country'], Text).ilike(search_term),
    cast(Property.location['state'], Text).ilike(search_term),
    cast(Property.location['area'], Text).ilike(search_term),
    cast(Property.location['address'], Text).ilike(search_term),

    # FULL LOCATION JSON SEARCH
    cast(Property.location, Text).ilike(search_term)
))

        db_result = await db.execute(query.order_by(Property.created_at.desc()))
        rows = db_result.all()

        property_ids = [prop.id for prop, _, _ in rows]
        bookings_result = await db.execute(
            select(BookingConfirmation).where(BookingConfirmation.property_id.in_(property_ids))
        )
        all_bookings = bookings_result.scalars().all()

        bookings_map = {}
        for b in all_bookings:
            if b.property_id not in bookings_map:
                bookings_map[b.property_id] = []
            bookings_map[b.property_id].append(b)

        today_date = date.today()

        result = []
        for prop, avg_rating, review_count in rows:
            avg_rating_f = float(avg_rating) if avg_rating else 0.0

            prop_bookings = bookings_map.get(prop.id, [])
            total_booked_days = 0
            is_live = False

            for b in prop_bookings:
                try:
                    b_in = datetime.strptime(b.check_in, '%Y-%m-%d').date() if isinstance(b.check_in, str) else b.check_in
                    b_out = datetime.strptime(b.check_out, '%Y-%m-%d').date() if isinstance(b.check_out, str) else b.check_out
                    days = (b_out - b_in).days
                    if days > 0:
                        total_booked_days += days
                    if b_in <= today_date < b_out:
                        is_live = True
                except:
                    continue
                
            occ_rate = calculate_occupancy(total_booked_days, prop.created_at)
            p_score = round((avg_rating_f * 10) + (occ_rate / 2), 1)

            # ─── Amenities filter ───────────────────────────────────────────────
            if filters.amenities and len(filters.amenities) > 0:
                prop_amenities = prop.amenities if isinstance(prop.amenities, list) else []
                prop_amenities_norm = [normalize(a) for a in prop_amenities]
                if not all(normalize(a) in prop_amenities_norm for a in filters.amenities):
                    continue

            # ─── Guests filter ──────────────────────────────────────────────────
            if filters.guests:
                prop_guests = prop.guests if isinstance(prop.guests, dict) else {}
                req_adults = filters.guests.get("adults", 0)
                req_children = filters.guests.get("children", 0)
                req_infants = filters.guests.get("infants", 0)
                has_breakdown = "adults" in prop_guests or "children" in prop_guests
                if has_breakdown:
                    if int(prop_guests.get("adults", 0)) < req_adults:
                        continue
                    if int(prop_guests.get("children", 0)) < req_children:
                        continue
                    if int(prop_guests.get("infants", 0)) < req_infants:
                        continue
                else:
                    total_capacity = int(prop_guests.get("total", prop_guests.get("maxGuests", 100)))
                    if total_capacity < (req_adults + req_children):
                        continue

            # ─── Pets filter ────────────────────────────────────────────────────
            pets_data = prop.pets_and_habits if isinstance(prop.pets_and_habits, dict) else {}
            if filters.petsAllowed:
                if not pets_data.get("petsAllowed", False):
                    continue

            # ─── Habits filter ──────────────────────────────────────────────────
            if filters.habitsAllowed:
                if not pets_data.get("habitsAllowed", False):
                    continue
                if filters.habits and len(filters.habits) > 0:
                    prop_habits_raw = pets_data.get("habits", [])
                    prop_habits_norm = [normalize(h) for h in prop_habits_raw]
                    if not all(normalize(h) in prop_habits_norm for h in filters.habits):
                        continue

            # ─── Highlights filter ──────────────────────────────────────────────
            if filters.highlights and len(filters.highlights) > 0:
                desc_data = prop.description_data if isinstance(prop.description_data, dict) else {}
                prop_highlights = desc_data.get("highlights", [])
                prop_highlights_norm = [normalize(h) for h in prop_highlights]
                if not all(normalize(h) in prop_highlights_norm for h in filters.highlights):
                    continue

            # ─── Cancellation policy filter ─────────────────────────────────────
            if filters.cancellationPolicies and len(filters.cancellationPolicies) > 0:
                policies_data = prop.policies if isinstance(prop.policies, dict) else {}
                prop_policy = normalize(policies_data.get("cancellation") or "")
                if not any(normalize(fp) == prop_policy for fp in filters.cancellationPolicies):
                    continue

            # ─── Safety filter ──────────────────────────────────────────────────
            if filters.safetyFeatures and len(filters.safetyFeatures) > 0:
                safety_data = prop.safety if prop.safety else {}
                active_safety_norm = get_active_safety_keys(safety_data)
                if not all(normalize(f) in active_safety_norm for f in filters.safetyFeatures):
                    continue

            # ─── Services filter ────────────────────────────────────────────────
            if filters.services and len(filters.services) > 0:
                prop_services_data = prop.services if isinstance(prop.services, list) else []
                prop_services_norm = [normalize(get_service_identifier(s)) for s in prop_services_data]
                if not all(normalize(s) in prop_services_norm for s in filters.services):
                    continue

            # ─── Bed types filter ───────────────────────────────────────────────
            if filters.bedTypes and len(filters.bedTypes) > 0:
                prop_rooms = prop.rooms if isinstance(prop.rooms, list) else []
                has_matching_bed = False
                for room in prop_rooms:
                    for bed_type in filters.bedTypes:
                        bed_key = normalize(bed_type)
                        # singleBeds / doubleBeds directly room mein count hote hain
                        for room_key, room_val in room.items():
                            if normalize(room_key) == bed_key:
                                if isinstance(room_val, (int, float)) and room_val > 0:
                                    has_matching_bed = True
                                    break
                        if has_matching_bed:
                            break
                    if has_matching_bed:
                        break
                if not has_matching_bed:
                    continue

            # ─── Rooms count filter ─────────────────────────────────────────────
            if filters.numRooms is not None and filters.numRooms > 0:
                prop_rooms = prop.rooms if isinstance(prop.rooms, list) else []
                if len(prop_rooms) < filters.numRooms:
                    continue

            # ─── Booking type filter ────────────────────────────────────────────
            if filters.bookingType:
                policies_data = prop.policies if isinstance(prop.policies, dict) else {}
                prop_booking_type_norm = normalize(policies_data.get("bookingType") or "")
                filter_booking_type_norm = normalize(filters.bookingType)
                if prop_booking_type_norm != filter_booking_type_norm:
                    continue

            # ─── Date filter ────────────────────────────────────────────────────
            if filters.checkIn and filters.checkOut:
                try:
                    req_in = datetime.strptime(filters.checkIn, '%Y-%m-%d').date()
                    req_out = datetime.strptime(filters.checkOut, '%Y-%m-%d').date()
                    conflict = False
                    for b in prop_bookings:
                        try:
                            b_in_str = b.check_in
                            b_out_str = b.check_out
                            if isinstance(b_in_str, str):
                                b_in = datetime.strptime(b_in_str, '%Y-%m-%d').date()
                            else:
                                b_in = b_in_str
                            if isinstance(b_out_str, str):
                                b_out = datetime.strptime(b_out_str, '%Y-%m-%d').date()
                            else:
                                b_out = b_out_str
                            if req_in < b_out and req_out > b_in:
                                conflict = True
                                break
                        except:
                            continue
                    if conflict:
                        continue
                except:
                    pass

            result.append({
                "id": prop.id,
                "user_id": prop.user_id,
                "name": prop.name,
                "propertyType": prop.propertyType,
                "structure": prop.structure,
                "placeType": prop.placeType,
                "status": prop.status,
                "isActive": prop.isActive,
                "price": prop.price,
                "image": prop.image,
                "guests": prop.guests,
                "rooms": prop.rooms,
                "amenities": prop.amenities,
                "location": prop.location,
                "media": prop.media,
                "description_data": prop.description_data,
                "pets_and_habits": prop.pets_and_habits,
                "policies": prop.policies,
                "pricing": prop.pricing,
                "safety": prop.safety,
                "services": prop.services,
                "available_from": prop.available_from,
                "available_to": prop.available_to,
                "gender": getattr(prop, 'gender', 'Mixed') or 'Mixed',
                "created_at": prop.created_at,
                "updated_at": prop.updated_at,
                "rating": round(avg_rating_f, 1),
                "occupancy_rate": occ_rate,
                "property_score": p_score,
                "review_count": review_count or 0,
                "is_live_occupied": is_live,
                "owner": {
                    "id": prop.owner.id,
                    "fullname": prop.owner.fullname,
                    "email": prop.owner.email,
                    "profile_picture": prop.owner.profile_picture,
                    "created_at": prop.owner.created_at
                } if prop.owner else None
            })
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


class SearchNearbyRequest(BaseModel):
    lat: float
    lng: float
    radius_km: Optional[float] = 50.0
    gender: Optional[str] = None

@router.post("/search/nearby", response_model=List[dict])
async def search_nearby_properties(req: SearchNearbyRequest, db: AsyncSession = Depends(get_db)):
    try:
        rating_stmt = select(
            Review.property_id,
            func.avg(Review.property_rating).label("avg_rating"),
            func.count(Review.id).label("review_count")
        ).where(Review.property_rating != None).group_by(Review.property_id).subquery()

        query = select(Property, rating_stmt.c.avg_rating, rating_stmt.c.review_count).outerjoin(
            rating_stmt, Property.id == rating_stmt.c.property_id
        ).options(selectinload(Property.owner)).where(Property.isActive == True)

        db_result = await db.execute(query)
        rows = db_result.all()

        import math
        def calculate_distance(lat1, lon1, lat2, lon2):
            R = 6371
            d_lat = math.radians(lat2 - lat1)
            d_lon = math.radians(lon2 - lon1)
            a = math.sin(d_lat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            return R * c

        result = []
        for prop, avg_rating, review_count in rows:
            prop_loc = prop.location if isinstance(prop.location, dict) else {}
            p_lat = prop_loc.get("latitude")
            p_lng = prop_loc.get("longitude")

            if p_lat is None or p_lng is None:
                map_pin = prop_loc.get("mapPin")
                if map_pin and "," in map_pin:
                    try:
                        p_lat, p_lng = map(float, map_pin.split(","))
                    except:
                        continue

            if p_lat is not None and p_lng is not None:
                dist = calculate_distance(req.lat, req.lng, float(p_lat), float(p_lng))
                if dist <= req.radius_km:
                    try:
                        prop_gender = getattr(prop, "gender", "Mixed") or "Mixed"
                        if req.gender and prop_gender != req.gender:
                            continue
                    except:
                        pass

                    avg_rating_f = float(avg_rating) if avg_rating else 0.0

                    result.append({
                        "id": prop.id,
                        "name": prop.name,
                        "propertyType": prop.propertyType,
                        "price": prop.price,
                        "image": prop.image,
                        "location": prop.location,
                        "pricing": prop.pricing,
                        "distance_km": round(dist, 2),
                        "isActive": prop.isActive,
                        "gender": getattr(prop, 'gender', 'Mixed') or 'Mixed',
                        "rating": round(avg_rating_f, 1),
                        "review_count": review_count or 0,
                        "owner": {
                            "id": prop.owner.id,
                            "fullname": prop.owner.fullname,
                            "profile_picture": prop.owner.profile_picture
                        } if prop.owner else None
                    })

        result.sort(key=lambda x: x["distance_km"])
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))