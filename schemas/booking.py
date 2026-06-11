from pydantic import BaseModel, ConfigDict
from typing import Optional, Any

class BookingBase(BaseModel):
    property_id: int
    guest_id: int
    check_in: str
    check_out: str
    guests_details: Any
    total_price: float
    tokens_used: Optional[int] = 0

class BookingCreate(BookingBase):
    pass

class BookingRequestResponse(BookingBase):
    id: int
    status: str
    model_config = ConfigDict(from_attributes=True)

class BookingConfirmationResponse(BookingBase):
    id: int
    request_id: Optional[int] = None
    booking_type: str
    status: str
    model_config = ConfigDict(from_attributes=True)