"""
Router for Events (hybrid curated + scraped).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from core.exceptions import NotFoundException

from database import get_db
from models.event import Event
from schemas.event import (
    EventCreate,
    EventRead,
    EventList,
)
from dependencies.auth import get_current_active_user
from models.user import User

router = APIRouter(
    prefix="",
    tags=["Admin - Curated Events (protected)"]
)


@router.get("/", response_model=EventList)
def list_events(
    category: Optional[str] = None,
    is_curated: Optional[bool] = None,
    has_reliable_date: Optional[bool] = None,
    search: Optional[str] = None,
    include_inactive: bool = Query(False, description="Admin only: include soft-deleted events"),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List events (protected admin endpoint). Supports filtering and optional inclusion of inactive records."""
    query = db.query(Event)

    if not include_inactive:
        query = query.filter(Event.is_active == True)

    if category:
        query = query.filter(Event.category.ilike(f"%{category}%"))

    if is_curated is not None:
        query = query.filter(Event.is_curated == is_curated)

    if has_reliable_date is not None:
        query = query.filter(Event.has_reliable_date == has_reliable_date)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Event.title.ilike(search_term)) |
            (Event.short_description.ilike(search_term))
        )

    total = query.count()
    items = query.offset(offset).limit(limit).all()

    return EventList(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{event_id}", response_model=EventRead)
def get_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a single event (admin)."""
    event = db.query(Event).filter(Event.id == event_id).first()

    if not event:
        raise NotFoundException(message="Događaj nije pronađen.")

    return event


@router.post("/", response_model=EventRead, status_code=201)
def create_event(
    event_in: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a curated event manually.
    Requires authentication.
    """
    data = event_in.model_dump()
    # Force correct flags for curated events created via admin
    data["source"] = data.get("source") or "curated"
    data["is_curated"] = True
    data["is_active"] = data.get("is_active", True)

    event = Event(**data)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.put("/{event_id}", response_model=EventRead)
def update_event(
    event_id: int,
    event_in: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update an existing event (full update). Protected."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise NotFoundException(message="Događaj nije pronađen.")

    for key, value in event_in.model_dump().items():
        setattr(event, key, value)

    # Ensure curated flag stays sane
    event.is_curated = True
    if not event.source:
        event.source = "curated"

    db.commit()
    db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=204)
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Soft delete a curated event (sets is_active=False).
    The record stays in the database for history/audit.
    Requires authentication.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise NotFoundException(message="Događaj nije pronađen.")

    event.is_active = False
    db.commit()
    # 204 No Content
