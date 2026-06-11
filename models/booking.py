from sqlalchemy import Column, Integer, String, Text, Float, JSON, TIMESTAMP, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.database import Base

class BookingRequest(Base):
    __tablename__ = "booking_requests"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)
    guest_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    check_in = Column(String(50), nullable=False)
    check_out = Column(String(50), nullable=False)
    guests_details = Column(JSON, nullable=False) 
    total_price = Column(Float, nullable=False)
    tokens_used = Column(Integer, default=0)  
    
    status = Column(String(50), default="pending") 
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    property = relationship("Property", back_populates="booking_requests")
    guest = relationship("User", back_populates="booking_requests")

class BookingConfirmation(Base):
    __tablename__ = "booking_confirmations"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("booking_requests.id", ondelete="SET NULL"), nullable=True) 
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)
    guest_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    check_in = Column(String(50), nullable=False)
    check_out = Column(String(50), nullable=False)
    guests_details = Column(JSON, nullable=False)
    total_price = Column(Float, nullable=False)
    tokens_used = Column(Integer, default=0)  
    
    booking_type = Column(String(50), nullable=False)
    
    status = Column(String(50), default="confirmed") 
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    property = relationship("Property", back_populates="booking_confirmations")
    guest = relationship("User", back_populates="booking_confirmations")
    booking_request = relationship("BookingRequest")
