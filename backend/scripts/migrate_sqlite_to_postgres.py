"""Migrate legacy SQLite data files to PostgreSQL.

Usage:
    cd backend
    conda run -n techeyes python scripts/migrate_sqlite_to_postgres.py
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

from sqlalchemy import text

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import models  # noqa: F401 - ensure SQLAlchemy models are registered
from config import get_config
from database import engine, init_db
from services.cache_service import CacheService
from services.conversation_store import ConversationStore
from services.history_store import HistoryStore


def _sqlite_rows(db_path: Path, query: str):
    if not db_path.exists():
        return []
    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query).fetchall()
    return rows


def migrate_users(storage_dir: Path) -> int:
    sqlite_path = storage_dir / "techeyes.db"
    rows = _sqlite_rows(
        sqlite_path,
        "SELECT id, username, password_hash, created_at FROM users",
    )
    if not rows:
        return 0

    inserted = 0
    with engine.begin() as conn:
        for row in rows:
            result = conn.execute(
                text(
                    """
                    INSERT INTO users (id, username, password_hash, created_at)
                    VALUES (:id, :username, :password_hash, :created_at)
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {
                    "id": row["id"],
                    "username": row["username"],
                    "password_hash": row["password_hash"],
                    "created_at": row["created_at"],
                },
            )
            inserted += int(result.rowcount or 0)
    return inserted


def migrate_conversations(storage_dir: Path) -> tuple[int, int]:
    sqlite_path = storage_dir / "conversation.db"
    conv_rows = _sqlite_rows(
        sqlite_path,
        "SELECT conversation_id, owner_key, title, status, created_at, updated_at FROM conversations",
    )
    msg_rows = _sqlite_rows(
        sqlite_path,
        "SELECT conversation_id, owner_key, turn_id, role, content, meta_json, created_at FROM messages",
    )

    inserted_conv = 0
    inserted_msg = 0

    with engine.begin() as conn:
        for row in conv_rows:
            result = conn.execute(
                text(
                    """
                    INSERT INTO conversations (conversation_id, owner_key, title, status, created_at, updated_at)
                    VALUES (:conversation_id, :owner_key, :title, :status, :created_at, :updated_at)
                    ON CONFLICT (conversation_id) DO NOTHING
                    """
                ),
                {
                    "conversation_id": row["conversation_id"],
                    "owner_key": row["owner_key"],
                    "title": row["title"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                },
            )
            inserted_conv += int(result.rowcount or 0)

        for row in msg_rows:
            result = conn.execute(
                text(
                    """
                    INSERT INTO messages (conversation_id, owner_key, turn_id, role, content, meta_json, created_at)
                    VALUES (:conversation_id, :owner_key, :turn_id, :role, :content, :meta_json, :created_at)
                    ON CONFLICT (conversation_id, turn_id) DO NOTHING
                    """
                ),
                {
                    "conversation_id": row["conversation_id"],
                    "owner_key": row["owner_key"],
                    "turn_id": row["turn_id"],
                    "role": row["role"],
                    "content": row["content"],
                    "meta_json": row["meta_json"],
                    "created_at": row["created_at"],
                },
            )
            inserted_msg += int(result.rowcount or 0)

    return inserted_conv, inserted_msg


def migrate_history(storage_dir: Path) -> int:
    sqlite_path = storage_dir / "history.db"
    rows = _sqlite_rows(
        sqlite_path,
        """
        SELECT session_id, owner_key, query, status, progress, summary, result_json, start_time, end_time, updated_at
        FROM analysis_history
        """,
    )
    if not rows:
        return 0

    inserted = 0
    with engine.begin() as conn:
        for row in rows:
            result = conn.execute(
                text(
                    """
                    INSERT INTO analysis_history (
                        session_id, owner_key, query, status, progress, summary, result_json,
                        start_time, end_time, updated_at
                    ) VALUES (
                        :session_id, :owner_key, :query, :status, :progress, :summary, :result_json,
                        :start_time, :end_time, :updated_at
                    )
                    ON CONFLICT (session_id) DO NOTHING
                    """
                ),
                {
                    "session_id": row["session_id"],
                    "owner_key": row["owner_key"] or "legacy:migrated",
                    "query": row["query"],
                    "status": row["status"],
                    "progress": row["progress"],
                    "summary": row["summary"],
                    "result_json": row["result_json"],
                    "start_time": row["start_time"],
                    "end_time": row["end_time"],
                    "updated_at": row["updated_at"],
                },
            )
            inserted += int(result.rowcount or 0)

    return inserted


def migrate_semantic_cache(storage_dir: Path) -> int:
    sqlite_path = storage_dir / "semantic_cache.db"
    rows = _sqlite_rows(
        sqlite_path,
        """
        SELECT scope, owner_key, model_signature, normalized_query, normalized_context,
               query_embedding, context_embedding, pointer_key, created_at
        FROM semantic_cache_index
        """,
    )
    if not rows:
        return 0

    inserted = 0
    with engine.begin() as conn:
        for row in rows:
            result = conn.execute(
                text(
                    """
                    INSERT INTO semantic_cache_index (
                        scope, owner_key, model_signature, normalized_query, normalized_context,
                        query_embedding, context_embedding, pointer_key, created_at
                    ) VALUES (
                        :scope, :owner_key, :model_signature, :normalized_query, :normalized_context,
                        :query_embedding, :context_embedding, :pointer_key, :created_at
                    )
                    """
                ),
                {
                    "scope": row["scope"],
                    "owner_key": row["owner_key"],
                    "model_signature": row["model_signature"],
                    "normalized_query": row["normalized_query"],
                    "normalized_context": row["normalized_context"],
                    "query_embedding": row["query_embedding"],
                    "context_embedding": row["context_embedding"],
                    "pointer_key": row["pointer_key"],
                    "created_at": row["created_at"],
                },
            )
            inserted += int(result.rowcount or 0)

    return inserted


def print_counts():
    with engine.begin() as conn:
        counts = {
            "users": conn.execute(text("SELECT COUNT(*) FROM users")).scalar_one(),
            "conversations": conn.execute(text("SELECT COUNT(*) FROM conversations")).scalar_one(),
            "messages": conn.execute(text("SELECT COUNT(*) FROM messages")).scalar_one(),
            "analysis_history": conn.execute(text("SELECT COUNT(*) FROM analysis_history")).scalar_one(),
            "semantic_cache_index": conn.execute(text("SELECT COUNT(*) FROM semantic_cache_index")).scalar_one(),
        }

    print("\nPostgreSQL row counts:")
    for k, v in counts.items():
        print(f"  - {k}: {v}")


def main() -> None:
    cfg = get_config()
    storage_dir = Path(cfg.app.storage_path)
    os.makedirs(storage_dir, exist_ok=True)

    # Ensure all PostgreSQL tables exist before migration.
    init_db()
    ConversationStore()
    HistoryStore()
    CacheService()

    print(f"Using storage dir: {storage_dir}")
    print(f"Target PostgreSQL: {cfg.database.url}")

    users = migrate_users(storage_dir)
    convs, msgs = migrate_conversations(storage_dir)
    hist = migrate_history(storage_dir)
    sem = migrate_semantic_cache(storage_dir)

    print("\nMigration completed:")
    print(f"  - users inserted: {users}")
    print(f"  - conversations inserted: {convs}")
    print(f"  - messages inserted: {msgs}")
    print(f"  - history inserted: {hist}")
    print(f"  - semantic cache inserted: {sem}")

    print_counts()


if __name__ == "__main__":
    main()
