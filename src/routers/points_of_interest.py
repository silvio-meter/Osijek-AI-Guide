"""
Router for Points of Interest (POI).

Current endpoints (as of end of Week 3 work):

GET    /points_of_interest/                 → List with rich filtering + proximity search + smart sorting
GET    /points_of_interest/{id}             → Get single POI
POST   /points_of_interest/                 → Create new POI (requires auth)
PUT    /points_of_interest/{id}             → Update existing POI (requires auth)

Supported query parameters on list:
- category, tags, is_featured, min_rating, search
- lat + lng (+ optional radius) → proximity search
- has_website, price_level
- sort (featured | rating | distance | name)
  → When lat+lng provided, defaults to "distance" unless overridden

Note: Distance is calculated in Python (fine for current dataset size).
"""

import math
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models.point_of_interest import PointOfInterest
from schemas.poi import (
    PointOfInterestCreate,
    PointOfInterestRead,
    PointOfInterestList,
)
from dependencies.auth import get_current_active_user
from models.user import User

router = APIRouter(
    prefix="/points_of_interest",
    tags=["Public Data"]
)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth in kilometers.
    """
    R = 6371.0  # Earth radius in km

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


@router.get("/", response_model=PointOfInterestList)
def list_points_of_interest(
    category: Optional[str] = None,
    tags: Optional[str] = Query(None, description="Comma-separated tags, e.g. tvrda,romantika"),
    is_featured: Optional[bool] = None,
    min_rating: Optional[float] = Query(None, ge=0, le=5, description="Minimum rating (0-5)"),
    search: Optional[str] = Query(None, description="Search in name and short description"),
    lat: Optional[float] = Query(None, description="Latitude for proximity search"),
    lng: Optional[float] = Query(None, description="Longitude for proximity search"),
    radius: Optional[float] = Query(None, description="Radius in km for proximity search"),
    has_website: Optional[bool] = Query(None, description="Filter locations that have a website"),
    price_level: Optional[int] = Query(None, ge=1, le=4, description="Exact price level (1-4)"),
    sort: str = Query(
        "featured",
        description="Sort order: featured (default), rating, distance, name. "
                    "When lat+lng are provided without an explicit sort, it automatically defaults to sorting by distance."
    ),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Returns a list of points of interest with advanced filtering, proximity search and smart sorting.

    Proximity behavior:
    - If `lat` and `lng` are provided, distance is calculated for each result.
    - If `radius` is also provided, only results within that radius (in km) are returned.
    - When doing a proximity search, the default sort becomes "distance" (closest first),
      unless the client explicitly requests another sort order (e.g. sort=rating).

    This makes the endpoint very useful for "near me" map experiences.
    """
    query = db.query(PointOfInterest).filter(PointOfInterest.is_active == True)

    # Category filter
    if category:
        query = query.filter(PointOfInterest.category.ilike(category))

    # Tags filter (multiple tags supported)
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        for tag in tag_list:
            query = query.filter(PointOfInterest.tags.contains(tag))

    if is_featured is not None:
        query = query.filter(PointOfInterest.is_featured == is_featured)

    if min_rating is not None:
        query = query.filter(PointOfInterest.rating >= min_rating)

    if has_website is not None:
        if has_website:
            query = query.filter(PointOfInterest.website.isnot(None))
        else:
            query = query.filter(PointOfInterest.website.is_(None))

    if price_level is not None:
        query = query.filter(PointOfInterest.price_level == price_level)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (PointOfInterest.name.ilike(search_term)) |
            (PointOfInterest.short_description.ilike(search_term))
        )

    # Fetch items (we need to calculate distance in Python for now)
    items = query.all()

    # Proximity filtering + distance calculation
    if lat is not None and lng is not None:
        items_with_distance = []
        for item in items:
            distance = haversine_distance(lat, lng, item.lat, item.lng)
            if radius is None or distance <= radius:
                # Attach distance dynamically
                item.distance = round(distance, 2)
                items_with_distance.append(item)
        items = items_with_distance
    else:
        # No proximity search → ensure distance is None
        for item in items:
            item.distance = None

    # Determine effective sort order
    effective_sort = sort

    # Smart default: if user is doing proximity search (lat/lng provided)
    # and didn't explicitly choose another sort, default to sorting by distance.
    if effective_sort == "featured" and lat is not None and lng is not None:
        effective_sort = "distance"

    # Apply sorting
    if effective_sort == "distance" and lat is not None and lng is not None:
        items.sort(key=lambda x: x.distance if x.distance is not None else float('inf'))
    elif effective_sort == "rating":
        items.sort(key=lambda x: (x.rating or 0), reverse=True)
    elif effective_sort == "featured":
        items.sort(key=lambda x: (not x.is_featured, -(x.rating or 0)))
    elif effective_sort == "name":
        items.sort(key=lambda x: x.name.lower())
    else:
        # Fallback: featured first, then rating
        items.sort(key=lambda x: (not x.is_featured, -(x.rating or 0)))

    total = len(items)

    # Apply pagination after sorting/filtering
    paginated_items = items[offset : offset + limit]

    return PointOfInterestList(
        items=paginated_items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{poi_id}", response_model=PointOfInterestRead)
def get_point_of_interest(poi_id: int, db: Session = Depends(get_db)):
    """Returns a single point of interest by ID."""
    poi = db.query(PointOfInterest).filter(
        PointOfInterest.id == poi_id,
        PointOfInterest.is_active == True
    ).first()

    if not poi:
        raise HTTPException(status_code=404, detail="Point of interest not found")

    return poi


@router.post("/", response_model=PointOfInterestRead, status_code=201)
def create_point_of_interest(
    poi_in: PointOfInterestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new Point of Interest.
    Requires authentication (for now any logged-in user can create).
    """
    # Basic slug uniqueness check
    existing = db.query(PointOfInterest).filter(PointOfInterest.slug == poi_in.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Slug already exists")

    poi = PointOfInterest(**poi_in.model_dump())
    db.add(poi)
    db.commit()
    db.refresh(poi)
    return poi


@router.put("/{poi_id}", response_model=PointOfInterestRead)
def update_point_of_interest(
    poi_id: int,
    poi_in: PointOfInterestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update an existing Point of Interest."""
    poi = db.query(PointOfInterest).filter(PointOfInterest.id == poi_id).first()
    if not poi:
        raise HTTPException(status_code=404, detail="Point of interest not found")

    # Check for slug conflict (if slug is being changed)
    if poi_in.slug != poi.slug:
        slug_exists = db.query(PointOfInterest).filter(
            PointOfInterest.slug == poi_in.slug,
            PointOfInterest.id != poi_id
        ).first()
        if slug_exists:
            raise HTTPException(status_code=400, detail="Slug already in use")

    for key, value in poi_in.model_dump().items():
        setattr(poi, key, value)

    db.commit()
    db.refresh(poi)
    return poi


@router.delete("/{poi_id}", status_code=204)
def delete_point_of_interest(
    poi_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Soft delete a Point of Interest (sets is_active=False).
    The record is not removed from the database.
    """
    poi = db.query(PointOfInterest).filter(PointOfInterest.id == poi_id).first()
    if not poi:
        raise HTTPException(status_code=404, detail="Point of interest not found")

    poi.is_active = False
    db.commit()

    return  # 204 No Content
