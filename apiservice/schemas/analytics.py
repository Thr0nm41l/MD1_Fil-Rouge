from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class KpiValue(BaseModel):
    value: float
    variation_pct: float


class KpisResponse(BaseModel):
    volume_collected_l: KpiValue
    collection_count: KpiValue
    avg_fill_rate_pct: KpiValue
    overflow_count: KpiValue
    total_distance_km: KpiValue
    active_containers: KpiValue


class TypeDistributionItem(BaseModel):
    type: str
    count: int
    pct: float


class ZoneCollectionItem(BaseModel):
    zone_id: int
    zone_name: Optional[str] = None
    collection_count: int
    volume_l: float


class FillBucket(BaseModel):
    bucket_min: int
    bucket_max: int
    count: int


class FillEvolutionPoint(BaseModel):
    date: date
    avg_fill_rate: float
    moving_avg_7d: Optional[float] = None


class RoutePerformancePoint(BaseModel):
    route_id: int
    distance_km: float
    volume_collected_l: float
    container_count: int


class IncidentEvent(BaseModel):
    timestamp: datetime
    type: str
    zone_id: Optional[int] = None
    container_id: Optional[int] = None
    description: Optional[str] = None
    content: Optional[str] = None


class ChoroplethZone(BaseModel):
    zone_id: int
    zone_name: Optional[str] = None
    polygon: Optional[Dict[str, Any]] = None
    density_km2: float
    avg_fill_rate: float


class CostsRoiPoint(BaseModel):
    month: str
    total_cost: float
    estimated_savings: float
    co2_saved_kg: float
