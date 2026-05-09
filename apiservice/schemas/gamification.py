from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    name: Optional[str] = None
    first_name: Optional[str] = None
    total_points: int


class EarnedBadge(BaseModel):
    badge_id: int
    name: str
    category: str
    earned_at: datetime


class NextBadge(BaseModel):
    badge_id: int
    name: str
    category: str
    target: int
    current_progress: int


class UserBadgesResponse(BaseModel):
    earned: List[EarnedBadge]
    next: List[NextBadge]


class UserImpact(BaseModel):
    user_id: int
    total_points: int
    signalement_count: int
    collection_count: int
    co2_saved_kg: float
    since: Optional[datetime] = None


class DefiOut(BaseModel):
    key_defi: int
    title: str
    type: str
    target_value: int
    reward_points: int
    ends_at: Optional[datetime] = None
    participant_count: int
    collective_progress: int
    progress_pct: float
