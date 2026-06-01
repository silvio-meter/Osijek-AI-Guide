"""
PointOfInterest model for locations shown on the map.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, JSON
from sqlalchemy.sql import func
from database import Base


class PointOfInterest(Base):
    __tablename__ = "points_of_interest"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    slug = Column(String(150), unique=True, index=True, nullable=False)

    category = Column(String(50), nullable=False, index=True)
    subcategory = Column(String(80), nullable=True)

    description = Column(Text, nullable=True)
    short_description = Column(String(250), nullable=True)

    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)

    address = Column(String(200), nullable=True)
    website = Column(String(250), nullable=True)
    phone = Column(String(50), nullable=True)

    opening_hours = Column(String(300), nullable=True)
    price_level = Column(Integer, nullable=True)  # 1-4 scale
    price_info = Column(String(150), nullable=True)

    tags = Column(JSON, nullable=True)  # List of strings, e.g. ["tvrda", "besplatno"]

    rating = Column(Float, nullable=True)
    review_count = Column(Integer, default=0)

    is_featured = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<PointOfInterest(id={self.id}, name={self.name}, category={self.category})>"
