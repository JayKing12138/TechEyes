"""历史记录持久化存储（PostgreSQL）"""

import json
import threading
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import text

from database import engine


class HistoryStore:
    """基于 PostgreSQL 的历史记录存储"""

    def __init__(self):
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS analysis_history (
                        session_id TEXT PRIMARY KEY,
                        owner_key TEXT NOT NULL,
                        query TEXT NOT NULL,
                        status TEXT NOT NULL,
                        progress INTEGER NOT NULL DEFAULT 0,
                        summary TEXT,
                        result_json TEXT,
                        start_time TIMESTAMPTZ,
                        end_time TIMESTAMPTZ,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_history_start_time ON analysis_history(start_time DESC)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_history_owner_key ON analysis_history(owner_key)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_history_query ON analysis_history(query)"))

    def _to_iso(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, str):
            return value
        return str(value)

    def upsert_session(self, session: dict) -> None:
        session_id = session.get("session_id")
        if not session_id:
            return

        result = session.get("result") if isinstance(session.get("result"), dict) else None
        summary = ""
        if result:
            raw_summary = result.get("summary", "")
            summary = raw_summary[:180] if isinstance(raw_summary, str) else ""

        now_iso = datetime.now().isoformat()
        payload = {
            "session_id": session_id,
            "owner_key": session.get("owner_key") or "guest:unknown",
            "query": session.get("query", ""),
            "status": session.get("status", "idle"),
            "progress": int(session.get("progress", 0) or 0),
            "summary": summary,
            "result_json": json.dumps(result, ensure_ascii=False) if result else None,
            "start_time": self._to_iso(session.get("start_time")),
            "end_time": self._to_iso(session.get("end_time")),
            "updated_at": now_iso,
        }

        with self._lock:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO analysis_history (
                            session_id, owner_key, query, status, progress, summary, result_json,
                            start_time, end_time, updated_at
                        ) VALUES (
                            :session_id, :owner_key, :query, :status, :progress, :summary, :result_json,
                            :start_time, :end_time, :updated_at
                        )
                        ON CONFLICT(session_id) DO UPDATE SET
                            owner_key = excluded.owner_key,
                            query = excluded.query,
                            status = excluded.status,
                            progress = excluded.progress,
                            summary = excluded.summary,
                            result_json = COALESCE(excluded.result_json, analysis_history.result_json),
                            start_time = COALESCE(excluded.start_time, analysis_history.start_time),
                            end_time = excluded.end_time,
                            updated_at = excluded.updated_at
                        """
                    ),
                    payload,
                )

    def get_result(self, session_id: str, owner_key: str) -> Optional[dict]:
        with engine.begin() as conn:
            row = conn.execute(
                text("SELECT result_json FROM analysis_history WHERE session_id = :session_id AND owner_key = :owner_key"),
                {"session_id": session_id, "owner_key": owner_key},
            ).mappings().first()

        if not row or not row["result_json"]:
            return None

        try:
            return json.loads(row["result_json"])
        except json.JSONDecodeError:
            return None

    def list_history(self, owner_key: str, limit: int = 50, keyword: Optional[str] = None) -> list[dict]:
        limit = max(1, min(limit, 200))

        sql = """
            SELECT session_id, query, status, progress, summary, start_time, end_time
            FROM analysis_history
            WHERE owner_key = :owner_key
        """

        bind_params: dict[str, Any] = {
            "owner_key": owner_key,
            "limit": limit,
        }

        if keyword:
            sql += " AND query ILIKE :keyword "
            bind_params["keyword"] = f"%{keyword.strip()}%"

        sql += " ORDER BY COALESCE(start_time, updated_at) DESC LIMIT :limit"

        with engine.begin() as conn:
            rows = conn.execute(text(sql), bind_params).mappings().all()

        return [
            {
                "session_id": row["session_id"],
                "query": row["query"],
                "status": row["status"],
                "progress": row["progress"],
                "summary": row["summary"] or "",
                "start_time": row["start_time"],
                "end_time": row["end_time"],
            }
            for row in rows
        ]

    def delete_session(self, session_id: str, owner_key: str) -> bool:
        """删除指定的历史记录（需验证 owner）"""
        with self._lock:
            with engine.begin() as conn:
                cursor = conn.execute(
                    text("DELETE FROM analysis_history WHERE session_id = :session_id AND owner_key = :owner_key"),
                    {"session_id": session_id, "owner_key": owner_key},
                )
                return cursor.rowcount > 0
