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
  "status": "Draft | Registration | Running | Finished",
  "created_at": 1710000000,
  "updated_at": 1710000100
}
```

Allowed tournament statuses are `Draft`, `Registration`, `Running`, and
`Finished`. `created_at` and `updated_at` are Unix timestamps in seconds.
`updated_at` is present after a tournament has been updated.

Tournament detail responses use `participants` instead of `participant_ids`.
`participants` is always present, is never `null`, and contains public user
objects. If a stored participant id no longer points to an existing user, that
user is omitted from `participants`.

## Supported Messages

### auth

Authenticates an existing user by email or login and password.

Request:

```json
{
  "type": "auth",
  "email": "alice@example.com",
  "password": "secret123"
}
```

The request may send `login` instead of `email`. If the client uses a single identifier field, `email` may also contain the login value.

```json
{
  "type": "auth",
  "login": "alice",
  "password": "secret123"
}
```

`username` is also accepted as a compatibility alias for `login`.

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
- `email`, when provided, must be a valid email address.
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

### logout

Revokes the active server-managed device token for the current WebSocket client.

Request:

```json
{
  "type": "logout",
  "device_token": "device-token"
}
```

Required fields:

- `device_token`

Successful response:

```json
{
  "is_ok": true,
  "type": "logout"
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

### update_tournament

Updates editable tournament information. The authenticated user must have the
`organizer` role and must be the tournament creator.

Request:

```json
{
  "type": "update_tournament",
  "device_token": "device-token",
  "tournament_id": "tournament-id",
  "title": "Summer Cup",
  "description": "Updated event",
  "start_date": "2026-05-10",
  "end_date": "2026-05-12"
}
```

Required fields:

- `device_token`
- `tournament_id`

Editable fields:

- `title`
- `description`
- `start_date`
- `end_date`

Successful response:

```json
{
  "is_ok": true,
  "type": "update_tournament",
  "tournament": {
    "_id": "tournament-id",
    "title": "Summer Cup",
    "description": "Updated event",
    "created_by": "user-id",
    "start_date": "2026-05-10",
    "end_date": "2026-05-12",
    "participant_ids": [],
    "status": "Draft",
    "created_at": 1710000000,
    "updated_at": 1710000100
  }
}
```

Current inline errors:

```json
{
  "is_ok": false,
  "type": "update_tournament",
  "error": "Tournament not found"
}
```

Possible error messages include:

- `Authentication required`
- `Access denied`
- `Required data is missing`
- `Invalid tournament_id`
- `Tournament not found`
- `Invalid tournament data: 'title' cannot be empty`
- `Invalid tournament dates`
- `Invalid tournament dates: 'start_date' must be earlier than 'end_date'`

### change_tournament_status

Changes a tournament status. The authenticated user must have the `organizer`
role and must be the tournament creator.

Request:

```json
{
  "type": "change_tournament_status",
  "device_token": "device-token",
  "tournament_id": "tournament-id",
  "status": "Registration"
}
```

Required fields:

- `device_token`
- `tournament_id`
- `status`

Allowed `status` values:

- `Draft`
- `Registration`
- `Running`
- `Finished`

Successful response:

```json
{
  "is_ok": true,
  "type": "change_tournament_status",
  "tournament": {
    "_id": "tournament-id",
    "title": "Spring Cup",
    "description": "Test event",
    "created_by": "user-id",
    "start_date": "2026-05-01",
    "end_date": "2026-05-03",
    "participants": [],
    "status": "Registration",
    "created_at": 1710000000,
    "updated_at": 1710000100
  }
}
```

Current standard errors:

```json
{
  "is_ok": false,
  "type": "change_tournament_status",
  "error": "The requested resource was not found.",
  "err_code": "#NOT_FOUND"
}
```

Possible error codes include:

- `#AUTH_TOKEN_EMPTY`
- `#INSECURE_CONNECTION`
- `#INCOMPLETE_REQUEST`
- `#FORBIDDEN`
- `#INVALID_ID`
- `#INVALID_STATUS`
- `#NOT_FOUND`

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

### get_tournament

Returns a single tournament with resolved public participant information.

Request:

```json
{
  "type": "get_tournament",
  "device_token": "device-token",
  "tournament_id": "tournament-id"
}
```

Required fields:

- `device_token`
- `tournament_id`

Successful response:

```json
{
  "is_ok": true,
  "type": "get_tournament",
  "tournament": {
    "_id": "tournament-id",
    "title": "Spring Cup",
    "description": "Test event",
    "created_by": "user-id",
    "start_date": "2026-05-01",
    "end_date": "2026-05-03",
    "participants": [
      {
        "_id": "participant-user-id",
        "email": "participant@example.com",
        "full_name": "Participant User",
        "login": "participant",
        "role": "team"
      }
    ],
    "status": "Draft",
    "created_at": 1710000000
  }
}
```

When no assigned participants can be resolved, `participants` is returned as
`[]`.

Current inline errors:

```json
{
  "is_ok": false,
  "type": "get_tournament",
  "error": "Tournament not found"
}
```

### get_actual_tournaments

Returns tournaments available to the authenticated user. Admins receive all
actual tournaments, organizers receive actual tournaments they created, and
participant roles receive actual tournaments where their user id is included in
`participant_ids`. Archived tournaments are not included.

Request:

```json
{
  "type": "get_actual_tournaments",
  "device_token": "device-token"
}
```

Required fields:

- `device_token`

Successful response:

```json
{
  "is_ok": true,
  "type": "get_actual_tournaments",
  "tournaments": [
    {
      "_id": "tournament-id",
      "title": "Spring Cup",
      "description": "Test event",
      "created_by": "user-id",
      "start_date": "2026-05-01",
      "end_date": "2026-05-03",
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
  "type": "get_actual_tournaments",
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

### search_users

Searches public user records for role management or tournament participant
assignment.

Admins may use `purpose: "role_management"` to retrieve users for role
management. Organizers may use `purpose: "tournament_participants"` to retrieve
eligible tournament participants.

Request:

```json
{
  "type": "search_users",
  "device_token": "device-token",
  "purpose": "role_management",
  "query": "bob",
  "limit": 20
}
```

Required fields:

- `device_token`

Optional fields:

- `purpose`: `role_management` or `tournament_participants`
- `query`: case-insensitive search text matched against `email`, `full_name`, and `login`
- `search`: accepted as an alias for `query`
- `limit`: maximum result count from 1 to 100; defaults to 20

Successful response:

```json
{
  "is_ok": true,
  "type": "search_users",
  "users": [
    {
      "_id": "user-id",
      "email": "bob@example.com",
      "full_name": "Bob Example",
      "login": "bob",
      "role": "team"
    }
  ]
}
```

Only public user fields are returned: `_id`, `email`, `full_name`, `login`, and
`role`. Passwords and private fields are never returned.

Current inline errors:

```json
{
  "is_ok": false,
  "type": "search_users",
  "error": "Access denied"
}
```

Possible error messages include:

- `Authentication required`
- `Access denied`

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
