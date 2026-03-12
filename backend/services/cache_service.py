"""Cache service with L1/L2/L3 layers."""

import hashlib
import json
import math
import os
import threading
from collections import OrderedDict
from datetime import datetime
from typing import Optional

import httpx
import redis
from loguru import logger
from sqlalchemy import text

from config import get_config
from database import engine


class CacheService:
    """Three-layer cache: L1 memory, L2 redis, L3 semantic index."""

    def __init__(self):
        self.config = get_config()

        self.l1_max_size = int(os.getenv("CACHE_L1_MAX_SIZE", "300"))
        self.l1_ttl = int(os.getenv("CACHE_L1_TTL_SECONDS", "180"))
        self._l1_cache: OrderedDict[str, tuple[float, dict]] = OrderedDict()
        self._l1_lock = threading.Lock()

        self.redis_ttl = int(os.getenv("CACHE_L2_TTL_SECONDS", str(self.config.cache.cache_ttl)))
        try:
            self.redis_client = redis.from_url(self.config.cache.redis_url)
            self.redis_client.ping()
            logger.info("Redis connected, L2 cache enabled")
        except Exception:
            logger.info("Redis unavailable, L2 cache disabled")
            self.redis_client = None

        self._semantic_lock = threading.Lock()
        self._init_semantic_db()

        self.semantic_threshold = float(os.getenv("CACHE_L3_SIM_THRESHOLD", "0.88"))
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-v4")
        self._embedding_key_invalid = self._is_placeholder_api_key(self.config.llm.api_key)
        self._embedding_warned = False
        if self._embedding_key_invalid:
            logger.warning("LLM_API_KEY 无效或占位符，L3 语义嵌入将自动跳过")

        self.stats = {
            "l1_hits": 0,
            "l2_hits": 0,
            "l3_hits": 0,
            "misses": 0,
        }

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

    def get_cache_key(self, query: str) -> str:
        normalized = self.normalize_text(query)
        digest = hashlib.md5(normalized.encode("utf-8")).hexdigest()
        return f"analysis:legacy:{digest}"

    def get_cached_result(self, query: str) -> Optional[dict]:
        key = self.get_cache_key(query)

        hit = self._get_l1(key)
        if hit is not None:
            self.stats["l1_hits"] += 1
            return hit

        hit = self._get_l2(key)
        if hit is not None:
            self.stats["l2_hits"] += 1
            self._set_l1(key, hit)
            return hit

        self.stats["misses"] += 1
        return None

    def set_cache(self, query: str, result: dict) -> bool:
        key = self.get_cache_key(query)
        self._set_l1(key, result)
        self._set_l2(key, result)
        return True

    async def get_chat_cached_result(
        self,
        owner_key: str,
        query: str,
        context_text: str,
        model_signature: str,
        allow_public: bool,
    ) -> tuple[Optional[dict], Optional[str]]:
        normalized_query = self.normalize_text(query)
        normalized_context = self.normalize_text(context_text)
        context_hash = self._short_hash(normalized_context)

        private_key = self._build_chat_key(
            scope="private",
            owner_key=owner_key,
            normalized_query=normalized_query,
            context_hash=context_hash,
            model_signature=model_signature,
        )

        hit = self._get_l1(private_key)
        if hit is not None:
            self.stats["l1_hits"] += 1
            return hit, "l1-private"

        hit = self._get_l2(private_key)
        if hit is not None:
            self.stats["l2_hits"] += 1
            self._set_l1(private_key, hit)
            return hit, "l2-private"

        public_key = self._build_chat_key(
            scope="public",
            owner_key="*",
            normalized_query=normalized_query,
            context_hash=context_hash,
            model_signature=model_signature,
        )

        if allow_public:
            hit = self._get_l1(public_key)
            if hit is not None:
                self.stats["l1_hits"] += 1
                return hit, "l1-public"

            hit = self._get_l2(public_key)
            if hit is not None:
                self.stats["l2_hits"] += 1
                self._set_l1(public_key, hit)
                return hit, "l2-public"

        l3_key = await self._search_semantic_pointer(
            owner_key=owner_key,
            normalized_query=normalized_query,
            normalized_context=normalized_context,
            model_signature=model_signature,
            allow_public=allow_public,
        )

        if l3_key:
            l3_hit = self._get_l2(l3_key)
            if l3_hit is not None:
                self.stats["l3_hits"] += 1
                self._set_l1(l3_key, l3_hit)
                return l3_hit, "l3"

        self.stats["misses"] += 1
        return None, None

    async def set_chat_cache(
        self,
        owner_key: str,
        query: str,
        context_text: str,
        model_signature: str,
        result: dict,
        allow_public: bool,
    ) -> dict:
        normalized_query = self.normalize_text(query)
        normalized_context = self.normalize_text(context_text)
        context_hash = self._short_hash(normalized_context)

        private_key = self._build_chat_key(
            scope="private",
            owner_key=owner_key,
            normalized_query=normalized_query,
            context_hash=context_hash,
            model_signature=model_signature,
        )

        self._set_l1(private_key, result)
        self._set_l2(private_key, result)

        public_key = None
        if allow_public:
            public_key = self._build_chat_key(
                scope="public",
                owner_key="*",
                normalized_query=normalized_query,
                context_hash=context_hash,
                model_signature=model_signature,
            )
            self._set_l1(public_key, result)
            self._set_l2(public_key, result)

        try:
            query_embedding = await self._embed_text(normalized_query)
            context_embedding = await self._embed_text(normalized_context or "empty context")
            if query_embedding and context_embedding:
                self._upsert_semantic_index(
                    owner_key=owner_key,
                    scope="private",
                    model_signature=model_signature,
                    normalized_query=normalized_query,
                    normalized_context=normalized_context,
                    query_embedding=query_embedding,
                    context_embedding=context_embedding,
                    pointer_key=private_key,
                )
                if allow_public and public_key:
                    self._upsert_semantic_index(
                        owner_key="*",
                        scope="public",
                        model_signature=model_signature,
                        normalized_query=normalized_query,
                        normalized_context=normalized_context,
                        query_embedding=query_embedding,
                        context_embedding=context_embedding,
                        pointer_key=public_key,
                    )
        except Exception as exc:
            logger.warning(f"L3 indexing failed: {exc}")

        return {"private_key": private_key, "public_key": public_key}

    def get_cache_stats(self) -> dict:
        l1_size = len(self._l1_cache)
        redis_keys = 0
        if self.redis_client:
            try:
                redis_keys = self.redis_client.dbsize()
            except Exception:
                redis_keys = -1

        return {
            "backend": "redis" if self.redis_client else "memory-only",
            "l1_entries": l1_size,
            "l2_keys": redis_keys,
            "semantic_threshold": self.semantic_threshold,
            "stats": dict(self.stats),
        }

    @staticmethod
    def normalize_text(text: str) -> str:
        value = (text or "").strip().lower()
        for char in ["\n", "\r", "\t", "，", "。", "？", "！", "、", ",", ".", "?", "!", "；", ";", ":", "："]:
            value = value.replace(char, " ")
        value = " ".join(value.split())

        synonym_map = {
            "多少钱": "价格",
            "收费标准": "价格",
            "价位": "价格",
            "对比一下": "比较",
            "比较下": "比较",
        }
        for src, dst in synonym_map.items():
            value = value.replace(src, dst)
        return value

    @staticmethod
    def _short_hash(text: str) -> str:
        return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:20]

    def _build_chat_key(
        self,
        scope: str,
        owner_key: str,
        normalized_query: str,
        context_hash: str,
        model_signature: str,
    ) -> str:
        q_hash = self._short_hash(normalized_query)
        return f"chat:v1:{scope}:{owner_key}:{model_signature}:{q_hash}:{context_hash}"

    def _get_l1(self, key: str) -> Optional[dict]:
        now = datetime.now().timestamp()
        with self._l1_lock:
            item = self._l1_cache.get(key)
            if not item:
                return None
            expires_at, payload = item
            if expires_at < now:
                del self._l1_cache[key]
                return None
            self._l1_cache.move_to_end(key)
            return payload

    def _set_l1(self, key: str, value: dict) -> None:
        expires_at = datetime.now().timestamp() + self.l1_ttl
        with self._l1_lock:
            self._l1_cache[key] = (expires_at, value)
            self._l1_cache.move_to_end(key)
            while len(self._l1_cache) > self.l1_max_size:
                self._l1_cache.popitem(last=False)

    def _get_l2(self, key: str) -> Optional[dict]:
        if not self.redis_client:
            return None
        try:
            raw = self.redis_client.get(key)
            return json.loads(raw) if raw else None
        except Exception as exc:
            logger.warning(f"L2 read failed: {exc}")
            return None

    def _set_l2(self, key: str, value: dict) -> None:
        if not self.redis_client:
            return
        try:
            self.redis_client.setex(key, self.redis_ttl, json.dumps(value, ensure_ascii=False))
        except Exception as exc:
            logger.warning(f"L2 write failed: {exc}")

    def _init_semantic_db(self) -> None:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS semantic_cache_index (
                        id BIGSERIAL PRIMARY KEY,
                        scope TEXT NOT NULL,
                        owner_key TEXT NOT NULL,
                        model_signature TEXT NOT NULL,
                        normalized_query TEXT NOT NULL,
                        normalized_context TEXT NOT NULL,
                        query_embedding TEXT NOT NULL,
                        context_embedding TEXT NOT NULL,
                        pointer_key TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_semantic_scope_owner ON semantic_cache_index(scope, owner_key, created_at DESC)"
                )
            )
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_semantic_model ON semantic_cache_index(model_signature)"))

    async def _search_semantic_pointer(
        self,
        owner_key: str,
        normalized_query: str,
        normalized_context: str,
        model_signature: str,
        allow_public: bool,
    ) -> Optional[str]:
        query_embedding = await self._embed_text(normalized_query)
        context_embedding = await self._embed_text(normalized_context or "empty context")
        if not query_embedding or not context_embedding:
            return None

        with self._semantic_lock:
            with engine.begin() as conn:
                rows_private = conn.execute(
                    text(
                        """
                        SELECT query_embedding, context_embedding, pointer_key
                        FROM semantic_cache_index
                        WHERE scope = 'private' AND owner_key = :owner_key AND model_signature = :model_signature
                        ORDER BY id DESC
                        LIMIT 150
                        """
                    ),
                    {"owner_key": owner_key, "model_signature": model_signature},
                ).mappings().all()

                rows_public = []
                if allow_public:
                    rows_public = conn.execute(
                        text(
                            """
                            SELECT query_embedding, context_embedding, pointer_key
                            FROM semantic_cache_index
                            WHERE scope = 'public' AND owner_key = '*' AND model_signature = :model_signature
                            ORDER BY id DESC
                            LIMIT 250
                            """
                        ),
                        {"model_signature": model_signature},
                    ).mappings().all()

        best_score = 0.0
        best_pointer: Optional[str] = None
        for row in list(rows_private) + list(rows_public):
            try:
                q_vec = json.loads(row["query_embedding"])
                c_vec = json.loads(row["context_embedding"])
            except Exception:
                continue

            q_sim = self._cosine_similarity(query_embedding, q_vec)
            c_sim = self._cosine_similarity(context_embedding, c_vec)
            score = 0.7 * q_sim + 0.3 * c_sim
            if score > best_score:
                best_score = score
                best_pointer = row["pointer_key"]

        logger.info(f"[L3缓存] 最佳匹配相似度={best_score:.4f}, 阈值={self.semantic_threshold}, 是否命中={best_score >= self.semantic_threshold}")
        if best_pointer and best_score >= self.semantic_threshold:
            return best_pointer
        return None

    def _upsert_semantic_index(
        self,
        owner_key: str,
        scope: str,
        model_signature: str,
        normalized_query: str,
        normalized_context: str,
        query_embedding: list[float],
        context_embedding: list[float],
        pointer_key: str,
    ) -> None:
        with self._semantic_lock:
            with engine.begin() as conn:
                conn.execute(
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
                        "scope": scope,
                        "owner_key": owner_key,
                        "model_signature": model_signature,
                        "normalized_query": normalized_query,
                        "normalized_context": normalized_context,
                        "query_embedding": json.dumps(query_embedding),
                        "context_embedding": json.dumps(context_embedding),
                        "pointer_key": pointer_key,
                        "created_at": datetime.now().isoformat(),
                    },
                )

    async def _embed_text(self, text: str) -> Optional[list[float]]:
        payload_text = (text or "").strip()
        if not payload_text:
            return None

        if self._embedding_key_invalid:
            if not self._embedding_warned:
                logger.warning("Embedding 已跳过：LLM_API_KEY 未正确配置")
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
                    logger.warning("Embedding 鉴权失败(401): 请检查 LLM_API_KEY")
                    self._embedding_warned = True
                self._embedding_key_invalid = True
                return None
            logger.warning(f"Embedding fetch failed: {exc}")
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

    def clear_cache(self, query: Optional[str] = None) -> bool:
        try:
            if query:
                key = self.get_cache_key(query)
                with self._l1_lock:
                    self._l1_cache.pop(key, None)
                if self.redis_client:
                    self.redis_client.delete(key)
            else:
                with self._l1_lock:
                    self._l1_cache.clear()
                if self.redis_client:
                    self.redis_client.flushdb()
            return True
        except Exception as exc:
            logger.error(f"Cache clear failed: {exc}")
            return False
