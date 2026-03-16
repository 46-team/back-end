from enum import IntFlag


class TournamentStatus(IntFlag):
    NONE = 0
    IS_DRAFT = 1
    IS_REGISTRATION = 2
    IS_RUNNING = 4
    IS_FINISHED = 8


class Tournament:
    def __init__(self, id: str, title: str, desc: str, status: TournamentStatus, start_date: int, finish_date: int,
                 max_teams: int | None, rounds: list | None):
        self.id = id
        self.title = title
        self.desc = desc
        self.status = status
        self.start_date = start_date
        self.finish_date = finish_date
        self.max_teams = max_teams
        self.rounds = rounds

        if self.max_teams is None:
            self.max_teams = 1

        if self.rounds is None:
            self.rounds = []

    async def open_registration(self):
        pass

    async def close_registration(self):
        pass

    async def start(self):
        pass

    async def finish(self):
        pass

    async def add_round(self):
        pass

    async def del_round(self):
        pass
