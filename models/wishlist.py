from sqlalchemy import Column, BigInteger, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.database import Base

class Wishlist(Base):
    __tablename__ = "wishlist"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    property_id = Column(BigInteger, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", backref="wishlist_items")
    property = relationship("Property", backref="wishlisted_by")