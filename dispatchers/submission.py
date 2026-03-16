from enum import IntFlag
from round import Round
from team import Team


class SubmissionStatus(IntFlag):
    NONE = 0
    IS_DRAFT = 1
    IS_SUBMITTED = 2
    IS_LOCKED = 4
    IS_EVALUATED = 8

class Submission:
    def __init__(self, id: int, team: Team, round: Round, description: str, submitted_at: int,
                 status: SubmissionStatus):
        self.id = id
        self.team = team
        self.round = round
        self.description = description
        self.submitted_at = submitted_at
        self.status = status

    async def update_submission(self):
        pass

    async def lock(self):
        pass
