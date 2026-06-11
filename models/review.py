from sqlalchemy import Column, Integer, String, Text, Float, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.database import Base

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("booking_confirmations.id", ondelete="CASCADE"), nullable=False, unique=True)
    guest_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)
    
    # Guest's review of property and host
    property_rating = Column(Integer, nullable=True) # 1 to 5
    property_review = Column(Text, nullable=True)
    host_rating = Column(Integer, nullable=True) # 1 to 5
    host_review = Column(Text, nullable=True)
    
    # Host's review of guest
    guest_rating = Column(Integer, nullable=True) # 1 to 5
    guest_review = Column(Text, nullable=True)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    booking = relationship("BookingConfirmation")
    guest = relationship("User", foreign_keys=[guest_id])
    property = relationship("Property")
