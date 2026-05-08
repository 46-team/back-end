# WebSocket Error Contract

This document lists the current standard WebSocket error format and known error
codes.

## Standard Error Shape

Errors produced through `FGProto.Error` use this shape:

```json
{
  "is_ok": false,
  "type": "message_type",
  "error": "Human readable error message",
  "err_code": "#ERROR_CODE"
}
```

The `type` value is the related request type when the handler passes it. Some
older errors currently use `"null"`.

## Known Standard Errors

| Error code | Message |
| --- | --- |
| `#PROHIBITED_METHOD` | `Internal server error. Please try again later.` |
| `#INSECURE_CONNECTION` | `Unable to establish a secure connection. Please try again later.` |
| `#AUTH_TOKEN_EMPTY` | `Authorization token is missing. Please try again later.` |
| `#INCOMPLETE_REQUEST` | `Required data is missing. Please check your request and try again.` |
| `#DB_INCR_SERVER_ERROR` | `Internal server error. Please try again later.` |
| `#UNKNOWN_METHOD` | `Request not recognized. Please verify the method and try again.` |
| `#ACCOUNT_SYNC_ERR` | `Unable to synchronize account data. Please try again later.` |
| `#SESSION_TOKEN_NF` | `Device not recognized.` |
| `#SESSION_TOKEN_GOOD` | `Invalid operation for current device state.` |
| `#SESSION_TOKEN_EXPIRED` | `Token expired. Please log in again.` |
| `#AUTH_TOKEN_FROZEN` | `Access temporarily restricted. Please log in again.` |
| `#NOT_FULLY_LOGGED_IN` | `Authentication process not completed.` |
| `#INCORRECT_LOGIN` | `Invalid login credentials. Please try again.` |
| `#USER_ALREADY_EXISTS` | `User with this login or email already exists.` |
| `#INVALID_PASSWORD` | `Password must contain at least 6 characters.` |

## Current Inline Errors

Some handlers currently send inline error responses without `err_code`.

### create_tournament

```json
{
  "is_ok": false,
  "type": "create_tournament",
  "error": "Access denied"
}
```

Known messages:

- `Access denied`
- `Invalid tournament data: 'title' is required`

### update_tournament

```json
{
  "is_ok": false,
  "type": "update_tournament",
  "error": "Tournament not found"
}
```

Known messages:

- `Authentication required`
- `Access denied`
- `Required data is missing`
- `Invalid tournament_id`
- `Tournament not found`
- `Invalid tournament data: 'title' cannot be empty`
- `Invalid tournament dates`
- `Invalid tournament dates: 'start_date' must be earlier than 'end_date'`

### get_tournaments

```json
{
  "is_ok": false,
  "type": "get_tournaments",
  "error": "Invalid token"
}
```

### get_actual_tournaments

```json
{
  "is_ok": false,
  "type": "get_actual_tournaments",
  "error": "Invalid token"
}
```

Known messages:

- `Invalid token`
- `Authentication required`

### assign_tournament_participants

```json
{
  "is_ok": false,
  "type": "assign_tournament_participants",
  "error": "Access denied"
}
```

Known messages:

- `Authentication required`
- `Access denied`
- `Required data is missing`
- `Invalid tournament_id`
- `Tournament not found`
- `Invalid participant_ids`
- `Invalid user_id`
- `User not found`

### update_user_role

```json
{
  "is_ok": false,
  "type": "update_user_role",
  "error": "Access denied"
}
```

Known messages:

- `Authentication required`
- `Access denied`
- `Required data is missing`
- `Invalid role`
- `User not found`
- `Users cannot change their own role`

## Recommendation

New handlers should prefer the standard error shape with `err_code`. Existing
inline errors can be migrated gradually, but frontend code should support both
formats until migration is complete.
