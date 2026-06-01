"""
Event models for curated and scraped events.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, Float
from sqlalchemy.sql import func
from database import Base


class Event(Base):
    """
    Unified event model.
    Can represent both curated (manually added) and scraped events.
    """
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)

    # Core info
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    short_description = Column(String(300), nullable=True)

    # Dates
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    date_text = Column(String(150), nullable=True)   # Original text like "15. lipnja" or "kraj lipnja"

    # Location
    location = Column(String(150), nullable=True)
    address = Column(String(200), nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)

    # Categorization
    category = Column(String(50), nullable=True, index=True)   # koncert, izložba, sport, gastro, kazalište, festival...
    tags = Column(JSON, nullable=True)                         # ["besplatno", "obitelj", "tvrda"]

    # Links & source
    url = Column(String(300), nullable=True)
    source = Column(String(50), nullable=False, index=True)    # "curated", "osijek031", "sib", "osijeknews", "tavily"
    source_id = Column(String(100), nullable=True)             # original ID or URL hash for dedup

    # Quality flags
    has_reliable_date = Column(Boolean, default=False)
    is_curated = Column(Boolean, default=False)                # True only for manually maintained events
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Event(id={self.id}, title={self.title[:40]}, source={self.source})>"
