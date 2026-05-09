from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    report_type: str = Field(..., pattern="^(monthly|weekly|custom|zone|route)$")
    format: str = Field("pdf", pattern="^(pdf|excel)$")
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    zone_id: Optional[int] = None
    user_id: Optional[int] = None
