# Architecture Overview

## System Components

This document describes the high-level architecture of the application.

### Backend API

The backend is built with a layered architecture:

1. **Routes Layer** — Handles HTTP requests, input validation, and response formatting.
2. **Service Layer** — Contains business logic and orchestrates operations across repositories.
3. **Repository Layer** — Manages database access using the connection pool.
4. **Database Layer** — SQLite with WAL mode for concurrent read performance.

### Authentication Flow

1. User submits credentials to `POST /api/auth/login`.
2. Server validates credentials against the user store.
3. On success, a signed JWT token is returned with a 1-hour expiry.
4. Client includes the token in the `Authorization: Bearer <token>` header.
5. The `authMiddleware` function verifies the token on protected routes.
6. Role-based access is enforced by the `adminOnly` middleware.

### Database Schema

```sql
CREATE TABLE users (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT    NOT NULL UNIQUE,
    email    TEXT    NOT NULL,
    role     TEXT    NOT NULL DEFAULT 'viewer'
);

CREATE TABLE sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    token      TEXT    NOT NULL UNIQUE,
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Error Handling Strategy

- All route handlers use try/catch blocks.
- Errors are logged with stack traces in development mode.
- API responses follow a consistent format:
  - Success: `{ "data": ... }`
  - Error: `{ "error": "message" }`

### Deployment

The application is containerized using Docker:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Environment variables:
- `APP_DB_PATH` — Path to the SQLite database file
- `SECRET_KEY` — JWT signing secret
- `LOG_LEVEL` — Logging verbosity (DEBUG, INFO, WARNING, ERROR)

### Caching

We use an in-memory LRU cache for frequently accessed queries:

```python
from functools import lru_cache

@lru_cache(maxsize=256)
def get_user_permissions(user_id: int) -> list[str]:
    """Cached lookup of user permissions."""
    user = user_repo.get_by_id(user_id)
    return ROLE_PERMISSIONS.get(user.role, [])
```

Cache invalidation happens on user role updates.
