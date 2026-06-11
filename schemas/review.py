from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class ReviewBase(BaseModel):
    booking_id: int
    property_rating: Optional[int] = None
    property_review: Optional[str] = None
    host_rating: Optional[int] = None
    host_review: Optional[str] = None
    guest_rating: Optional[int] = None
    guest_review: Optional[str] = None

class ReviewCreateGuest(BaseModel):
    booking_id: int
    property_rating: int
    property_review: str
    host_rating: int
    host_review: str

class ReviewCreateHost(BaseModel):
    booking_id: int
    guest_rating: int
    guest_review: str

class ReviewResponse(ReviewBase):
    id: int
    guest_id: int
    property_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class PropertyAverageRating(BaseModel):
    average_property_rating: float
    total_reviews: int
