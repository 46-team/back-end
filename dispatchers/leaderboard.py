from dataclasses import dataclass
from uuid import UUID


@dataclass
class LeaderboardEntry:
    team_id: UUID
    total_score: int
    average_score: float
