from enum import IntFlag
from task import Task


class RoundStatus(IntFlag):
    NONE = 0
    IS_DRAFT = 1
    IS_ACTIVE = 2
    IS_SUBMISSION_CLOSED = 4
    IS_EVALUATED = 8


class Round:
    def __init__(self, id: str, tournament_id: str, title: str, description: str, status: RoundStatus, start_time: int,
                 end_time: int, must_complete_rounds_before: list | None, tasks: list[Task] | None):
        self.id = id
        self.tournament_id = tournament_id
        self.title = title
        self.description = description
        self.status = status
        self.start_time = start_time
        self.end_time = end_time
        self.must_complete_rounds_before = must_complete_rounds_before or []
        self.tasks = tasks or []

    async def activate(self):
        pass

    async def close_submissions(self):
        pass

    async def mark_evaluated(self):
        pass

    async def edit(self):
        pass
