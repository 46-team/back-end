from enum import IntFlag
from uuid import UUID
from account import User


class TaskStatus(IntFlag):
    NONE = 0
    IS_DELETED = 1
    IS_NEW = 2
    IS_CLOSED = 4
    IS_DRAFT = 8


class TaskInfo:
    def __init__(self, author: UUID, use_times: int, likes: int):
        self._author = author
        self._use_times = use_times
        self._likes = likes

    @property
    def author(self):
        return self._author

    @property
    def use_times(self):
        return self._use_times

    @property
    def likes(self):
        return self._likes


class Task:
    def __init__(self, id: str, title: str, description: str, author: User, info: TaskInfo, status: TaskStatus):
        self.id = id
        self.title = title
        self.description = description
        self.author = author
        self.info = info
        self.status = status

    async def create(self):
        pass

    async def update(self):
        pass

    async def get_info(self):
        pass

    async def delete(self):
        pass
