# Points of Interest (POI) – Initial Notes (Preparation for Week 3)

This document is a starting point for **Tjedan 3** work on Points of Interest.

## Goal

Create a rich, useful set of locations that can power the map in the mobile application.

## Planned Model (initial draft)

```python
class PointOfInterest(Base):
    id: int
    name: str
    category: str          # e.g. "Povijest", "Gastro", "Priroda", "Kultura", "Sport"
    description: str
    lat: float
    lng: float
    address: Optional[str]
    website: Optional[str]
    phone: Optional[str]
    opening_hours: Optional[str]
    price_info: Optional[str]
    tags: list[str]        # ["tvrda", "romantika", "besplatno", "dobra_vista"]
    rating: Optional[float]
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime]
```

## Categories (proposed)

- Povijest (Tvrđa, Katedrala, Muzej Slavonije...)
- Priroda (Kopački rit, Drava, parkovi)
- Gastro (restorani koje vrijedi istaknuti, ne svi)
- Kultura (kazalište, galerije, muzeji)
- Šetnja / Romantika (Europska avenija, Zimska luka...)
- Sport & Rekreacija
- Praktično (banke, pošte, hitna pomoć, parking)

## Data Sources (to be decided in Week 3)

- Manual curation (highest quality)
- Existing PDFs in `data/`
- Public open data if available
- Community / admin input later

## API Ideas (for later)

- `GET /points_of_interest`
- `GET /points_of_interest?category=Priroda`
- `GET /points_of_interest?near=lat,lng&radius=km`
- Filtering by tags

## Next Steps (Week 3)

- Decide on final data model
- Seed 30–50 high-quality locations manually
- Implement basic CRUD + listing endpoints
- Add simple admin-friendly way to maintain data

---

*This is a living document. Will be expanded during Week 3.*
