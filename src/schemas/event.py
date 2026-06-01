"""
Pydantic schemas for Events (curated + scraped).
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any
from datetime import datetime


class EventBase(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=300)

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    date_text: Optional[str] = Field(None, max_length=150)

    location: Optional[str] = Field(None, max_length=150)
    address: Optional[str] = Field(None, max_length=200)
    lat: Optional[float] = None
    lng: Optional[float] = None

    category: Optional[str] = Field(None, max_length=50)
    tags: Optional[List[str]] = None

    url: Optional[str] = Field(None, max_length=300)
    source: str = Field(..., max_length=50)           # "curated", "osijek031", "sib", etc.
    source_id: Optional[str] = Field(None, max_length=100)

    has_reliable_date: bool = False
    is_curated: bool = False
    is_active: bool = True


class EventCreate(EventBase):
    """Used when manually creating curated events."""
    pass


class EventRead(EventBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class EventList(BaseModel):
    items: List[EventRead]
    total: int
    limit: int
    offset: int
