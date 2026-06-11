from sqlalchemy import Column, Integer, String, Text, Boolean, Float, JSON, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy import Column, Date
from sqlalchemy.orm import relationship
from core.database import Base

class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False) # Owner of the property
    

    name = Column(String(255), nullable=False)
    propertyType = Column(String(100), nullable=False)
    structure = Column(String(100))
    placeType = Column(String(100))
    
   
    status = Column(String(50), default="active")
    isActive = Column(Boolean, default=True)
    
   
    price = Column(Float, nullable=False)
    image = Column(Text)
    

    guests = Column(JSON, nullable=False)
    rooms = Column(JSON, nullable=False)
    amenities = Column(JSON, nullable=False)
    location = Column(JSON, nullable=False)
    media = Column(JSON, nullable=False)
    description_data = Column(JSON) 
    pets_and_habits = Column(JSON)
    policies = Column(JSON)
    pricing = Column(JSON, nullable=False)
    safety = Column(JSON)
    services = Column(JSON)
    

    available_from = Column(Date, nullable=True)
    available_to = Column(Date, nullable=True)


    floors = Column(Integer, default=0)
    gender = Column(String(50), default="Mixed")


    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


    owner = relationship("User", back_populates="properties")
    booking_requests = relationship("BookingRequest", back_populates="property")
    booking_confirmations = relationship("BookingConfirmation", back_populates="property")
