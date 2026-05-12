# SFLU FastAPI WebSocket Backend

This backend is a Python service built with FastAPI. It exposes the
application WebSocket API, handles authentication/session state, and stores
persistent application data in MongoDB.

## Technologies

- Python
- FastAPI
- Uvicorn
- MongoDB

## Required Tools

- Python 3.10+ or another project-compatible Python 3 version
- pip
- MongoDB, either local or hosted

## Setup

Create and activate a virtual environment from the `back-end` directory:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install runtime dependencies:

```bash
pip install -r requirements.txt
```

For local development and tests, also install the development dependencies:

```bash
pip install -r requirements-dev.txt
```

## Configuration

The backend reads configuration from environment variables and from
`back-end/config/.env`. Values from `config/.env` override matching process
environment variables.

Create `back-end/config/.env` with the following variables:

```env
SERVER_DB_IP=127.0.0.1
SERVER_DB_PORT=27017
SERVER_DB_NAME=sflu
SERVER_DB_USERNAME=
SERVER_DB_PASSWORD=

SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=username
SMTP_PASSWORD=password
SMTP_FROM_EMAIL=no-reply@example.com
SMTP_USE_TLS=true
```

### MongoDB Variables

- `SERVER_DB_IP`: MongoDB host name or IP address.
- `SERVER_DB_PORT`: MongoDB port, usually `27017`.
- `SERVER_DB_NAME`: MongoDB database name used by the backend.
- `SERVER_DB_USERNAME`: Optional MongoDB username. Leave empty for local MongoDB without authentication.
- `SERVER_DB_PASSWORD`: Optional MongoDB password. Leave empty for local MongoDB without authentication.

If both `SERVER_DB_USERNAME` and `SERVER_DB_PASSWORD` are set, the backend
connects with credentials. Otherwise it connects without authentication.

### SMTP Variables

- `SMTP_HOST`: SMTP server host.
- `SMTP_PORT`: SMTP server port, commonly `587` for STARTTLS.
- `SMTP_USERNAME`: SMTP account username.
- `SMTP_PASSWORD`: SMTP account password or app password.
- `SMTP_FROM_EMAIL`: Sender email address used for outbound messages.
- `SMTP_USE_TLS`: Whether SMTP TLS should be enabled, for example `true` or `false`.

## Running Locally

Start MongoDB first, then run the backend from the `back-end` directory:

```bash
python main.py
```

The service starts Uvicorn on `0.0.0.0:8000`.

The backend exposes its WebSocket endpoint at:

```text
ws://localhost:8000/apiws
```

The WebSocket protocol is documented in
[docs/websocket-contract.md](docs/websocket-contract.md).

Session data is persisted in `back-end/config/SESSIONS.dat`.

## Testing

Install both runtime and development dependencies, then run:

```bash
pytest
```

## Deployment

For deployment, provide the same environment variables listed above through
the target runtime environment or a deployed `config/.env` file. Ensure the
deployed service can reach MongoDB, then run the application with Uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --ws-ping-interval 10 --ws-ping-timeout 10
```

Expose the WebSocket route `/apiws` through the hosting platform or reverse
proxy, and preserve `back-end/config/SESSIONS.dat` if session continuity must
survive restarts.
