"""
Pydantic schemas for Points of Interest.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any
from datetime import datetime


class PointOfInterestBase(BaseModel):
    name: str = Field(..., max_length=150)
    slug: str = Field(..., max_length=150)
    category: str = Field(..., max_length=50)
    subcategory: Optional[str] = Field(None, max_length=80)

    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=250)

    lat: float
    lng: float

    address: Optional[str] = Field(None, max_length=200)
    website: Optional[str] = Field(None, max_length=250)
    phone: Optional[str] = Field(None, max_length=50)

    opening_hours: Optional[str] = Field(None, max_length=300)
    price_level: Optional[int] = Field(None, ge=1, le=4)
    price_info: Optional[str] = Field(None, max_length=150)

    tags: Optional[List[str]] = None

    rating: Optional[float] = Field(None, ge=0, le=5)
    review_count: int = 0

    is_featured: bool = False
    is_active: bool = True


class PointOfInterestCreate(PointOfInterestBase):
    """Schema used when creating a new POI (e.g. via admin or seeding script)."""
    pass


class PointOfInterestRead(PointOfInterestBase):
    """Schema returned to clients."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Populated dynamically when proximity search is used
    distance: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class PointOfInterestList(BaseModel):
    """Response for listing POIs."""
    items: List[PointOfInterestRead]
    total: int
    limit: int
    offset: int
