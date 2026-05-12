import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from bson import ObjectId


class FakeProto:
    def __init__(self):
        self.send_message = AsyncMock()
        self.Error = self._error_factory

    class _error_factory(Exception):
        def __init__(self, proto, message, enc_key, error_code=None, client=None, type="null"):
            super().__init__(message)
            asyncio.get_event_loop().create_task(
                proto.send_message(
                    {
                        "is_ok": False,
                        "type": type,
                        "error": message,
                        "err_code": f"#{error_code}" if error_code else None,
                    },
                    enc_key,
                    client_usr=client,
                )
            )


class FakeCollection:
    def __init__(self, find_one_result=None, insert_one_result=None):
        self.find_one_result = find_one_result
        self.inserted_id = insert_one_result or ObjectId()
        self.find_one = AsyncMock(return_value=find_one_result)
        self.insert_one = AsyncMock(return_value=SimpleNamespace(inserted_id=self.inserted_id))
        self.update_one = AsyncMock()


class FakeDb:
    def __init__(self, collections):
        self.collections = collections

    def __getitem__(self, name):
        return self.collections[name]


@pytest.fixture
def client():
    return object()


@pytest.fixture
def encryption_keys(client):
    return {client: {"key": b"secret"}}


@pytest.fixture
def proto():
    return FakeProto()
