from pydantic import BaseModel
from datetime import datetime
from typing import Optional
# from .property import PropertyOut # Assuming PropertyOut exists or I'll create/check it

class WishlistItem(BaseModel):
    id: int
    user_id: int
    property_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class WishlistToggle(BaseModel):
    property_id: int