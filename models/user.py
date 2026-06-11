from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    fullname = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phonenumber = Column(String(20))
    password_hash = Column(Text, nullable=False)
    role = Column(String(50), default="guest")
    profile_picture = Column(Text)
    verification_status = Column(String(50), default="pending")

    gender = Column(String(50))
    tokens = Column(Integer, default=0)  
    full_address = Column(Text)
    bio = Column(Text)
    habbits = Column(JSON)

    live_image_url = Column(Text)
    cnic_front_url = Column(Text)
    cnic_back_url = Column(Text)
    passport_url = Column(Text)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    notifications = relationship("Notification", primaryjoin="User.id==Notification.user_id", back_populates="user", cascade="all, delete-orphan")

    family_members = relationship("FamilyMember", back_populates="user", cascade="all, delete-orphan" )
    properties = relationship("Property", back_populates="owner", cascade="all, delete-orphan")
    booking_requests = relationship("BookingRequest", back_populates="guest", cascade="all, delete-orphan")
    booking_confirmations = relationship("BookingConfirmation", back_populates="guest", cascade="all, delete-orphan")