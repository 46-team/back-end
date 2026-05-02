# WebSocket API Contract

This document describes the current backend and frontend WebSocket contract.
The current backend implementation is the source of truth.

## Endpoint

```text
WS /apiws
```

The client must complete a handshake before sending application messages.

## Connection Lifecycle

1. Client opens a WebSocket connection to `/apiws`.
2. Client sends a JSON handshake request:

```json
{
  "type": "handshake_request",
  "client_public_key": "-----BEGIN PUBLIC KEY-----..."
}
```

3. Server responds with the server public key as bytes.
4. Both sides derive the shared ECDH key.
5. All further application messages are AES-GCM encrypted bytes.
6. Decrypted application messages are JSON objects.

If the first message is not a handshake request, the server responds with:

```json
{
  "is_ok": false,
  "error": "It seems like you are not authorized. Make handshake request first."
}
```

## Message Envelope

All decrypted application requests must include a `type` field:

```json
{
  "type": "message_type"
}
```

Successful responses use this common shape:

```json
{
  "is_ok": true,
  "type": "message_type"
}
```

Error responses generally use this common shape:

```json
{
  "is_ok": false,
  "type": "message_type",
  "error": "Human readable error message",
  "err_code": "#ERROR_CODE"
}
```

Some handlers currently return inline errors without `err_code`. See
[errors.md](./errors.md).

## Shared Data Shapes

### PublicUser

Public user objects returned to the frontend contain only public fields:

```json
{
  "_id": "string",
  "email": "string",
  "full_name": "string",
  "login": "string",
  "role": "admin | team | jury | organizer"
}
```

The backend may omit fields that are not present in the stored document.
The `password` field must not be returned in public user responses.

### Tournament

Tournament objects currently use this shape:

```json
{
  "_id": "string",
  "title": "string",
  "description": "string | null",
  "created_by": "string",
  "start_date": "string | null",
  "end_date": "string | null",
  "participant_ids": ["string"],
  "status": "Draft",
  "created_at": 1710000000
}
```

`created_at` is a Unix timestamp in seconds.

## Supported Messages

### auth

Authenticates an existing user by login and password.

Request:

```json
{
  "type": "auth",
  "login": "alice",
  "password": "secret123"
}
```

Successful response:

```json
{
  "is_ok": true,
  "type": "auth",
  "token": "device-token",
  "auth_mode": "login",
  "user": {
    "_id": "user-id",
    "email": "alice@example.com",
    "full_name": "Alice Example",
    "login": "alice",
    "role": "team"
  }
}
```

Known errors:

- `#INCORRECT_LOGIN`
- `#PROHIBITED_METHOD`

### register_account

Creates a new account and authenticates the created user.

Request:

```json
{
  "type": "register_account",
  "login": "alice",
  "password": "secret123",
  "full_name": "Alice Example",
  "email": "alice@example.com"
}
```

Required fields:

- `login`
- `password`
- `full_name`

Optional fields:

- `email`

Validation:

- `login` must contain at least 3 characters after trimming.
- `password` must contain at least 6 characters.
- `login` and `email` must be unique.

Successful response:

```json
{
  "is_ok": true,
  "type": "register_account",
  "token": "device-token",
  "auth_mode": "register",
  "user": {
    "_id": "user-id",
    "email": "alice@example.com",
    "full_name": "Alice Example",
    "login": "alice",
    "role": "team"
  }
}
```

Known errors:

- `#INCOMPLETE_REQUEST`
- `#INVALID_PASSWORD`
- `#USER_ALREADY_EXISTS`

### get_me

Returns the currently authenticated user for a device token.

Request:

```json
{
  "type": "get_me",
  "device_token": "device-token"
}
```

Required fields:

- `device_token`

Successful response:

```json
{
  "is_ok": true,
  "type": "get_me",
  "user": {
    "_id": "user-id",
    "email": "alice@example.com",
    "full_name": "Alice Example",
    "login": "alice",
    "role": "team"
  }
}
```

Known errors:

- `#INSECURE_CONNECTION`

### create_tournament

Creates a tournament. The authenticated user must have the `organizer` role.

Request:

```json
{
  "type": "create_tournament",
  "device_token": "device-token",
  "title": "Spring Cup",
  "description": "Test event",
  "start_date": "2026-05-01",
  "end_date": "2026-05-03"
}
```

Required fields:

- `device_token`
- `title`

Optional fields:

- `description`
- `start_date`
- `end_date`

Successful response:

```json
{
  "is_ok": true,
  "type": "create_tournament",
  "tournament": {
    "_id": "tournament-id",
    "title": "Spring Cup",
    "description": "Test event",
    "created_by": "user-id",
    "start_date": "2026-05-01",
    "end_date": "2026-05-03",
    "participant_ids": [],
    "status": "Draft",
    "created_at": 1710000000
  }
}
```

Current inline errors:

```json
{
  "is_ok": false,
  "type": "create_tournament",
  "error": "Access denied"
}
```

Possible error messages include:

- `Access denied`
- `Invalid tournament data: 'title' is required`

If `device_token` is invalid, the current handler returns no response.

### get_tournaments

Returns all tournaments.

Request:

```json
{
  "type": "get_tournaments",
  "device_token": "device-token"
}
```

Required fields:

- `device_token`

Successful response:

```json
{
  "is_ok": true,
  "type": "get_tournaments",
  "tournaments": [
    {
      "_id": "tournament-id",
      "title": "Spring Cup",
      "description": "Test event",
      "created_by": "user-id",
      "start_date": "2026-05-01",
      "end_date": "2026-05-03",
      "participant_ids": ["participant-user-id"],
      "status": "Draft",
      "created_at": 1710000000
    }
  ]
}
```

Current inline errors:

```json
{
  "is_ok": false,
  "type": "get_tournaments",
  "error": "Invalid token"
}
```

### assign_tournament_participants

Replaces the participant list for a tournament. The authenticated user must have
the `organizer` role.

Request:

```json
{
  "type": "assign_tournament_participants",
  "device_token": "device-token",
  "tournament_id": "tournament-id",
  "participant_ids": ["participant-user-id"]
}
```

Required fields:

- `device_token`
- `tournament_id`
- `participant_ids`

Successful response:

```json
{
  "is_ok": true,
  "type": "assign_tournament_participants",
  "tournament": {
    "_id": "tournament-id",
    "title": "Spring Cup",
    "description": "Test event",
    "created_by": "user-id",
    "start_date": "2026-05-01",
    "end_date": "2026-05-03",
    "participant_ids": ["participant-user-id"],
    "status": "Draft",
    "created_at": 1710000000
  }
}
```

Current inline errors:

```json
{
  "is_ok": false,
  "type": "assign_tournament_participants",
  "error": "Access denied"
}
```

Possible error messages include:

- `Authentication required`
- `Access denied`
- `Required data is missing`
- `Invalid tournament_id`
- `Tournament not found`
- `Invalid participant_ids`
- `Invalid user_id`
- `User not found`

### update_user_role

Updates another user's role. The authenticated user must have the `admin` role.

Request:

```json
{
  "type": "update_user_role",
  "device_token": "device-token",
  "target_user_id": "user-id",
  "role": "jury"
}
```

Required fields:

- `device_token`
- `target_user_id` or `user_id`
- `role`

Allowed roles:

- `admin`
- `team`
- `jury`
- `organizer`

Successful response:

```json
{
  "is_ok": true,
  "type": "update_user_role",
  "user": {
    "_id": "user-id",
    "email": "bob@example.com",
    "full_name": "Bob Example",
    "login": "bob",
    "role": "jury"
  }
}
```

Current inline errors:

```json
{
  "is_ok": false,
  "type": "update_user_role",
  "error": "Access denied"
}
```

Possible error messages include:

- `Authentication required`
- `Access denied`
- `Required data is missing`
- `Invalid role`
- `User not found`
- `Users cannot change their own role`

### echo

Returns the provided message payload.

Request:

```json
{
  "type": "echo",
  "message": "hello"
}
```

Successful response:

```json
{
  "is_ok": true,
  "type": "echo",
  "message": "hello"
}
```

## Unknown Message Type

If `type` is not supported, the server returns:

```json
{
  "is_ok": false,
  "type": "null",
  "error": "Request not recognized. Please verify the method and try again.",
  "err_code": "#UNKNOWN_METHOD"
}
```

## Contract Maintenance Rules

- Any new WebSocket message type must be added to this document.
- Any response field change must be reflected here before frontend usage.
- New shared objects should be documented in "Shared Data Shapes".
- New standard errors should be added to [errors.md](./errors.md).
- Prefer adding or updating JSON Schema in `contracts/ws-messages.schema.json`
  when a message payload changes.
