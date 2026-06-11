from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from core.database import Base

class FamilyMember(Base):
    __tablename__ = "family_member"

    id = Column(Integer, primary_key=True, index=True)
    fullname = Column(String(255), nullable=False)
    profile_picture = Column(Text)
    relation = Column(String(255))
    age = Column(Integer)
    gender = Column(String(10))
    email = Column(String(100))
    phonenumber = Column(String(255), nullable=True)
    bio = Column(Text)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))

    user = relationship("User", back_populates="family_members")