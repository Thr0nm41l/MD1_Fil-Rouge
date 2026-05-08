from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ContainerCreate(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    type_id: Optional[int] = None
    capacity_liters: float = Field(1000.0, gt=0)
    fill_threshold_pct: float = Field(70.0, ge=0, le=100)


class ContainerUpdate(BaseModel):
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lng: Optional[float] = Field(None, ge=-180, le=180)
    type_id: Optional[int] = None
    capacity_liters: Optional[float] = Field(None, gt=0)
    fill_threshold_pct: Optional[float] = Field(None, ge=0, le=100)


class ContainerOut(BaseModel):
    key_container: int
    lat: Optional[float] = None
    lng: Optional[float] = None
    type_id: Optional[int] = None
    zone_id: Optional[int] = None
    capacity_liters: float
    fill_rate: float
    status: str
    fill_threshold_pct: float
    last_updated: datetime
    is_active: bool


class MeasureCreate(BaseModel):
    fill_rate: float = Field(..., ge=0, le=100)
    temperature: Optional[float] = None
    battery_pct: Optional[float] = Field(None, ge=0, le=100)
    measured_at: Optional[datetime] = None
    device_id: Optional[int] = None


class MeasureOut(BaseModel):
    key_history: int
    container_id: int
    fill_rate: float
    temperature: Optional[float] = None
    battery_pct: Optional[float] = None
    is_outlier: bool
    measured_at: datetime
