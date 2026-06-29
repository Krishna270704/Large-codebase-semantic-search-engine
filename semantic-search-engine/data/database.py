"""
database.py — Sample database connection and query module.

Provides a SQLite-backed connection pool, query builder,
and CRUD operations for a simple user management system.
"""

import os
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, List, Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_DB_PATH = os.environ.get("APP_DB_PATH", "app.sqlite3")
MAX_POOL_SIZE = 5


# ---------------------------------------------------------------------------
# Connection pool
# ---------------------------------------------------------------------------

class ConnectionPool:
    """Thread-safe SQLite connection pool.

    Manages a fixed number of reusable database connections to avoid
    the overhead of creating a new connection for every query.

    Parameters
    ----------
    db_path : str
        Path to the SQLite database file.
    max_size : int
        Maximum number of connections in the pool.
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH, max_size: int = MAX_POOL_SIZE):
        self.db_path = db_path
        self.max_size = max_size
        self._pool: List[sqlite3.Connection] = []
        self._lock = threading.Lock()
        self._initialized = False

    def initialize(self) -> None:
        """Create the database file and seed the pool with connections."""
        with self._lock:
            if self._initialized:
                return
            for _ in range(self.max_size):
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA journal_mode=WAL")
                self._pool.append(conn)
            self._initialized = True

    @contextmanager
    def acquire(self) -> Generator[sqlite3.Connection, None, None]:
        """Acquire a connection from the pool (context manager)."""
        if not self._initialized:
            self.initialize()

        conn: Optional[sqlite3.Connection] = None
        with self._lock:
            if self._pool:
                conn = self._pool.pop()

        if conn is None:
            # Pool exhausted — create a temporary connection
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row

        try:
            yield conn
        finally:
            with self._lock:
                if len(self._pool) < self.max_size:
                    self._pool.append(conn)
                else:
                    conn.close()

    def close_all(self) -> None:
        """Close every connection in the pool."""
        with self._lock:
            for conn in self._pool:
                conn.close()
            self._pool.clear()
            self._initialized = False


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class User:
    """Represents a row in the 'users' table."""
    id: Optional[int] = None
    username: str = ""
    email: str = ""
    role: str = "viewer"


# ---------------------------------------------------------------------------
# Repository (CRUD)
# ---------------------------------------------------------------------------

class UserRepository:
    """CRUD operations for the ``users`` table.

    Parameters
    ----------
    pool : ConnectionPool
        A connection pool instance to use for database access.
    """

    CREATE_TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT    NOT NULL UNIQUE,
            email    TEXT    NOT NULL,
            role     TEXT    NOT NULL DEFAULT 'viewer'
        )
    """

    def __init__(self, pool: ConnectionPool):
        self._pool = pool
        self._ensure_table()

    def _ensure_table(self) -> None:
        with self._pool.acquire() as conn:
            conn.execute(self.CREATE_TABLE_SQL)
            conn.commit()

    def create(self, user: User) -> User:
        """Insert a new user and return it with the generated ID."""
        with self._pool.acquire() as conn:
            cursor = conn.execute(
                "INSERT INTO users (username, email, role) VALUES (?, ?, ?)",
                (user.username, user.email, user.role),
            )
            conn.commit()
            user.id = cursor.lastrowid
        return user

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Fetch a user by primary key."""
        with self._pool.acquire() as conn:
            row = conn.execute(
                "SELECT id, username, email, role FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        return User(id=row["id"], username=row["username"], email=row["email"], role=row["role"])

    def get_by_username(self, username: str) -> Optional[User]:
        """Fetch a user by username."""
        with self._pool.acquire() as conn:
            row = conn.execute(
                "SELECT id, username, email, role FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        if row is None:
            return None
        return User(id=row["id"], username=row["username"], email=row["email"], role=row["role"])

    def list_all(self) -> List[User]:
        """Return all users."""
        with self._pool.acquire() as conn:
            rows = conn.execute("SELECT id, username, email, role FROM users").fetchall()
        return [User(id=r["id"], username=r["username"], email=r["email"], role=r["role"]) for r in rows]

    def update(self, user: User) -> None:
        """Update an existing user's email and role."""
        with self._pool.acquire() as conn:
            conn.execute(
                "UPDATE users SET email = ?, role = ? WHERE id = ?",
                (user.email, user.role, user.id),
            )
            conn.commit()

    def delete(self, user_id: int) -> bool:
        """Delete a user by ID. Returns True if a row was deleted."""
        with self._pool.acquire() as conn:
            cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
        return cursor.rowcount > 0
