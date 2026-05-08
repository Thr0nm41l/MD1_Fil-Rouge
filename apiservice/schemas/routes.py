from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


class RouteOut(BaseModel):
    key_route: int
    zone_id: Optional[int] = None
    team_id: Optional[int] = None
    name: Optional[str] = None
    status: str
    scheduled_at: Optional[date] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    distance_m: Optional[float] = None


class RouteStep(BaseModel):
    key_step: int
    container_id: int
    step_order: int
    collected: bool
    collected_at: Optional[datetime] = None
    volume_collected_l: Optional[float] = None


class RouteDetail(RouteOut):
    path: Optional[dict] = None  # GeoJSON LineString
    steps: List[RouteStep] = []


class RouteStats(BaseModel):
    total_routes: int
    total_distance_km: float
    total_collections: int
    avg_containers_per_route: float
    overflows_avoided: int
