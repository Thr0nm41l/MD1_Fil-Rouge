from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class HistoryBucket(BaseModel):
    bucket: datetime
    avg_fill_rate: float
    min_fill_rate: Optional[float] = None
    max_fill_rate: Optional[float] = None
    measurement_count: int


class HeatmapPoint(BaseModel):
    day_of_week: int
    hour_of_day: int
    count: int
