from enum import IntFlag


class UserRole(IntFlag):
    NONE = 0
    IS_ADMIN = 1
    IS_ORGANIZER = 2
    IS_TEAM = 4
    IS_JURY = 8
    IS_AUTHOR = 16

class User:

    def __init__(self, id: str, name: str, email: str, role: UserRole, created_at: int):
        self.id = id
        self.name = name
        self.email = email
        self.role = role
        self.created_at = created_at

    async def change_role(self, new_role: UserRole):
        self.role = new_role

    def add_role(self, role: UserRole):
        self.role |= role

    def remove_role(self, role: UserRole):
        self.role &= ~role

    def has_role(self, role: UserRole) -> bool:
        return bool(self.role & role)
