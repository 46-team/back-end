from collections import defaultdict
from enum import IntFlag
from typing import List
from account import User
from leaderboard import LeaderboardEntry
from submission import Submission


class EvaluationCriterion(IntFlag):
    NONE = 0
    BACKEND = 1
    DATABASE = 2
    FRONTEND = 4
    FUNCTIONALITY = 8
    UX = 16
    CREATIVITY = 32
    ADDITIONAL = 64


class Score:
    def __init__(self, criterion: EvaluationCriterion, value: int):
        self._criterion = criterion
        self._value = value

    @property
    def criterion(self):
        return self._criterion

    @property
    def value(self):
        return self._value


class Evaluation:
    def __init__(self, id: str, submission: Submission, jury: User, scores: list[Score] | None, comment: str | None,
                 published_at: int):
        self.id = id
        self.submission = submission
        self.jury = jury
        self.scores = scores
        self.comment = comment
        self.published_at = published_at

    async def calculate_total(self) -> float:
        pass

    def calculate_leaderboard(self, evaluations: List) -> list[LeaderboardEntry]:
        # TODO: needs to be tested

        scores = defaultdict(list)

        for eval in evaluations:
            scores[eval.team_id].append(eval.score)

        leaderboard = []

        for team_id, team_scores in scores.items():
            total = sum(team_scores)
            average = total / len(team_scores)
            leaderboard.append(
                LeaderboardEntry(
                    team_id=team_id,
                    total_score=total,
                    average_score=average
                )
            )

        leaderboard.sort(key=lambda x: x.total_score, reverse=True)
        return leaderboard
