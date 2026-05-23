from typing import Optional

from pydantic import BaseModel


class ZoneCreate(BaseModel):
    name: Optional[str] = None
    postal_code: Optional[int] = None
    polygon: dict  # GeoJSON Polygon geometry object


class ZoneUpdate(BaseModel):
    name: Optional[str] = None
    postal_code: Optional[int] = None
    polygon: Optional[dict] = None  # GeoJSON Polygon geometry object


class ZoneOut(BaseModel):
    key_zone: int
    name: Optional[str] = None
    postal_code: Optional[int] = None
    polygon: Optional[dict] = None  # GeoJSON geometry


class ZoneStats(BaseModel):
    zone_id: int
    zone_name: Optional[str] = None
    container_count: int
    avg_fill_rate: float
    overflow_count_30d: int


class ZoneDensity(BaseModel):
    zone_id: int
    zone_name: Optional[str] = None
    density_km2: float
