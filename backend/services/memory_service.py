"""Long-term memory service for chat conversations."""

import json
import math
import threading
import time
from datetime import datetime, timezone
from typing import Optional

import httpx
from loguru import logger
from sqlalchemy import text

from config import get_config
from database import engine


class MemoryService:
    """Stores and retrieves user-scoped long-term memories."""

    def __init__(self):
        self.config = get_config()
        self._lock = threading.Lock()
        self.raw_keep_limit = int(self._env("MEMORY_RAW_KEEP_LIMIT", "220"))
        self.summary_keep_limit = int(self._env("MEMORY_SUMMARY_KEEP_LIMIT", "80"))
        self.semantic_threshold = 0.75
        self.embedding_model = "text-embedding-v4"
        self.enable_llm_compression = self._env_bool("MEMORY_ENABLE_LLM_COMPRESSION", True)
        self.compression_trigger_raw = int(self._env("MEMORY_COMPRESSION_TRIGGER_RAW", "30"))
        self.compression_batch_size = int(self._env("MEMORY_COMPRESSION_BATCH_SIZE", "40"))
        self.compression_cooldown_seconds = int(self._env("MEMORY_COMPRESSION_COOLDOWN_SECONDS", "600"))
        self._last_compress_ts: dict[str, float] = {}
        self._embedding_key_invalid = self._is_placeholder_api_key(self.config.llm.api_key)
        self._embedding_warned = False
        self._init_db()

    @staticmethod
    def _env(key: str, default: str) -> str:
        import os
        return os.getenv(key, default).strip() or default

    @staticmethod
    def _env_bool(key: str, default: bool) -> bool:
        import os
        raw = os.getenv(key)
        if raw is None:
            return default
        return raw.strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _is_placeholder_api_key(value: str) -> bool:
        key = (value or "").strip().lower()
        if not key:
            return True
        return (
            "your_" in key
            or "api_key_here" in key
            or "replace" in key
            or key in {"test", "demo", "placeholder"}
        )

    def _init_db(self) -> None:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS long_term_memories (
                        id BIGSERIAL PRIMARY KEY,
                        owner_key TEXT NOT NULL,
                        conversation_id TEXT,
                        memory_type TEXT NOT NULL,
                        text_content TEXT NOT NULL,
                        normalized_text TEXT NOT NULL,
                        embedding TEXT,
                        strength DOUBLE PRECISION NOT NULL DEFAULT 1.0,
                        hit_count INTEGER NOT NULL DEFAULT 0,
                        last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        UNIQUE(owner_key, normalized_text)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_ltm_owner_updated ON long_term_memories(owner_key, updated_at DESC)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_ltm_owner_type ON long_term_memories(owner_key, memory_type, updated_at DESC)"
                )
            )

    @staticmethod
    def _normalize(text_value: str) -> str:
        value = (text_value or "").strip().lower()
        for char in ["\n", "\r", "\t", "，", "。", "？", "！", "、", ",", ".", "?", "!", ";", "；", ":", "："]:
            value = value.replace(char, " ")
        return " ".join(value.split())

    async def capture_from_turn(self, owner_key: str, conversation_id: str, user_text: str, assistant_text: str) -> None:
        """Extracts lightweight memories from one dialogue turn and upserts them."""
        candidates = self._extract_candidates(user_text=user_text, assistant_text=assistant_text)
        if not candidates:
            return

        for candidate in candidates:
            try:
                await self.upsert_memory(
                    owner_key=owner_key,
                    conversation_id=conversation_id,
                    memory_type=candidate["memory_type"],
                    text_content=candidate["text_content"],
                )
            except Exception as exc:
                logger.warning(f"memory capture failed: {exc}")

        try:
            await self._maybe_compress_with_llm(owner_key=owner_key, conversation_id=conversation_id)
        except Exception as exc:
            logger.warning(f"memory compression failed: {exc}")

    def _extract_candidates(self, user_text: str, assistant_text: str) -> list[dict]:
        cleaned_user = (user_text or "").strip()
        cleaned_assistant = (assistant_text or "").strip()
        candidates: list[dict] = []

        if cleaned_user:
            candidates.append(
                {
                    "memory_type": "user_interest",
                    "text_content": f"用户关注主题: {cleaned_user[:180]}",
                }
            )

        if cleaned_assistant:
            first_sentence = cleaned_assistant.split("\n")[0].strip()
            if first_sentence:
                candidates.append(
                    {
                        "memory_type": "assistant_fact",
                        "text_content": f"历史结论: {first_sentence[:220]}",
                    }
                )

        return candidates

    async def upsert_memory(
        self,
        owner_key: str,
        conversation_id: str,
        memory_type: str,
        text_content: str,
    ) -> None:
        normalized = self._normalize(text_content)
        if not normalized:
            return

        embedding = await self._embed_text(normalized)
        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            with engine.begin() as conn:
                existing = conn.execute(
                    text(
                        """
                        SELECT id, strength, hit_count
                        FROM long_term_memories
                        WHERE owner_key = :owner_key AND normalized_text = :normalized_text
                        """
                    ),
                    {"owner_key": owner_key, "normalized_text": normalized},
                ).mappings().first()

                if existing:
                    conn.execute(
                        text(
                            """
                            UPDATE long_term_memories
                            SET conversation_id = :conversation_id,
                                memory_type = :memory_type,
                                text_content = :text_content,
                                embedding = COALESCE(:embedding, embedding),
                                strength = LEAST(strength + 0.2, 10.0),
                                updated_at = :updated_at,
                                last_seen_at = :last_seen_at
                            WHERE id = :id
                            """
                        ),
                        {
                            "id": existing["id"],
                            "conversation_id": conversation_id,
                            "memory_type": memory_type,
                            "text_content": text_content[:500],
                            "embedding": json.dumps(embedding) if embedding else None,
                            "updated_at": now,
                            "last_seen_at": now,
                        },
                    )
                else:
                    conn.execute(
                        text(
                            """
                            INSERT INTO long_term_memories (
                                owner_key, conversation_id, memory_type, text_content,
                                normalized_text, embedding, strength, hit_count,
                                created_at, updated_at, last_seen_at
                            ) VALUES (
                                :owner_key, :conversation_id, :memory_type, :text_content,
                                :normalized_text, :embedding, 1.0, 0,
                                :created_at, :updated_at, :last_seen_at
                            )
                            """
                        ),
                        {
                            "owner_key": owner_key,
                            "conversation_id": conversation_id,
                            "memory_type": memory_type,
                            "text_content": text_content[:500],
                            "normalized_text": normalized,
                            "embedding": json.dumps(embedding) if embedding else None,
                            "created_at": now,
                            "updated_at": now,
                            "last_seen_at": now,
                        },
                    )

                self._trim_memories(conn=conn, owner_key=owner_key)

    def _trim_memories(self, conn, owner_key: str) -> None:
        # Keep raw and summary memories with separate limits to avoid summary starvation.
        conn.execute(
            text(
                """
                DELETE FROM long_term_memories
                WHERE id IN (
                    SELECT id FROM long_term_memories
                    WHERE owner_key = :owner_key
                      AND memory_type <> 'summary'
                    ORDER BY updated_at DESC
                    OFFSET :raw_keep_limit
                )
                """
            ),
            {"owner_key": owner_key, "raw_keep_limit": self.raw_keep_limit},
        )

        conn.execute(
            text(
                """
                DELETE FROM long_term_memories
                WHERE id IN (
                    SELECT id FROM long_term_memories
                    WHERE owner_key = :owner_key
                      AND memory_type = 'summary'
                    ORDER BY updated_at DESC
                    OFFSET :summary_keep_limit
                )
                """
            ),
            {"owner_key": owner_key, "summary_keep_limit": self.summary_keep_limit},
        )

    async def _maybe_compress_with_llm(self, owner_key: str, conversation_id: str) -> None:
        if not self.enable_llm_compression or self._embedding_key_invalid:
            return

        now_ts = time.time()
        last_ts = self._last_compress_ts.get(owner_key, 0.0)
        if now_ts - last_ts < self.compression_cooldown_seconds:
            return

        with engine.begin() as conn:
            count_row = conn.execute(
                text(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM long_term_memories
                    WHERE owner_key = :owner_key AND memory_type <> 'summary'
                    """
                ),
                {"owner_key": owner_key},
            ).mappings().first()
            raw_count = int((count_row or {}).get("cnt") or 0)
            if raw_count < self.compression_trigger_raw:
                return

            rows = conn.execute(
                text(
                    """
                    SELECT id, memory_type, text_content, updated_at
                    FROM long_term_memories
                    WHERE owner_key = :owner_key AND memory_type <> 'summary'
                    ORDER BY updated_at DESC
                    LIMIT :limit
                    """
                ),
                {"owner_key": owner_key, "limit": self.compression_batch_size},
            ).mappings().all()

        if len(rows) < self.compression_trigger_raw:
            return

        summaries = await self._llm_compress_memories(rows)
        if not summaries:
            return

        for summary_text in summaries:
            await self.upsert_memory(
                owner_key=owner_key,
                conversation_id=conversation_id,
                memory_type="summary",
                text_content=summary_text,
            )

        # Compression succeeded; now decay old raw memories to reduce noise.
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE long_term_memories
                    SET strength = GREATEST(strength * 0.85, 0.2)
                    WHERE owner_key = :owner_key
                      AND memory_type <> 'summary'
                      AND id IN (
                          SELECT id FROM long_term_memories
                          WHERE owner_key = :owner_key
                            AND memory_type <> 'summary'
                          ORDER BY updated_at DESC
                          OFFSET :keep_recent
                      )
                    """
                ),
                {"owner_key": owner_key, "keep_recent": max(self.raw_keep_limit // 2, 40)},
            )
            self._trim_memories(conn=conn, owner_key=owner_key)

        self._last_compress_ts[owner_key] = now_ts
        logger.info(f"memory compression done: owner={owner_key}, summaries={len(summaries)}, raw_count={raw_count}")

    async def _llm_compress_memories(self, rows: list[dict]) -> list[str]:
        if not rows:
            return []

        memory_lines = []
        for idx, row in enumerate(rows, start=1):
            memory_lines.append(f"{idx}. [{row.get('memory_type')}] {str(row.get('text_content') or '')[:220]}")

        prompt = (
            "请将以下用户历史记忆压缩为 3-8 条高信息密度的长期记忆摘要。"
            "要求：去重、合并同义、保留稳定事实与偏好，不要编造。"
            "输出 JSON 数组，每项包含字段 text。不要输出额外解释。\n\n"
            + "\n".join(memory_lines)
        )

        data = await self._call_chat_json(
            system_prompt="你是记忆压缩器。你的任务是将碎片记忆压缩为简洁、稳定、可检索的长期记忆。",
            user_prompt=prompt,
            max_tokens=800,
            temperature=0.1,
        )
        if not data:
            return []

        summaries: list[str] = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    txt = str(item.get("text") or "").strip()
                else:
                    txt = str(item).strip()
                if txt:
                    summaries.append(f"记忆摘要: {txt[:420]}")

        # De-duplicate within this compression result.
        dedup: list[str] = []
        seen = set()
        for line in summaries:
            normalized = self._normalize(line)
            if normalized and normalized not in seen:
                seen.add(normalized)
                dedup.append(line)

        return dedup[:8]

    async def _call_chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> Optional[object]:
        api_key = self.config.llm.api_key
        base_url = (self.config.llm.base_url or "").rstrip("/")
        if not api_key or not base_url:
            return None

        url = f"{base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        payload = {
            "model": self.config.llm.model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                body = response.json()
            content = body.get("choices", [{}])[0].get("message", {}).get("content")
            if not isinstance(content, str) or not content.strip():
                return None

            parsed = json.loads(content)
            if isinstance(parsed, dict):
                if isinstance(parsed.get("items"), list):
                    return parsed["items"]
                if isinstance(parsed.get("memories"), list):
                    return parsed["memories"]
            if isinstance(parsed, list):
                return parsed
            return None
        except Exception as exc:
            logger.warning(f"memory compression llm call failed: {exc}")
            return None

    async def search_memories(self, owner_key: str, query: str, top_k: int = 5) -> list[dict]:
        normalized_query = self._normalize(query)
        if not normalized_query:
            return []

        query_emb = await self._embed_text(normalized_query)

        with engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, memory_type, text_content, embedding, strength, hit_count, updated_at, last_seen_at
                    FROM long_term_memories
                    WHERE owner_key = :owner_key
                    ORDER BY updated_at DESC
                    LIMIT 250
                    """
                ),
                {"owner_key": owner_key},
            ).mappings().all()

        if not rows:
            return []

        scored: list[tuple[float, dict]] = []
        now_ts = datetime.now(timezone.utc).timestamp()
        for row in rows:
            score = 0.0
            if query_emb and row.get("embedding"):
                try:
                    mem_emb = json.loads(row["embedding"])
                    score = self._cosine_similarity(query_emb, mem_emb)
                except Exception:
                    score = 0.0
            else:
                if normalized_query in self._normalize(row["text_content"]):
                    score = 0.8

            updated_at = row.get("updated_at")
            recency_bonus = 0.0
            if updated_at:
                try:
                    age_days = max((now_ts - updated_at.timestamp()) / 86400.0, 0.0)
                    recency_bonus = math.exp(-age_days / 30.0) * 0.2
                except Exception:
                    recency_bonus = 0.0

            strength_bonus = min(float(row.get("strength") or 1.0) / 20.0, 0.2)
            summary_bonus = 0.08 if row.get("memory_type") == "summary" else 0.0
            final_score = score + recency_bonus + strength_bonus + summary_bonus
            if final_score >= self.semantic_threshold:
                scored.append(
                    (
                        final_score,
                        {
                            "id": row["id"],
                            "memory_type": row["memory_type"],
                            "text": row["text_content"],
                            "score": round(final_score, 4),
                        },
                    )
                )

        scored.sort(key=lambda item: item[0], reverse=True)
        selected = [item[1] for item in scored[: max(1, min(top_k, 10))]]
        if selected:
            await self._mark_memory_hits(memory_ids=[item["id"] for item in selected])
        return selected

    async def _mark_memory_hits(self, memory_ids: list[int]) -> None:
        if not memory_ids:
            return
        now = datetime.now(timezone.utc).isoformat()
        with engine.begin() as conn:
            for memory_id in memory_ids:
                conn.execute(
                    text(
                        """
                        UPDATE long_term_memories
                        SET hit_count = hit_count + 1,
                            strength = LEAST(strength + 0.1, 10.0),
                            last_seen_at = :last_seen_at
                        WHERE id = :memory_id
                        """
                    ),
                    {"memory_id": memory_id, "last_seen_at": now},
                )

    async def _embed_text(self, text_value: str) -> Optional[list[float]]:
        payload_text = (text_value or "").strip()
        if not payload_text:
            return None

        if self._embedding_key_invalid:
            if not self._embedding_warned:
                logger.warning("Memory embedding skipped: LLM_API_KEY invalid")
                self._embedding_warned = True
            return None

        api_key = self.config.llm.api_key
        base_url = (self.config.llm.base_url or "").rstrip("/")
        if not api_key or not base_url:
            return None

        url = f"{base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.embedding_model,
            "input": payload_text,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                emb = data.get("data", [{}])[0].get("embedding")
                if isinstance(emb, list) and emb:
                    return [float(x) for x in emb]
                return None
        except Exception as exc:
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 401:
                if not self._embedding_warned:
                    logger.warning("Memory embedding auth failed (401)")
                    self._embedding_warned = True
                self._embedding_key_invalid = True
                return None
            logger.warning(f"Memory embedding fetch failed: {exc}")
            return None

    @staticmethod
    def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot = 0.0
        norm1 = 0.0
        norm2 = 0.0
        for a, b in zip(vec1, vec2):
            dot += a * b
            norm1 += a * a
            norm2 += b * b

        if norm1 <= 0.0 or norm2 <= 0.0:
            return 0.0

        return dot / (math.sqrt(norm1) * math.sqrt(norm2))

    def get_stats(self) -> dict:
        with engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT COUNT(*) AS total,
                           COALESCE(SUM(hit_count), 0) AS total_hits,
                           COALESCE(AVG(strength), 0) AS avg_strength,
                           COALESCE(SUM(CASE WHEN memory_type = 'summary' THEN 1 ELSE 0 END), 0) AS summary_count,
                           COALESCE(SUM(CASE WHEN memory_type <> 'summary' THEN 1 ELSE 0 END), 0) AS raw_count
                    FROM long_term_memories
                    """
                )
            ).mappings().first()

        return {
            "total_memories": int((row or {}).get("total") or 0),
            "raw_memories": int((row or {}).get("raw_count") or 0),
            "summary_memories": int((row or {}).get("summary_count") or 0),
            "total_hits": int((row or {}).get("total_hits") or 0),
            "avg_strength": round(float((row or {}).get("avg_strength") or 0.0), 3),
            "semantic_threshold": self.semantic_threshold,
            "llm_compression_enabled": self.enable_llm_compression,
        }
