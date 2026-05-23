from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel


class DashboardConfig(BaseModel):
    user_id: int
    layout_config: Dict[str, Any]
    updated_at: datetime


class DashboardConfigUpdate(BaseModel):
    layout_config: Dict[str, Any]
