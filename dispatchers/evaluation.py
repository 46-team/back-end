from enum import IntFlag
from submission import Submission
from account import User


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
