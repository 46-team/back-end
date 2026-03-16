from account import User


class Team:
    def __init__(self, id: str, name: str, captain: str | None, members: list[User] | None, organization: str | None,
                 contact: str | None, tournament_id: str | None):
        self.id = id
        self.name = name
        self.captain = captain
        self.members = members or []
        self.organization = organization
        self.contact = contact
        self.tournament_id = tournament_id

    async def add_member(self, user: User):
        pass

    async def remove_member(self, user: User):
        pass

    async def validate_emails(self):
        pass
