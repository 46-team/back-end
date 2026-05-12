import json
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

from bson import ObjectId

from dispatchers.tournaments import update as update_tournament_module
from dispatchers.tournaments import upsert_submission as upsert_submission_module


async def test_message_handler_routes_update_tournament_with_full_context(monkeypatch):
    client = object()
    fake_db = object()
    fake_proto = object()
    handler = AsyncMock()
    user_tokens = {
        "organizer-token": [
            client,
            {"_id": ObjectId(), "role": "organizer"},
            False,
            "login",
            {},
        ]
    }
    encryption_keys = {client: {"key": b"secret"}}
    message = {
        "type": "update_tournament",
        "device_token": "organizer-token",
        "tournament_id": str(ObjectId()),
        "title": "Summer Cup",
    }

    monkeypatch.setitem(
        sys.modules,
        "dispatchers.utils.FGProto",
        SimpleNamespace(FGProto=lambda type, client: fake_proto),
    )
    import websocket as websocket_module

    monkeypatch.setattr(websocket_module.fgproto, "FGProto", lambda type, client: fake_proto)
    monkeypatch.setitem(sys.modules, "main", SimpleNamespace(db=fake_db))
    monkeypatch.setattr(update_tournament_module, "update_tournament_handler", handler)
    monkeypatch.setattr(websocket_module, "USER_TOKENS", user_tokens)
    monkeypatch.setattr(websocket_module, "ENCRYPTION_KEYS", encryption_keys)

    await websocket_module.message_handler(client, json.dumps(message))

    handler.assert_awaited_once_with(
        client=client,
        message=message,
        db=fake_db,
        USER_TOKENS=user_tokens,
        proto=fake_proto,
        ENCRYPTION_KEYS=encryption_keys,
    )


async def test_message_handler_routes_upsert_tournament_submission_with_full_context(monkeypatch):
    client = object()
    fake_db = object()
    fake_proto = object()
    handler = AsyncMock()
    user_tokens = {
        "team-token": [
            client,
            {"_id": ObjectId(), "role": "team"},
            False,
            "login",
            {},
        ]
    }
    encryption_keys = {client: {"key": b"secret"}}
    message = {
        "type": "upsert_tournament_submission",
        "device_token": "team-token",
        "tournament_id": str(ObjectId()),
        "repository_url": "https://github.com/team/project",
        "video_demo_url": "https://video.example/demo",
    }

    monkeypatch.setitem(
        sys.modules,
        "dispatchers.utils.FGProto",
        SimpleNamespace(FGProto=lambda type, client: fake_proto),
    )
    import websocket as websocket_module

    monkeypatch.setattr(websocket_module.fgproto, "FGProto", lambda type, client: fake_proto)
    monkeypatch.setitem(sys.modules, "main", SimpleNamespace(db=fake_db))
    monkeypatch.setattr(upsert_submission_module, "upsert_tournament_submission_handler", handler)
    monkeypatch.setattr(websocket_module, "USER_TOKENS", user_tokens)
    monkeypatch.setattr(websocket_module, "ENCRYPTION_KEYS", encryption_keys)

    await websocket_module.message_handler(client, json.dumps(message))

    handler.assert_awaited_once_with(
        client=client,
        message=message,
        db=fake_db,
        USER_TOKENS=user_tokens,
        proto=fake_proto,
        ENCRYPTION_KEYS=encryption_keys,
    )
