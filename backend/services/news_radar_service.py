"""科技新闻雷达服务 - Neo4j + 搜索 + LLM 抽取实体图谱"""

from __future__ import annotations

import hashlib
import json
import re
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from email.utils import parsedate_to_datetime
import urllib.request

import httpx

from loguru import logger
from agents.langchain_runtime import LangChainLLM, SimpleLangChainAgent

from config import get_config
from services.neo4j_client import neo4j_client
from tools.search_tools import get_search_tool
from database import get_db_context
from models import UserNewsHistory, UserRadarProfile
from services.news_cache import news_cache, REDIS_AVAILABLE, redis_client


config = get_config()


class NewsRadarService:
    """负责：
    - 拉取科技新闻（Tavily / SERPAPI）
    - 抽取实体与关系，写入 Neo4j
    - 提供热榜、新闻详情 + 图谱数据
    - 按实体组合问题，基于最新新闻做 RAG 分析（MVP 版仅返回新闻摘要 + 结构化回答）
    """

    def __init__(self) -> None:
        self.search_tool = get_search_tool()
        if self.search_tool is None:
            logger.warning("NewsRadarService: 未配置搜索工具，热榜功能将不可用")

        self.llm = LangChainLLM(
            model=config.llm.model_id,
            api_key=config.llm.api_key,
            base_url=config.llm.base_url if config.llm.base_url else None,
            provider=config.llm.provider,
        )
        self.entity_agent = SimpleLangChainAgent(
            name="NewsEntityExtractor",
            llm=self.llm,
            system_prompt=self._entity_system_prompt(),
        )
        self.analysis_agent = SimpleLangChainAgent(
            name="NewsRadarAnalyzer",
            llm=self.llm,
            system_prompt=self._analysis_system_prompt(),
        )
        
        # 时间限流：记录上次搜索时间（key: 查询关键词或'hot', value: datetime）
        self.last_search_time: Dict[str, datetime] = {}
        self.search_interval_hours = 1  # 搜索间隔：1小时

        # 记忆分层：L0(进程内短期) -> L1(Redis短期/画像) -> L2(PG长期/画像)
        self._runtime_short_memory: Dict[str, tuple[float, Dict[str, Any]]] = {}
        self._runtime_lock = threading.Lock()
        self._runtime_short_ttl_seconds = 45 * 60
        self._redis_short_ttl_seconds = 6 * 60 * 60
        self._redis_profile_ttl_seconds = 24 * 60 * 60

    # -------------------- cache helpers --------------------

    @staticmethod
    def _short_hash(value: str) -> str:
        return hashlib.md5((value or "").encode("utf-8")).hexdigest()[:16]

    def _build_radar_cache_key(
        self,
        kind: str,
        news_id: str,
        entities: List[str],
        question: str,
        extra_context: str = "",
    ) -> str:
        # 精准匹配：只使用请求原始参数生成稳定键，不做别名/扩展映射
        exact_entities = "|".join(sorted((x or "").strip() for x in entities if (x or "").strip()))
        material = "\n".join([
            kind,
            news_id or "",
            exact_entities,
            (question or "").strip(),
            (extra_context or "").strip(),
        ])
        return f"{kind}:{self._short_hash(material)}"

    @staticmethod
    def _default_short_memory() -> Dict[str, Any]:
        return {
            "window": [],
            "summary": "",
            "last_topics": [],
            "last_updated": "",
        }

    @staticmethod
    def _default_user_profile() -> Dict[str, Any]:
        return {
            "focus_areas": [],
            "style_preferences": {"response_style": "evidence-first"},
            "entity_interest": {},
            "topic_interest": {},
            "updated_at": "",
        }

    def _memory_slot_key(self, user_id: int, news_id: str) -> str:
        return f"{user_id}:{news_id}"

    def _redis_short_memory_key(self, user_id: int, news_id: str) -> str:
        return f"news:memory:short:{user_id}:{news_id}"

    def _redis_profile_key(self, user_id: int) -> str:
        return f"news:memory:profile:{user_id}"

    def _normalize_short_memory(self, value: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        base = self._default_short_memory()
        if not isinstance(value, dict):
            return base
        window = value.get("window") if isinstance(value.get("window"), list) else []
        norm_window = []
        for item in window[-10:]:
            if not isinstance(item, dict):
                continue
            norm_window.append(
                {
                    "ts": str(item.get("ts") or ""),
                    "type": str(item.get("type") or "analysis"),
                    "question": str(item.get("question") or "")[:300],
                    "answer_highlight": str(item.get("answer_highlight") or "")[:240],
                    "entities": [str(e) for e in (item.get("entities") or []) if str(e).strip()][:8],
                }
            )
        base["window"] = norm_window
        base["summary"] = str(value.get("summary") or "")[:360]
        base["last_topics"] = [str(x) for x in (value.get("last_topics") or []) if str(x).strip()][:12]
        base["last_updated"] = str(value.get("last_updated") or "")
        return base

    def _normalize_user_profile(self, value: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        base = self._default_user_profile()
        if not isinstance(value, dict):
            return base
        base["focus_areas"] = [str(x) for x in (value.get("focus_areas") or []) if str(x).strip()][:25]
        style = value.get("style_preferences") if isinstance(value.get("style_preferences"), dict) else {}
        base["style_preferences"] = {
            "response_style": str(style.get("response_style") or "evidence-first"),
        }
        entity_interest = value.get("entity_interest") if isinstance(value.get("entity_interest"), dict) else {}
        topic_interest = value.get("topic_interest") if isinstance(value.get("topic_interest"), dict) else {}
        base["entity_interest"] = entity_interest
        base["topic_interest"] = topic_interest
        base["updated_at"] = str(value.get("updated_at") or "")
        return base

    def _get_runtime_short_memory(self, user_id: int, news_id: str) -> Optional[Dict[str, Any]]:
        slot = self._memory_slot_key(user_id, news_id)
        now = time.time()
        with self._runtime_lock:
            item = self._runtime_short_memory.get(slot)
            if not item:
                return None
            expires_at, payload = item
            if expires_at < now:
                self._runtime_short_memory.pop(slot, None)
                return None
            return self._normalize_short_memory(payload)

    def _set_runtime_short_memory(self, user_id: int, news_id: str, payload: Dict[str, Any]) -> None:
        slot = self._memory_slot_key(user_id, news_id)
        expires_at = time.time() + self._runtime_short_ttl_seconds
        with self._runtime_lock:
            self._runtime_short_memory[slot] = (expires_at, self._normalize_short_memory(payload))

    def _get_redis_json(self, key: str) -> Optional[Dict[str, Any]]:
        if not REDIS_AVAILABLE or redis_client is None:
            return None
        try:
            raw = redis_client.get(key)
            if not raw:
                return None
            data = json.loads(raw)
            return data if isinstance(data, dict) else None
        except Exception as exc:
            logger.debug(f"[NewsRadarMemory] Redis读取失败 key={key}: {exc}")
            return None

    def _set_redis_json(self, key: str, payload: Dict[str, Any], ttl_seconds: int) -> None:
        if not REDIS_AVAILABLE or redis_client is None:
            return
        try:
            redis_client.setex(key, max(1, int(ttl_seconds)), json.dumps(payload, ensure_ascii=False))
        except Exception as exc:
            logger.debug(f"[NewsRadarMemory] Redis写入失败 key={key}: {exc}")

    def _load_layered_short_memory(self, user_id: int, news_id: str, notes: Dict[str, Any]) -> Dict[str, Any]:
        runtime = self._get_runtime_short_memory(user_id, news_id)
        if runtime:
            return runtime
        redis_data = self._get_redis_json(self._redis_short_memory_key(user_id, news_id))
        if redis_data:
            short_memory = self._normalize_short_memory(redis_data)
            self._set_runtime_short_memory(user_id, news_id, short_memory)
            return short_memory
        fallback = self._normalize_short_memory(notes.get("short_term_memory") or {})
        self._set_runtime_short_memory(user_id, news_id, fallback)
        self._set_redis_json(self._redis_short_memory_key(user_id, news_id), fallback, self._redis_short_ttl_seconds)
        return fallback

    def _persist_layered_short_memory(self, user_id: int, news_id: str, short_memory: Dict[str, Any]) -> None:
        norm = self._normalize_short_memory(short_memory)
        self._set_runtime_short_memory(user_id, news_id, norm)
        self._set_redis_json(self._redis_short_memory_key(user_id, news_id), norm, self._redis_short_ttl_seconds)

    def _load_user_profile(self, user_id: int) -> Dict[str, Any]:
        redis_key = self._redis_profile_key(user_id)
        redis_profile = self._get_redis_json(redis_key)
        if redis_profile:
            return self._normalize_user_profile(redis_profile)

        with get_db_context() as db:
            row = db.query(UserRadarProfile).filter(UserRadarProfile.user_id == user_id).first()
            if not row or not row.profile_json:
                profile = self._default_user_profile()
            else:
                try:
                    profile = self._normalize_user_profile(json.loads(row.profile_json))
                except Exception:
                    profile = self._default_user_profile()

        self._set_redis_json(redis_key, profile, self._redis_profile_ttl_seconds)
        return profile

    def _save_user_profile(self, user_id: int, profile: Dict[str, Any]) -> None:
        norm = self._normalize_user_profile(profile)
        self._set_redis_json(self._redis_profile_key(user_id), norm, self._redis_profile_ttl_seconds)
        with get_db_context() as db:
            row = db.query(UserRadarProfile).filter(UserRadarProfile.user_id == user_id).first()
            if not row:
                row = UserRadarProfile(user_id=user_id, profile_json=json.dumps(norm, ensure_ascii=False))
                db.add(row)
            else:
                row.profile_json = json.dumps(norm, ensure_ascii=False)
            db.commit()

    def _update_user_profile_from_interaction(
        self,
        user_id: int,
        entities: List[str],
        question: str,
    ) -> Dict[str, Any]:
        profile = self._load_user_profile(user_id)
        ts = datetime.utcnow().isoformat()
        focus_areas = profile.setdefault("focus_areas", [])
        entity_interest = profile.setdefault("entity_interest", {})
        topic_interest = profile.setdefault("topic_interest", {})

        for entity in [e for e in entities if e][:8]:
            if entity not in focus_areas:
                focus_areas.append(entity)
            info = entity_interest.get(entity) or {"count": 0, "last_seen": ts}
            info["count"] = int(info.get("count") or 0) + 1
            info["last_seen"] = ts
            entity_interest[entity] = info

        for keyword in ["风险", "机会", "竞争", "合作", "投资", "并购", "产品", "技术"]:
            if keyword in (question or ""):
                score = int(topic_interest.get(keyword) or 0) + 1
                topic_interest[keyword] = score

        profile["focus_areas"] = focus_areas[-25:]
        profile["updated_at"] = ts
        self._save_user_profile(user_id=user_id, profile=profile)
        return profile

    # -------------------- public API --------------------

    async def get_hot_news(self, limit: int = 20, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """从搜索工具获取最新科技新闻（优先真实搜索，而非仅依赖 Neo4j）。
        
        Args:
            limit: 返回新闻数量
            force_refresh: 强制刷新，跳过缓存直接搜索最新新闻
        """
        # 强制刷新：直接搜索最新新闻
        if force_refresh:
            logger.info("[NewsRadar] 强制刷新热榜，开始搜索最新科技新闻")
            await self.refresh_hot_news(limit=limit)
            news_cache.invalidate_hot_news()
        
        # 尝试从缓存获取
        cached_news = news_cache.get_hot_news()
        if cached_news and len(cached_news) >= max(5, limit // 2) and not force_refresh:
            logger.info(f"[NewsRadar] 从缓存返回热榜: {len(cached_news)} 条")
            return cached_news[:limit]
        
        try:
            records = neo4j_client.run_query(
                """
                MATCH (n:News)
                WHERE n.is_search_archive IS NULL OR n.is_search_archive = false
                RETURN n
                ORDER BY n.created_at DESC
                LIMIT $limit
                """,
                {"limit": limit},
            )
            items = [self._serialize_news_record(r["n"]) for r in records]
            
            # ⚠️ 注意：不要在这里重复翻译！翻译应该在入库时只做一次
            # 直接返回已翻译的数据

            # 日志：如果新闻不足，提示需要显式刷新（不再自动搜索，以避免每次访问都卡顿）
            if len(items) < 5 and self.search_tool:
                logger.info(f"[NewsRadar] 热榜新闻不足（仅{len(items)}条），建议通过 force_refresh=True 手动刷新")
            
            # 缓存结果
            if items:
                news_cache.set_hot_news(items)
            return items
            
        except Exception as e:
            logger.error(f"[NewsRadar] 获取热榜失败: {e}", exc_info=True)
            # 返回空列表或缓存数据（如果有）
            return cached_news[:limit] if cached_news else []

    async def refresh_hot_news(self, limit: int = 20) -> None:
        """调用外部搜索，抓取一批最新科技新闻并入图。
        
        使用多个科技关键词搜索，确保获取真实最新的科技新闻。
        """
        if not self.search_tool:
            logger.warning("NewsRadarService.refresh_hot_news: 无可用搜索工具，跳过")
            return

        # 检查时间限制（热榜刷新每1小时只进行一次真实搜索）
        if not self._should_search("hot_news"):
            logger.info("[NewsRadar] 热榜刷新冷却中，跳过此次搜索")
            return

        try:
            # 覆盖不同科技赛道，且强调时效性（latest/today/breaking）
            search_queries = [
                "latest AI robotics semiconductor cloud cybersecurity biotech EV quantum tech news today",
                "今日 科技 新闻 半导体 云计算 网络安全 新能源汽车 生物科技",
                "breaking technology startup funding IPO M&A chip data center edge computing news",
                "consumer electronics smartphone AR VR gaming platform tech launch this week",
            ]

            all_results: List[Dict[str, Any]] = []
            for query in search_queries:
                try:
                    results = await self.search_tool.search(query, max_results=max(12, limit))
                    all_results.extend(results)
                    logger.info(f"[NewsRadar] 搜索'{query[:40]}...'获取 {len(results)} 条新闻")
                except Exception as e:
                    logger.warning(f"[NewsRadar] 搜索'{query[:30]}...'失败: {e}")

            # 去重（基于URL）
            seen_urls = set()
            unique_results: List[Dict[str, Any]] = []
            for item in all_results:
                url = (item.get("url") or "").strip()
                if not url:
                    continue
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                unique_results.append(item)

            logger.info(f"[NewsRadar] 去重后共 {len(unique_results)} 条候选新闻")

            # 外部搜索异常时，兜底抓取 RSS 最新科技新闻
            if not unique_results:
                rss_results = await self._fetch_latest_tech_rss(max_items=max(30, limit * 2))
                unique_results = rss_results
                logger.info(f"[NewsRadar] 搜索接口无结果，使用 RSS 兜底: {len(unique_results)} 条")

            # 按时间顺序分组生成“事件追踪稿”，避免赛道式总分门类
            digests: List[Dict[str, Any]] = []
            group_size = 5
            max_input = min(len(unique_results), max(limit * group_size, group_size))
            for idx in range(0, max_input, group_size):
                chunk = unique_results[idx: idx + group_size]
                if not chunk:
                    continue
                label = self._make_digest_label(chunk)
                digest = await self._build_topic_digest(label, chunk)
                if digest:
                    digests.append(digest)

            # 按来源文章数量排序，最多入库 limit 条主题摘要
            digests.sort(key=lambda d: d.get("source_count", 0), reverse=True)
            for digest in digests[:limit]:
                try:
                    await self._upsert_news_with_entities(digest)
                except Exception as exc:
                    logger.warning(f"[NewsRadar] 主题摘要入库失败: {exc}")
            
            # 记录本次搜索时间
            self._record_search("hot_news")
            
            # 清除热榜缓存，下次查询会重新加载
            news_cache.invalidate_hot_news()
            logger.info(f"[NewsRadar] 热榜刷新完成，已清除缓存")
            
        except Exception as e:
            logger.error(f"[NewsRadar] 刷新热榜失败: {e}", exc_info=True)

    async def delete_news(self, news_id: str) -> bool:
        """删除新闻节点及其关联关系。
        
        Args:
            news_id: 新闻ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            # 删除新闻节点及其所有关联关系
            result = neo4j_client.run_query(
                """
                MATCH (n:News {id: $id})
                DETACH DELETE n
                RETURN count(n) as deleted_count
                """,
                {"id": news_id},
                read_only=False,
            )
            
            # 清除相关缓存
            news_cache.invalidate_hot_news()
            news_cache.invalidate_news_detail(news_id)
            
            deleted_count = result[0]["deleted_count"] if result else 0
            
            if deleted_count > 0:
                logger.info(f"[NewsRadar] 成功删除新闻: {news_id}")
                
                # 同时删除 PostgreSQL 中的用户查看历史
                with get_db_context() as db:
                    db.query(UserNewsHistory).filter(
                        UserNewsHistory.news_id == news_id
                    ).delete()
                    db.commit()
                    
                return True
            else:
                logger.warning(f"[NewsRadar] 新闻不存在: {news_id}")
                return False
                
        except Exception as e:
            logger.error(f"[NewsRadar] 删除新闻失败: {e}", exc_info=True)
            raise

    async def delete_all_news(self) -> Dict[str, int]:
        """清空所有新闻及图谱关系（用于重新构建最新热榜）。"""
        try:
            news_count_result = neo4j_client.run_query(
                """
                MATCH (n:News)
                RETURN count(n) AS total
                """,
                {},
            )
            total_news = int(news_count_result[0].get("total", 0)) if news_count_result else 0

            neo4j_client.run_query(
                """
                MATCH (n:News)
                DETACH DELETE n
                """,
                {},
                read_only=False,
            )

            # 清理孤立实体（没有任何关系）
            neo4j_client.run_query(
                """
                MATCH (e:Entity)
                WHERE NOT (e)--()
                DELETE e
                """,
                {},
                read_only=False,
            )

            with get_db_context() as db:
                db.query(UserNewsHistory).delete()
                db.commit()

            news_cache.invalidate_hot_news()
            logger.info(f"[NewsRadar] 已清空全部新闻数据: {total_news} 条")
            return {"deleted_news": total_news}
        except Exception as e:
            logger.error(f"[NewsRadar] 清空新闻失败: {e}", exc_info=True)
            raise

    async def fetch_and_ingest_news(self, query: str, max_items: int = 10) -> Dict[str, Any]:
        """搜索特定主题的新闻并入库。"""
        if not self.search_tool:
            logger.warning("NewsRadarService.fetch_and_ingest_news: 无可用搜索工具")
            return {"count": 0, "entities_count": 0}

        results = await self.search_tool.search(query, max_results=max_items)
        logger.info(f"[NewsRadar] 搜索'{query}'获取 {len(results)} 条新闻")

        count = 0
        entities_count = 0
        
        for item in results:
            try:
                await self._upsert_news_with_entities(item)
                count += 1
            except Exception as exc:
                logger.warning(f"[NewsRadar] 处理新闻失败: {exc}")

        return {"count": count, "entities_count": entities_count}

    async def get_search_archives(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取所有搜索档案（用户搜索过的主题）。
        
        Args:
            limit: 返回档案数量
            
        Returns:
            搜索档案列表，按创建时间倒序
        """
        try:
            records = neo4j_client.run_query(
                """
                MATCH (n:News)
                WHERE n.is_search_archive = true AND n.search_topic IS NOT NULL
                RETURN n
                ORDER BY n.created_at DESC
                LIMIT $limit
                """,
                {"limit": limit},
            )
            
            items = []
            for r in records:
                news_data = self._serialize_news_record(r["n"])
                # 添加搜索主题字段
                search_topic = r["n"].get("search_topic", "")
                if search_topic:
                    news_data["search_topic"] = search_topic
                items.append(news_data)
            
            logger.info(f"[NewsRadar] 返回 {len(items)} 个搜索档案")
            return items
            
        except Exception as e:
            logger.error(f"[NewsRadar] 获取搜索档案失败: {e}", exc_info=True)
            return []

    async def get_news_detail(self, news_id: str) -> Optional[Dict[str, Any]]:
        """返回新闻文本 + 增强的图数据（实体节点、关系、重要性得分等）。"""
        records = neo4j_client.run_query(
            """
            MATCH (n:News {id: $id})
            OPTIONAL MATCH (n)-[r:MENTIONS]->(e:Entity)
            RETURN n, 
                   collect(DISTINCT {id: e.id, name: e.name, type: e.type, importance: e.importance}) AS entities
            """,
            {"id": news_id},
        )
        if not records:
            return None

        rec = records[0]
        news = self._serialize_news_record(rec["n"])
        entities_raw = rec.get("entities") or []

        nodes = []
        node_ids = set()
        entity_names = []
        entity_importance = {}
        
        for e in entities_raw:
            if e is None or not e.get("id"):
                continue
            node_id = e.get("id")
            if node_id in node_ids:
                continue
            node_ids.add(node_id)
            
            # 计算节点大小和重要性（基于 importance 字段）
            importance_score = max(0.5, min(2.0, (e.get("importance") or 50) / 50.0))
            entity_importance[e.get("name")] = importance_score
            
            # 根据实体类型设置颜色
            entity_type = e.get("type", "Entity").lower()
            type_colors = {
                "company": "#FF6B6B",      # 红色
                "person": "#4ECDC4",       # 青色
                "product": "#45B7D1",      # 蓝色
                "technology": "#96CEB4",   # 绿色
                "event": "#FFEAA7",        # 黄色
                "location": "#DDA15E",     # 棕色
            }
            node_color = type_colors.get(entity_type, "#95E1D3")
            
            nodes.append(
                {
                    "id": node_id,
                    "name": e.get("name"),
                    "type": e.get("type", "Entity"),
                    "importance": importance_score,
                    "size": max(20, min(60, 20 + importance_score * 15)),  # 节点大小范围 20-60
                    "color": node_color,
                }
            )
            entity_names.append(e.get("name"))

        edges = []
        
        if entity_names:
            # 查询实体之间的关系及其强度
            entity_relations = neo4j_client.run_query(
                """
                MATCH (e1:Entity)-[r:RELATES_TO]->(e2:Entity)
                WHERE e1.name IN $names AND e2.name IN $names
                RETURN e1.id as from_id, e2.id as to_id, e1.name as from_name, 
                       e2.name as to_name, r.type as rel_type, 
                       r.strength as strength, r.context as context
                """,
                {"names": entity_names},
            )
            
            # 统计实体间关系的频次以确定边的强度
            relation_strengths = {}
            for rel in entity_relations:
                rel_key = (rel["from_id"], rel["to_id"])
                raw_strength = rel.get("strength", 1)
                try:
                    rel_strength = int(raw_strength) if raw_strength is not None else 1
                except Exception:
                    rel_strength = 1
                rel_strength = max(1, min(5, rel_strength))  # 强度 1-5
                relation_strengths[rel_key] = rel_strength
                
                edges.append(
                    {
                        "source": rel["from_id"],
                        "target": rel["to_id"],
                        "type": rel["rel_type"] or "related",
                        "strength": rel_strength,
                        "context": rel.get("context", ""),
                        "width": 1 + (rel_strength - 1) * 0.5,  # 边宽度 1-3
                    }
                )
            
            # 如果关系数量较少，尝试查找二阶关系（间接相连）
            if len(edges) < len(entity_names) and len(entity_names) > 1:
                indirect_relations = neo4j_client.run_query(
                    """
                    MATCH (e1:Entity)-[r1:RELATES_TO]-(e_mid:Entity)-[r2:RELATES_TO]-(e2:Entity)
                    WHERE e1.name IN $names AND e2.name IN $names AND e1 <> e2
                    RETURN DISTINCT e1.id as from_id, e2.id as to_id, e1.name as from_name, 
                           e2.name as to_name
                    LIMIT 10
                    """,
                    {"names": entity_names},
                )
                
                for rel in indirect_relations:
                    rel_key = (rel["from_id"], rel["to_id"])
                    # 避免重复添加
                    if not any(e["source"] == rel["from_id"] and e["target"] == rel["to_id"] for e in edges):
                        edges.append(
                            {
                                "source": rel["from_id"],
                                "target": rel["to_id"],
                                "type": "indirect",
                                "strength": 2,
                                "context": f"{rel['from_name']} 通过其他实体与 {rel['to_name']} 相关",
                                "width": 1.5,
                                "dashed": True,  # 虚线表示间接关系
                            }
                        )

        return {
            "news": news,
            "graph": {
                "nodes": nodes,
                "edges": edges,
                "metadata": {
                    "total_entities": len(nodes),
                    "total_relations": len(edges),
                    "graph_layout": "force-directed",  # 前端可使用力导向布局
                }
            },
        }

    async def analyze_entities(
        self,
        entity_names: List[str],
        user_question: Optional[str] = None,
        news_id: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """按图索骥：每次同时结合本地图谱和互联网新闻做综合分析。"""
        if not entity_names:
            raise ValueError("至少需要一个实体名称")

        question = user_question or "请综合分析这些实体在最近科技新闻中的最新动向、合作与竞争格局。"
        notes: Optional[Dict[str, Any]] = None
        memory_context = {"short_text": "- 无短期记忆", "long_text": "- 无长期记忆", "digest": ""}
        profile_context: Optional[Dict[str, Any]] = None
        if user_id and news_id:
            with get_db_context() as db:
                history = db.query(UserNewsHistory).filter(
                    UserNewsHistory.user_id == user_id,
                    UserNewsHistory.news_id == news_id,
                ).first()
                notes = self._parse_history_notes(history.notes if history else None)
            layered_short = self._load_layered_short_memory(user_id=user_id, news_id=news_id, notes=notes)
            notes["short_term_memory"] = layered_short
            profile_context = self._load_user_profile(user_id)
            memory_context = self._build_memory_context(notes, profile=profile_context)

        cache_key = self._build_radar_cache_key(
            kind="analyze",
            news_id=news_id or "",
            entities=entity_names,
            question=question,
            extra_context=memory_context.get("digest", ""),
        )
        cached = news_cache.get_entity_analysis(cache_key)
        if cached:
            logger.info(f"[NewsRadar] 按图索骥 Redis缓存命中 key={cache_key}")
            cached["cache_hit"] = True
            cached["cache_source"] = "news:l2_or_l1"
            if user_id and news_id:
                self.record_news_analysis(
                    user_id=user_id,
                    news_id=news_id,
                    entities=cached.get("entities") or entity_names,
                    question=cached.get("question") or question,
                    answer=cached.get("answer") or "",
                    local_news_count=int(cached.get("local_news_count") or 0),
                    web_news_count=int(cached.get("web_news_count") or 0),
                )
            return cached

        records = neo4j_client.run_query(
            """
            MATCH (e:Entity)<-[:MENTIONS]-(n:News)
            WHERE e.name IN $names
            WITH n, collect(DISTINCT e.name) AS matched_entities
            ORDER BY size(matched_entities) DESC, n.created_at DESC
            LIMIT 12
            RETURN n, matched_entities
            """,
            {"names": entity_names},
        )

        local_news_items: List[Dict[str, Any]] = []
        for r in records:
            n = self._serialize_news_record(r["n"])
            n["matched_entities"] = r.get("matched_entities", [])
            n["source_channel"] = "neo4j"
            local_news_items.append(n)

        web_news_items: List[Dict[str, Any]] = []
        web_query = " ".join(entity_names[:4])

        if self.search_tool:
            try:
                web_results = await self.search_tool.search(web_query, max_results=8, days=7, topic="news")
                for item in web_results:
                    mapped = {
                        "id": self._make_news_id((item.get("url") or item.get("title") or str(item)).strip()),
                        "title": (item.get("title") or "").strip(),
                        "url": (item.get("url") or "").strip(),
                        "snippet": (item.get("snippet") or "").strip(),
                        "content": (item.get("raw_content") or item.get("snippet") or "").strip(),
                        "source": item.get("source") or "web_search",
                        "matched_entities": entity_names,
                        "source_channel": "web",
                    }
                    if mapped["title"]:
                        web_news_items.append(mapped)
                logger.info(f"[NewsRadar] 按图索骥：web搜索返回 {len(web_news_items)} 条")
            except Exception as e:
                logger.warning(f"[NewsRadar] 按图索骥 web 搜索失败: {e}")

        merged: List[Dict[str, Any]] = []
        seen = set()
        for item in local_news_items + web_news_items:
            dedupe_key = (item.get("url") or item.get("title") or "").strip().lower()
            if not dedupe_key or dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            merged.append(item)

        news_items = merged[:12]

        # 将检索到的新闻入库为搜索档案，便于在档案列表中展示（防止匿名用户也可通过全局档案查看）
        try:
            search_topic = "、".join(entity_names[:4])
            for item in news_items:
                try:
                    upsert_item = dict(item)
                    upsert_item["is_search_archive"] = True
                    upsert_item["search_topic"] = search_topic
                    # 保留 source_urls 如果存在
                    await self._upsert_news_with_entities(upsert_item)
                except Exception as e:
                    logger.warning(f"[NewsRadar] 将检索到的新闻入库失败: {e}")
        except Exception:
            logger.exception("[NewsRadar] 在入库搜索档案环节发生异常")

        if not news_items:
            context = "本地图谱和互联网搜索都未检索到可用新闻。"
        else:
            pieces = []
            for idx, item in enumerate(news_items, start=1):
                pieces.append(
                    f"[新闻{idx}] 渠道:{item.get('source_channel', 'unknown')}\n标题:{item.get('title','')}\nURL:{item.get('url','')}\n摘要:{item.get('snippet','')}\n"
                )
            context = "\n\n".join(pieces)

        prompt = (
            f"用户关注的实体：{', '.join(entity_names)}\n\n"
            f"短期记忆（最近交互）：\n{memory_context['short_text']}\n\n"
            f"长期记忆（稳定偏好/历史结论）：\n{memory_context['long_text']}\n\n"
            f"相关新闻（按时间与相关度排序）：\n{context}\n\n"
            f"用户问题：{question}\n\n"
            "请按照系统指令返回结构化分析。"
        )

        answer = self.analysis_agent.run(prompt)

        if user_id and news_id:
            self.record_news_analysis(
                user_id=user_id,
                news_id=news_id,
                entities=entity_names,
                question=question,
                answer=answer,
                local_news_count=len(local_news_items),
                web_news_count=len(web_news_items),
            )

        result = {
            "question": question,
            "entities": entity_names,
            "news_count": len(news_items),
            "news": news_items,
            "local_news_count": len(local_news_items),
            "web_news_count": len(web_news_items),
            "answer": answer,
            "memory_used": bool(memory_context.get("digest")),
            "cache_hit": False,
            "cache_source": None,
        }
        news_cache.set_entity_analysis(cache_key, result)
        return result

    # -------------------- internal helpers --------------------

    async def _upsert_news_with_entities(self, item: Dict[str, Any]) -> None:
        """将一条搜索结果入库，并抽取实体关系写入 Neo4j。"""
        title = (item.get("title") or "").strip()
        url = (item.get("url") or "").strip()
        snippet = (item.get("snippet") or "").strip()
        raw_content = (item.get("raw_content") or snippet or "").strip()
        source = item.get("source") or "search"
        search_topic = item.get("search_topic")  # 搜索关键词（如果是搜索档案）
        is_search_archive = item.get("is_search_archive", False)  # 是否为搜索档案
        source_urls = item.get("source_urls", [])  # 原始新闻链接列表（用于档案详情页展示）

        if not title or not url:
            return

        news_id = self._make_news_id(url)

        logger.info(f"[NewsRadar] upsert news id={news_id} title={title[:40]}... search_archive={is_search_archive}")

        # 序列化source_urls为JSON字符串
        import json
        source_urls_json = json.dumps(source_urls, ensure_ascii=False) if source_urls else "[]"
        logger.debug(f"[NewsRadar] 保存source_urls：{len(source_urls)}条链接 -> {source_urls_json[:100]}...")

        # 1) 先写 News 节点（如果是搜索档案，保存search_topic）
        if is_search_archive and search_topic:
            neo4j_client.run_query(
                """
                MERGE (n:News {id: $id})
                SET n.title = $title,
                    n.url = $url,
                    n.snippet = $snippet,
                    n.content = $content,
                    n.source = $source,
                                        n.source_urls = $source_urls,
                    n.search_topic = $search_topic,
                    n.is_search_archive = true,
                    n.source_urls = $source_urls,
                    n.created_at = coalesce(n.created_at, datetime($created_at))
                """,
                {
                    "id": news_id,
                    "title": title,
                    "url": url,
                    "snippet": snippet,
                    "content": raw_content[:4000],
                    "source": source,
                                        "source_urls": source_urls_json,
                    "search_topic": search_topic,
                    "source_urls": source_urls_json,
                    "created_at": datetime.utcnow().isoformat(),
                },
                read_only=False,
            )
        else:
            neo4j_client.run_query(
                """
                MERGE (n:News {id: $id})
                SET n.title = $title,
                    n.url = $url,
                    n.snippet = $snippet,
                    n.content = $content,
                    n.source = $source,
                    n.source_urls = $source_urls,
                    n.created_at = coalesce(n.created_at, datetime($created_at))
                """,
                {
                    "id": news_id,
                    "title": title,
                    "url": url,
                    "snippet": snippet,
                    "content": raw_content[:4000],
                    "source": source,
                    "source_urls": source_urls_json,
                    "created_at": datetime.utcnow().isoformat(),
                },
                read_only=False,
            )

        # 2) 抽取实体并写 Entity / MENTIONS 关系
        if not raw_content:
            logger.info(f"[NewsRadar] 新闻缺少正文内容，跳过实体抽取: {url}")
            return

        extraction_result = await self._extract_entities(raw_content, title=title)
        entities = extraction_result.get("entities", [])
        relationships = extraction_result.get("relationships", [])
        
        if not entities:
            logger.info(f"[NewsRadar] 未从新闻中抽取到实体: {url}")
            return

        # 存储实体并创建 News->MENTIONS->Entity 关系
        entity_map: Dict[str, str] = {}  # 原始名/归一化名 -> entity_id
        for ent in entities:
            name = ent.get("name")
            etype = ent.get("type") or "entity"
            salience = float(ent.get("salience", 0.5))
            if not name:
                continue

            entity_id = self._make_entity_id(name, etype)
            entity_map[name] = entity_id
            entity_map[self._normalize_entity_name(name)] = entity_id
            
            neo4j_client.run_query(
                """
                MERGE (e:Entity {id: $eid})
                SET e.name = $name,
                    e.type = $type,
                    e.importance = coalesce(e.importance, 50) + $salience * 10
                WITH e
                MATCH (n:News {id: $nid})
                MERGE (n)-[r:MENTIONS]->(e)
                SET r.salience = $salience
                """,
                {
                    "eid": entity_id,
                    "nid": news_id,
                    "name": name,
                    "type": etype,
                    "salience": salience,
                },
                read_only=False,
            )
        
        # 创建实体之间的 RELATES_TO 关系
        for rel in relationships:
            from_name = rel.get("from")
            to_name = rel.get("to")
            rel_type = self._normalize_relation_type(rel.get("type", "related"))
            strength = max(1, min(5, int(rel.get("strength", 3))))
            
            if not from_name or not to_name:
                continue
            
            from_id = self._resolve_entity_id(from_name, entity_map)
            to_id = self._resolve_entity_id(to_name, entity_map)
            
            if not from_id or not to_id or from_id == to_id:
                continue
            
            neo4j_client.run_query(
                """
                MATCH (e1:Entity {id: $from_id})
                MATCH (e2:Entity {id: $to_id})
                MERGE (e1)-[r:RELATES_TO]->(e2)
                SET r.type = $rel_type,
                    r.strength = $strength,
                    r.context = $context
                """,
                {
                    "from_id": from_id,
                    "to_id": to_id,
                    "rel_type": rel_type,
                    "strength": strength,
                    "context": f"在新闻《{title[:50]}...》中提到的关系"
                },
                read_only=False,
            )

    async def _extract_entities(self, text: str, title: str = "") -> Dict[str, Any]:
        """使用 LLM 从新闻正文中抽取实体列表和实体间关系。"""
        snippet = text[:2000]
        prompt = (
            f"新闻标题：{title}\n\n"
            f"新闻正文片段（可能被截断）：\n{snippet}\n\n"
            "请分析新闻内容，找出核心实体和它们之间的关系。\n\n"
            "返回 JSON 格式，包含两个字段：\n"
            "1. entities: 实体数组，每个实体包含：\n"
            "   - name: 实体名称\n"
            "   - type: 实体类型（company/person/product/technology/location/event）\n"
            "   - salience: 该实体在新闻中的重要程度（0-1之间的小数）\n"
            "2. relationships: 关系数组，每个关系包含：\n"
            "   - from: 源实体名称\n"
            "   - to: 目标实体名称\n"
            "   - type: 关系类型（belongs_to/subsidiary_of/develops/competes_with/partners_with/owns/invests_in/uses/located_in/related）\n"
            "   - strength: 关系强度（1-5的整数）\n\n"
            "关系方向要求：若是隶属/从属关系，必须从子实体指向母实体。\n"
            "例如：通义实验室 -> 阿里云（belongs_to），阿里云 -> 阿里（subsidiary_of）。\n\n"
            "示例：\n"
            '{"entities": [{"name": "OpenAI", "type": "company", "salience": 0.9}, {"name": "GPT-4", "type": "product", "salience": 0.8}], '
            '"relationships": [{"from": "OpenAI", "to": "GPT-4", "type": "develops", "strength": 5}]}\n\n'
            "只返回 JSON，不要其他文字。"
        )

        try:
            raw = self.entity_agent.run(prompt)
            import json

            # 兼容带 ```json 包裹的情况
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()

            data = json.loads(raw)
            if not isinstance(data, dict):
                return {"entities": [], "relationships": []}
            
            entities = data.get("entities", [])
            relationships = data.get("relationships", [])
            
            # 为每个实体附加关系信息
            return {"entities": entities if isinstance(entities, list) else [], 
                    "relationships": relationships if isinstance(relationships, list) else []}
        except Exception as exc:
            logger.warning(f"[NewsRadar] 实体抽取失败: {exc}")
            return self._extract_entities_fallback(text=text, title=title)

    def _extract_entities_fallback(self, text: str, title: str = "") -> Dict[str, Any]:
        """当 LLM 不可用时的规则兜底抽取，保证图谱至少有可视化关系。"""
        corpus = f"{title}\n{text}"
        lower = corpus.lower()

        # 常见科技实体字典（可持续扩展）
        seed_entities = {
            "OpenAI": "company",
            "Google": "company",
            "Alphabet": "company",
            "Microsoft": "company",
            "Meta": "company",
            "Apple": "company",
            "Amazon": "company",
            "AWS": "company",
            "NVIDIA": "company",
            "TSMC": "company",
            "Tesla": "company",
            "Intel": "company",
            "AMD": "company",
            "Qualcomm": "company",
            "Anthropic": "company",
            "xAI": "company",
            "阿里": "company",
            "阿里云": "company",
            "通义": "product",
            "通义千问": "product",
            "通义实验室": "company",
            "Qwen": "product",
            "Qwen团队": "company",
            "林俊旸": "person",
            "郁博文": "person",
            "惠彬原": "person",
            "周浩": "person",
            "周靖人": "person",
            "Meta": "company",
            "字节": "company",
            "DeepMind": "company",
        }

        counts: Dict[str, int] = {}
        types: Dict[str, str] = {}

        for name, etype in seed_entities.items():
            c = lower.count(name.lower())
            if c > 0:
                counts[name] = c
                types[name] = etype

        # 从标题中补充专有名词（大写开头词）
        for token in re.findall(r"\b[A-Z][A-Za-z0-9\-\.]{2,24}\b", corpus):
            if token.lower() in {"the", "and", "for", "with", "from", "this", "that"}:
                continue
            counts[token] = counts.get(token, 0) + 1
            types.setdefault(token, "other")

        if not counts:
            return {"entities": [], "relationships": []}

        # 选取最重要实体
        sorted_entities = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:8]
        max_count = max(v for _, v in sorted_entities) if sorted_entities else 1
        entities = [
            {
                "name": name,
                "type": types.get(name, "other"),
                "salience": round(min(1.0, 0.35 + (cnt / max_count) * 0.65), 3),
            }
            for name, cnt in sorted_entities
        ]

        names = [e["name"] for e in entities]
        relationships: List[Dict[str, Any]] = []

        # 基于关键词推断关系
        rel_type = "related"
        strength = 2
        if re.search(r"acquire|acquisition|buy|merger|收购|并购", lower):
            rel_type, strength = "owns", 4
        elif re.search(r"partner|collaborat|alliance|合作|联合", lower):
            rel_type, strength = "partners_with", 4
        elif re.search(r"develop|launch|release|推出|发布", lower):
            rel_type, strength = "develops", 3
        elif re.search(r"subsidiary|belongs to|affiliated|隶属|旗下", lower):
            rel_type, strength = "belongs_to", 4

        # 先尝试抽取明确的中文关系句式（隶属/离职/加入/汇报）
        relation_patterns = [
            (r"([\u4e00-\u9fa5A-Za-z0-9·\-]{2,24})团队隶属于([\u4e00-\u9fa5A-Za-z0-9·\-]{2,24})", "belongs_to", 5),
            (r"([\u4e00-\u9fa5A-Za-z0-9·\-]{2,24})隶属于([\u4e00-\u9fa5A-Za-z0-9·\-]{2,24})", "belongs_to", 5),
            (r"([\u4e00-\u9fa5A-Za-z0-9·\-]{2,24})离职.*加入([\u4e00-\u9fa5A-Za-z0-9·\-]{2,24})", "moved_to", 4),
            (r"([\u4e00-\u9fa5A-Za-z0-9·\-]{2,24})从([\u4e00-\u9fa5A-Za-z0-9·\-]{2,24})离职", "resigned_from", 4),
            (r"([\u4e00-\u9fa5A-Za-z0-9·\-]{2,24})加入([\u4e00-\u9fa5A-Za-z0-9·\-]{2,24})", "joins", 3),
            (r"([\u4e00-\u9fa5A-Za-z0-9·\-]{2,24})向([\u4e00-\u9fa5A-Za-z0-9·\-]{2,24})汇报", "reports_to", 4),
            (r"([\u4e00-\u9fa5A-Za-z0-9·\-]{2,24})负责([\u4e00-\u9fa5A-Za-z0-9·\-]{2,24})", "leads", 3),
            (r"([\u4e00-\u9fa5A-Za-z0-9·\-]{2,24})接任([\u4e00-\u9fa5A-Za-z0-9·\-]{2,24})", "succeeds", 4),
        ]

        for pattern, p_type, p_strength in relation_patterns:
            for m in re.finditer(pattern, corpus):
                src = (m.group(1) or "").strip()
                dst = (m.group(2) or "").strip()
                if not src or not dst or src == dst:
                    continue
                relationships.append(
                    {
                        "from": src,
                        "to": dst,
                        "type": p_type,
                        "strength": p_strength,
                    }
                )

        # 若未抽到明确关系，至少连成链，避免“孤立球”
        if not relationships:
            for i in range(len(names) - 1):
                relationships.append(
                    {
                        "from": names[i],
                        "to": names[i + 1],
                        "type": rel_type,
                        "strength": strength,
                    }
                )

        return {"entities": entities, "relationships": relationships}

    @staticmethod
    def _normalize_entity_name(name: str) -> str:
        """将实体名标准化，便于关系对齐。"""
        normalized = re.sub(r"[\s\-—·()（）\[\]【】,，.:：]", "", (name or "").strip().lower())
        alias_map = {
            "alibaba": "阿里",
            "阿里巴巴": "阿里",
            "aliyun": "阿里云",
            "tongyi": "通义",
            "tongyilab": "通义实验室",
            "qwen": "通义千问",
        }
        return alias_map.get(normalized, normalized)

    def _resolve_entity_id(self, entity_name: str, entity_map: Dict[str, str]) -> Optional[str]:
        """在实体映射中容错匹配关系中的实体名称。"""
        if entity_name in entity_map:
            return entity_map[entity_name]

        normalized = self._normalize_entity_name(entity_name)
        if normalized in entity_map:
            return entity_map[normalized]

        for key, value in entity_map.items():
            if normalized and (normalized in key or key in normalized):
                return value
        return None

    @staticmethod
    def _normalize_relation_type(rel_type: str) -> str:
        """统一关系类型，避免同义词导致前端无法识别。"""
        t = (rel_type or "related").strip().lower()
        mapping = {
            "belongsto": "belongs_to",
            "belongs_to": "belongs_to",
            "affiliated_with": "belongs_to",
            "part_of": "belongs_to",
            "subsidiary_of": "subsidiary_of",
            "owned_by": "subsidiary_of",
            "owns": "owns",
            "developed_by": "develops",
            "develops": "develops",
        }
        return mapping.get(t, t)

    @staticmethod
    def _serialize_news_record(node: Any) -> Dict[str, Any]:
        props = dict(node)
        # 将 Neo4j 的 datetime 转为 ISO 字符串
        created_at = props.get("created_at")
        if hasattr(created_at, "isoformat"):
            props["created_at"] = created_at.isoformat()
        
        # 反序列化source_urls（JSON字符串 -> 列表）
        source_urls = []
        source_urls_str = props.get("source_urls")
        if source_urls_str:
            try:
                import json
                source_urls = json.loads(source_urls_str)
                logger.debug(f"[NewsRadar] 反序列化source_urls：{len(source_urls)}条链接")
            except Exception as e:
                logger.warning(f"[NewsRadar] source_urls反序列化失败: {e}")
                source_urls = []
        
        return {
            "id": props.get("id"),
            "title": props.get("title"),
            "url": props.get("url"),
            "snippet": props.get("snippet"),
            "content": props.get("content"),
            "source": props.get("source"),
            "created_at": props.get("created_at"),
            "source_urls": source_urls,  # 原始新闻链接列表
        }

    async def _format_and_translate_news_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """将新闻项格式化：翻译标题（如果是英文）、清理内容markdown标记、限制长度。"""
        title = item.get("title", "").strip()
        snippet = item.get("snippet", "").strip()
        content = item.get("content", snippet).strip()
        
        # 检测标题是否为英文，需要翻译
        needs_translation = self._is_mostly_english(title)
        
        translated_title = title
        if needs_translation and len(title) > 10:
            try:
                # 使用 LLM 翻译标题到中文
                translation_prompt = f"将以下新闻标题翻译成简体中文，仅返回翻译结果，不要其他说明：\n{title}"
                translated_title = self.entity_agent.run(translation_prompt)
                # 立即清洗可能的JSON/特殊格式
                translated_title = self._extract_clean_title(translated_title)
                if len(translated_title) > 300:
                    translated_title = translated_title[:300]
                logger.debug(f"[NewsRadar] 标题翻译: {title[:50]}... -> {translated_title[:50]}...")
            except Exception as e:
                logger.warning(f"[NewsRadar] 标题翻译失败: {e}，保持原标题")
                translated_title = title[:300]
        else:
            translated_title = title[:300]
        
        # 最后一道防线：再次确保标题干净
        translated_title = self._extract_clean_title(translated_title)
        
        # 清理内容：移除markdown标记
        cleaned_content = self._clean_markdown_content(content)
        
        return {
            **item,
            "title": translated_title,
            "snippet": snippet[:500],
            "content": cleaned_content[:3000],
        }
    
    def _extract_clean_title(self, title: str) -> str:
        """从标题中提取干净的文本，处理JSON和其他特殊格式。"""
        import json
        import re
        
        t = (title or "").strip()
        if not t:
            return "科技动态"
        
        # 如果看起来是JSON格式，尝试解析并提取纯文本
        if (t.startswith('{') or t.startswith('[')) or ('{' in t[:10] and '"' in t[:20]):
            try:
                # 尝试直接解析JSON
                obj = json.loads(t)
                if isinstance(obj, dict):
                    # 搜索包含text的字段：translation > translated_title > title > text > result等
                    for key in ['translation', 'translated_title', 'title', 'text', 'result', '翻译', 'content']:
                        val = obj.get(key)
                        if val and isinstance(val, str) and len(val.strip()) > 2:
                            t = val.strip()
                            break
                else:
                    t = str(obj)[:100]
            except json.JSONDecodeError:
                # JSON解析失败，用正则提取双引号内的内容
                matches = re.findall(r'"([^"]{6,150})"', t)
                if matches:
                    # 优先提取较长的内容（通常是实际文本）
                    t = max(matches, key=len)[:100]
                else:
                    # 最后的fallback：移除所有JSON标记字符
                    t = re.sub(r'[{}\[\]"]', '', t).strip()
        
        # 去掉多余的引号
        t = t.strip('"').strip("'").strip()
        
        # 移除常见的前缀（翻译、结果等）
        t = re.sub(r'^(翻译|translation|translated|结果|result|回复|response)[\s：:]*', '', t, flags=re.I).strip()
        
        # 如果太短或仍包含异常字符，使用默认值
        if not t or len(t) < 3 or t.count('{') > 0 or t.count('[') > 0:
            return "科技动态"
        
        return t[:150]
    
    @staticmethod
    def _is_mostly_english(text: str) -> bool:
        """判断文本是否主要是英文（超过30%的英文字符则认为是英文）。"""
        if not text or len(text) < 5:
            return False
        # 统计英文字母和数字
        en_count = sum(1 for c in text if (c.isascii() and c.isalpha()))
        return en_count > len(text) * 0.3
    
    @staticmethod
    def _clean_markdown_content(content: str) -> str:
        """从内容中清理markdown标记：移除# ## ###标题、代码块、特殊符号等。"""
        if not content:
            return ""
        
        lines = content.split("\n")
        cleaned = []
        in_code_block = False
        
        for line in lines:
            stripped = line.strip()
            
            # 处理代码块
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            
            if in_code_block:
                continue
            
            # 跳过仅包含分隔符的行
            if stripped in ("---", "***", "___") or stripped == "":
                if cleaned and stripped == "":
                    cleaned.append("")  # 保留一个空行作为段落分隔
                continue
            
            # 移除标题标记（# ## ### 等）但保留标题内容
            if stripped.startswith("#"):
                text = stripped.lstrip("#").strip()
                if text:
                    cleaned.append(f"\n{text}")  # 作为段落
            # 移除markdown链接格式但保留链接文本 [text](url) -> text
            elif "[" in stripped and "](http" in stripped:
                text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", stripped)
                if text:
                    cleaned.append(text)
            # 移除html标签
            elif "<" in stripped and ">" in stripped:
                text = re.sub(r"<[^>]+>", "", stripped)
                if text.strip():
                    cleaned.append(text)
            # 保留普通文本行
            elif stripped:
                cleaned.append(stripped)
        
        result = "\n".join(cleaned).strip()
        # 合并多余的空行
        result = re.sub(r"\n\n\n+", "\n\n", result)
        return result

    def _should_search(self, search_key: str = "default") -> bool:
        """检查是否应该执行搜索（基于时间限制）。
        
        Args:
            search_key: 搜索键（用于区分不同的搜索）
        
        Returns:
            bool: 是否应该执行搜索
        """
        if search_key not in self.last_search_time:
            return True  # 首次搜索
        
        last_time = self.last_search_time[search_key]
        elapsed_hours = (datetime.utcnow() - last_time).total_seconds() / 3600
        
        if elapsed_hours >= self.search_interval_hours:
            logger.info(f"[NewsRadar] 搜索间隔已满{self.search_interval_hours}小时，准许执行搜索: {search_key}")
            return True
        else:
            logger.info(f"[NewsRadar] 搜索冷却中: {search_key}，距下次搜索还有 {self.search_interval_hours - elapsed_hours:.1f} 小时")
            return False
    
    def _record_search(self, search_key: str = "default") -> None:
        """记录搜索时间。"""
        self.last_search_time[search_key] = datetime.utcnow()
        logger.info(f"[NewsRadar] 记录搜索时间: {search_key}")

    @staticmethod
    def _make_news_id(url: str) -> str:
        return hashlib.sha1(url.encode("utf-8")).hexdigest()

    @staticmethod
    def _make_entity_id(name: str, etype: str) -> str:
        key = f"{etype}::{name}".lower()
        return hashlib.sha1(key.encode("utf-8")).hexdigest()

    @staticmethod
    def _entity_system_prompt() -> str:
        return (
            "你是一个新闻实体抽取助手，专门从科技新闻文本中识别重要实体。\n"
            "始终用 JSON 格式回答，不要包含解释性文字。"
        )

    @staticmethod
    def _analysis_system_prompt() -> str:
        return (
            "你是科技新闻雷达的分析专家。\n"
            "收到用户关注的实体列表和最近相关新闻后，请：\n"
            "1) 概括这些实体在最近新闻中的关键事件\n"
            "2) 说明它们之间的合作/竞争/依赖关系\n"
            "3) 提出短期和中期的发展判断（机会与风险）\n"
            "4) 用 Markdown 分段输出，条理清晰，可直接展示给用户。\n"
        )

    async def search_news(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索新闻（使用真实搜索工具，不是在Neo4j中查询）。
        
        Args:
            query: 搜索关键词
            limit: 返回结果数量
            
        Returns:
            新闻列表
        """
        if not self.search_tool:
            logger.warning("[NewsRadar] 搜索工具未配置，无法执行真实搜索")
            # 降级到Neo4j本地搜索
            return await self._search_news_local(query, limit)
        
        # 尝试从缓存获取
        cached_results = news_cache.get_search_results(query)
        if cached_results:
            logger.info(f"[NewsRadar] 从缓存返回搜索结果: '{query[:30]}...'")
            return cached_results[:limit]
        
        # 检查搜索时间限制（每个查询每1小时只进行一次真实搜索）
        search_key = f"search_{query}"
        if not self._should_search(search_key):
            logger.info(f"[NewsRadar] 搜索冷却中，降级到本地搜索: '{query}'")
            return await self._search_news_local(query, limit)
        
        try:
            # 使用真实搜索工具获取最新新闻（限定为新闻类型）
            logger.info(f"[NewsRadar] 使用搜索工具搜索新闻: '{query}'")
            results = await self.search_tool.search(query, max_results=limit, days=7, topic="news")
            logger.info(f"[NewsRadar] 搜索到 {len(results)} 条新闻")

            if not results:
                # 搜索工具无结果时，使用 RSS 并做关键词过滤
                rss_results = await self._fetch_latest_tech_rss(max_items=max(30, limit * 2))
                q = query.lower()
                results = [
                    r for r in rss_results
                    if q in (r.get("title", "") + " " + r.get("snippet", "")).lower()
                ]
                if not results:
                    results = rss_results[:limit]
                logger.info(f"[NewsRadar] 使用 RSS 兜底搜索，返回 {len(results)} 条候选")
            
            # 记录本次搜索时间
            self._record_search(search_key)
            
            # 对搜索结果做综合整理，只生成少量摘要档案，而不是每条都展示
            digest = await self._build_topic_digest(query.strip(), results)
            news_items: List[Dict[str, Any]] = []
            if digest:
                # 标记这是一个搜索档案，保存搜索关键词
                digest["search_topic"] = query.strip()
                digest["is_search_archive"] = True
                await self._upsert_news_with_entities(digest)
                digest_id = digest.get("id") or self._make_news_id(digest.get("url", query))
                news_items.append(
                    {
                        "id": digest_id,
                        "title": digest.get("title"),
                        "url": digest.get("url"),
                        "snippet": digest.get("snippet"),
                        "content": digest.get("raw_content"),
                        "source": digest.get("source"),
                        "created_at": datetime.utcnow().isoformat(),
                    }
                )
            
            # 缓存结果
            if news_items:
                news_cache.set_search_results(query, news_items)
            
            return news_items[:limit]
            
        except Exception as e:
            logger.error(f"[NewsRadar] 真实搜索失败: {e}", exc_info=True)
            # 降级到本地搜索
            return await self._search_news_local(query, limit)
    
    async def _search_news_local(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """在Neo4j中搜索已有新闻（降级方案）"""
        try:
            records = neo4j_client.run_query(
                """
                MATCH (n:News)
                WHERE toLower(n.title) CONTAINS toLower($query) 
                   OR toLower(n.snippet) CONTAINS toLower($query)
                RETURN n
                ORDER BY n.created_at DESC
                LIMIT $limit
                """,
                {"query": query, "limit": limit},
            )
            results = [self._serialize_news_record(r["n"]) for r in records]
            
            # ⚠️ 注意：不要在这里重复翻译！翻译应该在入库时只做一次
            # 直接返回已翻译的数据
            
            return results
            
        except Exception as e:
            logger.error(f"[NewsRadar] 本地搜索失败: {e}", exc_info=True)
            return []

    async def _fetch_latest_tech_rss(self, max_items: int = 30) -> List[Dict[str, Any]]:
        """从公开科技 RSS 抓取最新新闻，作为搜索工具失败时的兜底方案。"""
        feeds = [
            ("TechCrunch", "https://techcrunch.com/feed/"),
            ("The Verge", "https://www.theverge.com/rss/index.xml"),
            ("Wired", "https://www.wired.com/feed/rss"),
            ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
            ("VentureBeat", "https://venturebeat.com/feed/"),
        ]
        collected: List[Dict[str, Any]] = []

        try:
            for source_name, url in feeds:
                try:
                    with urllib.request.urlopen(url, timeout=15) as resp:
                        text = resp.read().decode("utf-8", errors="ignore")

                        try:
                            root = ET.fromstring(text)

                            # 兼容 RSS/Atom
                            entries = root.findall(".//item")
                            if not entries:
                                entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")

                            for entry in entries[:15]:
                                title_el = entry.find("title") or entry.find("{http://www.w3.org/2005/Atom}title")
                                link_el = entry.find("link")
                                atom_link_el = entry.find("{http://www.w3.org/2005/Atom}link")
                                desc_el = entry.find("description") or entry.find("summary") or entry.find("{http://www.w3.org/2005/Atom}summary")
                                date_el = entry.find("pubDate") or entry.find("{http://www.w3.org/2005/Atom}updated")

                                title = (title_el.text or "").strip() if title_el is not None and title_el.text else ""
                                if not title:
                                    continue

                                link = ""
                                if link_el is not None:
                                    link = (link_el.text or "").strip() if link_el.text else ""
                                if not link and atom_link_el is not None:
                                    link = atom_link_el.attrib.get("href", "").strip()

                                snippet = ""
                                if desc_el is not None and desc_el.text:
                                    snippet = re.sub(r"<[^>]+>", "", desc_el.text).strip()

                                # 尝试过滤过旧新闻（超过14天）
                                if date_el is not None and date_el.text:
                                    try:
                                        dt = parsedate_to_datetime(date_el.text)
                                        age_days = (datetime.utcnow() - dt.replace(tzinfo=None)).days
                                        if age_days > 14:
                                            continue
                                    except Exception:
                                        pass

                                collected.append(
                                    {
                                        "title": title,
                                        "url": link,
                                        "snippet": snippet[:500],
                                        "source": source_name,
                                        "raw_content": snippet[:2000],
                                    }
                                )
                        except Exception:
                            # XML 解析失败时，退化为正则抽取（应对非标准 RSS）
                            item_blocks = re.findall(r"<item>(.*?)</item>", text, flags=re.S | re.I)
                            for block in item_blocks[:15]:
                                title_match = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>", block, flags=re.S | re.I)
                                link_match = re.search(r"<link>(.*?)</link>", block, flags=re.S | re.I)
                                desc_match = re.search(r"<description><!\[CDATA\[(.*?)\]\]></description>|<description>(.*?)</description>", block, flags=re.S | re.I)
                                if not title_match:
                                    continue
                                title = (title_match.group(1) or title_match.group(2) or "").strip()
                                if not title:
                                    continue
                                link = (link_match.group(1).strip() if link_match else "")
                                raw_desc = (desc_match.group(1) or desc_match.group(2) or "") if desc_match else ""
                                snippet = re.sub(r"<[^>]+>", "", raw_desc).strip()
                                collected.append(
                                    {
                                        "title": title,
                                        "url": link,
                                        "snippet": snippet[:500],
                                        "source": source_name,
                                        "raw_content": snippet[:2000],
                                    }
                                )
                except Exception as feed_exc:
                    logger.warning(f"[NewsRadar] RSS抓取失败 {source_name}: {repr(feed_exc)}")

            # 去重并限制数量
            uniq: List[Dict[str, Any]] = []
            seen = set()
            for item in collected:
                u = (item.get("url") or "").strip()
                if not u or u in seen:
                    continue
                seen.add(u)
                uniq.append(item)
                if len(uniq) >= max_items:
                    break

            return uniq
        except Exception as exc:
            logger.warning(f"[NewsRadar] RSS兜底抓取失败: {exc}")
            return []

    def _infer_tech_topic(self, item: Dict[str, Any]) -> str:
        text = f"{item.get('title', '')} {item.get('snippet', '')}".lower()
        rules = {
            "人工智能": ["ai", "artificial intelligence", "llm", "model", "机器人", "agent"],
            "芯片与半导体": ["chip", "semiconductor", "nvidia", "tsmc", "gpu", "晶圆", "半导体"],
            "云与数据中心": ["cloud", "aws", "azure", "gcp", "datacenter", "server", "云"],
            "网络与安全": ["cyber", "security", "zero-day", "attack", "漏洞", "安全"],
            "智能终端与消费电子": ["smartphone", "iphone", "android", "wearable", "ar", "vr", "pc"],
            "汽车与自动驾驶": ["ev", "electric vehicle", "autonomous", "tesla", "自动驾驶", "电动车"],
            "生物科技与医疗": ["biotech", "genomics", "drug", "fda", "医疗", "生物科技"],
            "量子与前沿科技": ["quantum", "fusion", "space tech", "satellite", "量子", "航天"],
        }
        for topic, keywords in rules.items():
            if any(k in text for k in keywords):
                return topic
        return "综合科技"

    async def _build_topic_digest(self, topic: str, items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not items:
            return None

        # 控制上下文长度，保留最新若干条
        selected = items[:8]
        lines = []
        for idx, it in enumerate(selected, start=1):
            title = (it.get("title") or "").strip()
            snippet = (it.get("snippet") or "").strip()
            url = (it.get("url") or "").strip()
            lines.append(f"[{idx}] 标题: {title}\n摘要: {snippet}\n链接: {url}")

        prompt = (
            f"追踪事件：{topic}\n"
            f"请基于以下新闻，生成事件追踪稿（不是赛道总分分类稿）。\n"
            "要求：\n"
            "1) 不要逐条照搬原文；请整理事件时间线、关键人物/组织、变动原因。\n"
            "2) 产出 JSON: {title, summary, key_points}。\n"
            "3) title 20字以内；summary 120-220字；key_points 为3-5条。\n"
            "4) 内容必须是时效性的最新动态。\n\n"
            f"新闻材料：\n{chr(10).join(lines)}\n"
            "只返回 JSON。"
        )

        try:
            raw = self.analysis_agent.run(prompt)
            import json

            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()

            data = json.loads(raw)
            title = (data.get("title") or f"{topic} 事件追踪").strip()
            title = self._sanitize_digest_title(title=title, topic=topic, items=selected)
            summary = (data.get("summary") or "").strip()
            key_points = data.get("key_points") or []
            if isinstance(key_points, list):
                bullets = [f"- {str(p).strip()}" for p in key_points if str(p).strip()]
            else:
                bullets = []

            merged_content = (summary + "\n\n" + "\n".join(bullets)).strip()
            if not merged_content:
                merged_content = "\n".join(lines)[:2000]

            digest_url_seed = "|".join([(it.get("url") or "") for it in selected if it.get("url")])
            digest_url = f"radar://digest/{self._make_news_id(topic + digest_url_seed)}"
            digest_id = self._make_news_id(digest_url)

            formatted = await self._format_and_translate_news_item(
                {
                    "id": digest_id,
                    "title": title,
                    "url": digest_url,
                    "snippet": summary[:180] if summary else merged_content[:180],
                    "content": merged_content,
                    "source": "radar_digest",
                    "created_at": datetime.utcnow().isoformat(),
                }
            )

            # 收集原始新闻链接，用于详情页展示
            source_urls = [
                {"title": it.get("title", "").strip(), "url": it.get("url", "").strip()}
                for it in selected
                if it.get("url") and it.get("title")
            ]

            return {
                "id": digest_id,
                "title": formatted.get("title", title),
                "url": digest_url,
                "snippet": formatted.get("snippet", summary[:180]),
                "raw_content": formatted.get("content", merged_content),
                "source": "radar_digest",
                "source_count": len(selected),
                "source_urls": source_urls,  # 原始新闻链接列表
            }
        except Exception as exc:
            logger.warning(f"[NewsRadar] 生成主题摘要失败({topic}): {exc}")
            fallback_title = self._make_digest_label(selected)
            headline_list = [((it.get("title") or "").strip()) for it in selected if (it.get("title") or "").strip()]
            top_titles = headline_list[:3]
            brief = "；".join(top_titles)
            fallback_summary = f"围绕“{topic}”的相关新闻显示：{brief[:180]}。从公开信息看，事件涉及组织调整、关键人事变动与竞争策略变化，短期仍在持续发酵。"
            fallback_points = [f"- {t[:80]}" for t in top_titles]
            fallback_text = (fallback_summary + "\n\n" + "\n".join(fallback_points)).strip()[:1800]
            digest_url = f"radar://digest/{self._make_news_id(topic + fallback_text[:120])}"
            digest_id = self._make_news_id(digest_url)
            
            # 收集原始新闻链接（fallback分支）
            source_urls = [
                {"title": it.get("title", "").strip(), "url": it.get("url", "").strip()}
                for it in selected
                if it.get("url") and it.get("title")
            ]
            
            return {
                "id": digest_id,
                "title": fallback_title,
                "url": digest_url,
                "snippet": fallback_summary[:180],
                "raw_content": fallback_text,
                "source": "radar_digest",
                "source_count": len(selected),
                "source_urls": source_urls,  # 原始新闻链接列表
            }

    def _make_digest_label(self, items: List[Dict[str, Any]]) -> str:
        """从新闻簇中提炼事件标题，用于替代纯分类命名。"""
        if not items:
            return "科技事件追踪"
        top_title = (items[0].get("title") or "科技事件").strip()
        top_title = re.sub(r"\s*[-|｜].*$", "", top_title).strip()
        if len(top_title) > 18:
            top_title = top_title[:18]
        return f"{top_title} 追踪"

    def _sanitize_digest_title(self, title: str, topic: str, items: List[Dict[str, Any]]) -> str:
        """清洗摘要标题，避免将JSON/异常文本直接展示到前端。"""
        t = (title or "").strip()
        if not t:
            return self._make_digest_label(items)

        lower_t = t.lower()
        looks_like_json = (
            t.startswith("{")
            or t.startswith("[")
            or "\"entities\"" in lower_t
            or "\"relationships\"" in lower_t
            or "\"key_points\"" in lower_t
        )

        # 过长标题通常是模型把结构化内容塞进了title字段
        if looks_like_json or len(t) > 36:
            return self._make_digest_label(items)

        # 去掉首尾引号和多余空白
        t = t.strip('"').strip("'").strip()
        return t or self._make_digest_label(items)

    def record_news_view(self, user_id: int, news_id: str, news_data: Dict[str, Any]) -> None:
        """记录用户查看新闻的历史（雷达档案）"""
        with get_db_context() as db:
            history = db.query(UserNewsHistory).filter(
                UserNewsHistory.user_id == user_id,
                UserNewsHistory.news_id == news_id
            ).first()

            if history:
                history.view_count += 1
                history.news_title = news_data.get("title", history.news_title)
                history.news_url = news_data.get("url", history.news_url)
                history.news_snippet = news_data.get("snippet", history.news_snippet)
            else:
                history = UserNewsHistory(
                    user_id=user_id,
                    news_id=news_id,
                    news_title=news_data.get("title"),
                    news_url=news_data.get("url"),
                    news_snippet=news_data.get("snippet"),
                    view_count=1
                )
                db.add(history)
            db.commit()

    @staticmethod
    def _parse_history_notes(raw_notes: Optional[str]) -> Dict[str, Any]:
        default_notes: Dict[str, Any] = {
            "schema_version": 2,
            "analysis_runs": [],
            "followups": [],
            "short_term_memory": {
                "window": [],
                "summary": "",
                "last_topics": [],
            },
            "long_term_memory": {
                "facts": [],
                "preferences": {
                    "focus_areas": [],
                    "response_style": "evidence-first",
                },
                "entity_interests": {},
            },
        }

        if not raw_notes:
            return default_notes
        try:
            parsed = json.loads(raw_notes)
            if isinstance(parsed, dict):
                parsed.setdefault("analysis_runs", [])
                parsed.setdefault("followups", [])
                parsed.setdefault("schema_version", 2)
                stm = parsed.setdefault("short_term_memory", {})
                if not isinstance(stm, dict):
                    stm = {}
                    parsed["short_term_memory"] = stm
                stm.setdefault("window", [])
                stm.setdefault("summary", "")
                stm.setdefault("last_topics", [])

                ltm = parsed.setdefault("long_term_memory", {})
                if not isinstance(ltm, dict):
                    ltm = {}
                    parsed["long_term_memory"] = ltm
                ltm.setdefault("facts", [])
                pref = ltm.setdefault("preferences", {})
                if not isinstance(pref, dict):
                    pref = {}
                    ltm["preferences"] = pref
                pref.setdefault("focus_areas", [])
                pref.setdefault("response_style", "evidence-first")
                ltm.setdefault("entity_interests", {})
                return parsed
            return default_notes
        except Exception:
            return default_notes

    @staticmethod
    def _pick_answer_highlight(answer: str) -> str:
        if not answer:
            return ""
        plain = re.sub(r"[`#>*\-]", " ", answer)
        plain = re.sub(r"\s+", " ", plain).strip()
        return plain[:220]

    @staticmethod
    def _estimate_memory_importance(question: str, answer: str, entities: List[str]) -> float:
        score = 0.45
        q = (question or "").lower()
        a = (answer or "").lower()
        if len(entities or []) >= 3:
            score += 0.15
        if any(k in q for k in ["风险", "机会", "策略", "判断", "预测", "投资", "竞争"]):
            score += 0.2
        if any(k in a for k in ["建议", "结论", "优先", "action", "建议"]):
            score += 0.1
        if len(answer or "") > 900:
            score += 0.1
        return min(1.0, round(score, 2))

    def _update_memory_from_interaction(
        self,
        notes: Dict[str, Any],
        memory_type: str,
        question: str,
        answer: str,
        entities: List[str],
        user_id: Optional[int] = None,
        news_id: Optional[str] = None,
    ) -> None:
        ts = datetime.utcnow().isoformat()
        short_term = self._normalize_short_memory(notes.get("short_term_memory") or {})
        if user_id and news_id:
            short_term = self._load_layered_short_memory(user_id=user_id, news_id=news_id, notes=notes)

        window = short_term.setdefault("window", [])
        item = {
            "ts": ts,
            "type": memory_type,
            "question": (question or "")[:300],
            "answer_highlight": self._pick_answer_highlight(answer),
            "entities": [e for e in entities if e][:8],
        }
        window.append(item)
        short_term["window"] = window[-10:]

        topics = short_term.setdefault("last_topics", [])
        for entity in item["entities"]:
            if entity not in topics:
                topics.append(entity)
        short_term["last_topics"] = topics[-12:]

        recent = short_term.get("window", [])[-3:]
        short_term["summary"] = " | ".join(
            [
                f"{x.get('type', 'analysis')}:{(x.get('question') or '')[:40]}"
                for x in recent
            ]
        )[:360]
        short_term["last_updated"] = ts

        long_term = notes.setdefault("long_term_memory", {})
        facts = long_term.setdefault("facts", [])
        importance = self._estimate_memory_importance(question, answer, item["entities"])
        highlight = item["answer_highlight"]
        if highlight:
            facts.append(
                {
                    "content": highlight,
                    "importance": importance,
                    "source": memory_type,
                    "updated_at": ts,
                    "entities": item["entities"],
                }
            )
        facts = sorted(
            facts,
            key=lambda x: (float(x.get("importance") or 0), str(x.get("updated_at") or "")),
            reverse=True,
        )
        long_term["facts"] = facts[:25]

        preferences = long_term.setdefault("preferences", {})
        focus_areas = preferences.setdefault("focus_areas", [])
        for entity in item["entities"]:
            if entity not in focus_areas:
                focus_areas.append(entity)
        preferences["focus_areas"] = focus_areas[-15:]

        entity_interests = long_term.setdefault("entity_interests", {})
        for entity in item["entities"]:
            info = entity_interests.get(entity) or {"count": 0, "last_seen": ts}
            info["count"] = int(info.get("count") or 0) + 1
            info["last_seen"] = ts
            entity_interests[entity] = info

        notes["short_term_memory"] = short_term
        if user_id and news_id:
            self._persist_layered_short_memory(user_id=user_id, news_id=news_id, short_memory=short_term)
        if user_id:
            self._update_user_profile_from_interaction(
                user_id=user_id,
                entities=item["entities"],
                question=question,
            )

    def _build_memory_context(self, notes: Dict[str, Any], profile: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        short_term = notes.get("short_term_memory") or {}
        long_term = notes.get("long_term_memory") or {}
        window = short_term.get("window") or []
        facts = long_term.get("facts") or []
        long_term_focus = ((long_term.get("preferences") or {}).get("focus_areas") or [])
        profile_focus = (profile or {}).get("focus_areas") or []
        merged_focus = []
        for token in list(long_term_focus) + list(profile_focus):
            if token and token not in merged_focus:
                merged_focus.append(token)

        short_lines = []
        for item in window[-4:]:
            short_lines.append(
                f"- {item.get('type', 'analysis')} | Q: {(item.get('question') or '')[:80]} | A: {(item.get('answer_highlight') or '')[:120]}"
            )
        short_text = "\n".join(short_lines) if short_lines else "- 无短期记忆"

        long_lines = []
        for idx, fact in enumerate(facts[:5], start=1):
            long_lines.append(f"- 记忆{idx}: {(fact.get('content') or '')[:150]}")
        if merged_focus:
            long_lines.append(f"- 用户画像关注: {', '.join(merged_focus[:8])}")
        long_text = "\n".join(long_lines) if long_lines else "- 无长期记忆"

        digest_parts = [short_term.get("summary") or ""]
        if merged_focus:
            digest_parts.append("focus:" + "|".join(merged_focus[:6]))
        digest = " || ".join([x for x in digest_parts if x])[:500]

        return {
            "short_text": short_text,
            "long_text": long_text,
            "digest": digest,
        }

    def record_news_analysis(
        self,
        user_id: int,
        news_id: str,
        entities: List[str],
        question: str,
        answer: str,
        local_news_count: int,
        web_news_count: int,
    ) -> None:
        """记录一次按图索骥历史，用于报告和追问上下文。"""
        with get_db_context() as db:
            history = db.query(UserNewsHistory).filter(
                UserNewsHistory.user_id == user_id,
                UserNewsHistory.news_id == news_id,
            ).first()

            if not history:
                history = UserNewsHistory(
                    user_id=user_id,
                    news_id=news_id,
                    view_count=0,
                    analysis_count=0,
                )
                db.add(history)

            history.analysis_count = (history.analysis_count or 0) + 1
            notes = self._parse_history_notes(history.notes)
            notes["analysis_runs"].append(
                {
                    "ts": datetime.utcnow().isoformat(),
                    "entities": entities,
                    "question": question,
                    "answer": answer[:2000],
                    "local_news_count": local_news_count,
                    "web_news_count": web_news_count,
                }
            )
            notes["analysis_runs"] = notes["analysis_runs"][-20:]
            self._update_memory_from_interaction(
                notes=notes,
                memory_type="analysis",
                question=question,
                answer=answer,
                entities=entities,
                user_id=user_id,
                news_id=news_id,
            )
            history.notes = json.dumps(notes, ensure_ascii=False)
            db.commit()

    async def generate_followup_answer(
        self,
        news_id: str,
        question: str,
        entities: Optional[List[str]] = None,
        analysis_history: Optional[List[Dict[str, Any]]] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """针对当前雷达项目进行追问，结合图谱、本地新闻与互联网搜索结果。"""
        detail = await self.get_news_detail(news_id)
        if not detail:
            raise ValueError("新闻不存在")

        entity_pool = entities or [n.get("name") for n in detail.get("graph", {}).get("nodes", []) if n.get("type") != "News"]
        entity_pool = [e for e in entity_pool if e][:6]

        notes: Optional[Dict[str, Any]] = None
        memory_context = {"short_text": "- 无短期记忆", "long_text": "- 无长期记忆", "digest": ""}
        profile_context: Optional[Dict[str, Any]] = None
        if user_id:
            with get_db_context() as db:
                history = db.query(UserNewsHistory).filter(
                    UserNewsHistory.user_id == user_id,
                    UserNewsHistory.news_id == news_id,
                ).first()
                notes = self._parse_history_notes(history.notes if history else None)
            layered_short = self._load_layered_short_memory(user_id=user_id, news_id=news_id, notes=notes)
            notes["short_term_memory"] = layered_short
            profile_context = self._load_user_profile(user_id)
            memory_context = self._build_memory_context(notes, profile=profile_context)

        # 追问缓存键：新闻 + 实体簇 + 追问内容 + 最近历史摘要 + 用户记忆摘要
        history_digest = memory_context.get("digest", "")
        if analysis_history:
            compact = analysis_history[-3:]
            ext = " | ".join((h.get("question") or "")[:80] for h in compact)
            history_digest = f"{history_digest} || {ext}" if history_digest else ext
        followup_cache_key = self._build_radar_cache_key(
            kind="followup",
            news_id=news_id,
            entities=entity_pool,
            question=question,
            extra_context=history_digest,
        )
        cached_followup = news_cache.get_entity_analysis(followup_cache_key)
        if cached_followup:
            logger.info(f"[NewsRadar] 继续追问 Redis缓存命中 key={followup_cache_key}")
            cached_followup["cache_hit"] = True
            cached_followup["cache_source"] = "news:l2_or_l1"
            if user_id:
                with get_db_context() as db:
                    history = db.query(UserNewsHistory).filter(
                        UserNewsHistory.user_id == user_id,
                        UserNewsHistory.news_id == news_id,
                    ).first()
                    if not history:
                        history = UserNewsHistory(
                            user_id=user_id,
                            news_id=news_id,
                            view_count=0,
                            analysis_count=0,
                        )
                        db.add(history)
                    notes = self._parse_history_notes(history.notes)
                    notes["followups"].append(
                        {
                            "ts": datetime.utcnow().isoformat(),
                            "question": question,
                            "answer": (cached_followup.get("answer") or "")[:2000],
                        }
                    )
                    notes["followups"] = notes["followups"][-30:]
                    self._update_memory_from_interaction(
                        notes=notes,
                        memory_type="followup",
                        question=question,
                        answer=(cached_followup.get("answer") or ""),
                        entities=entity_pool,
                        user_id=user_id,
                        news_id=news_id,
                    )
                    history.notes = json.dumps(notes, ensure_ascii=False)
                    db.commit()
            return cached_followup

        local_news = await self.analyze_entities(
            entity_names=entity_pool or [detail.get("news", {}).get("title", "科技新闻")],
            user_question="请仅返回相关新闻，不要分析。",
        )

        history_text = ""
        if analysis_history:
            compact = analysis_history[-5:]
            history_text = "\n".join(
                [f"- 问题: {h.get('question','')}\n  回答摘要: {(h.get('answer','') or '')[:300]}" for h in compact]
            )

        prompt = (
            f"当前新闻标题：{detail.get('news', {}).get('title', '')}\n"
            f"当前新闻摘要：{detail.get('news', {}).get('snippet', '')}\n"
            f"关键实体：{', '.join(entity_pool)}\n\n"
            f"短期记忆（最近交互）：\n{memory_context['short_text']}\n\n"
            f"长期记忆（稳定偏好/历史结论）：\n{memory_context['long_text']}\n\n"
            f"历史按图索骥记录：\n{history_text or '无'}\n\n"
            f"最新检索结果（本地+互联网）：\n{json.dumps(local_news.get('news', [])[:8], ensure_ascii=False)}\n\n"
            f"用户追问：{question}\n\n"
            "请给出直接、可执行、基于证据的回答，使用Markdown要点输出。"
        )

        answer = self.analysis_agent.run(prompt)

        if user_id:
            with get_db_context() as db:
                history = db.query(UserNewsHistory).filter(
                    UserNewsHistory.user_id == user_id,
                    UserNewsHistory.news_id == news_id,
                ).first()
                if not history:
                    history = UserNewsHistory(
                        user_id=user_id,
                        news_id=news_id,
                        view_count=0,
                        analysis_count=0,
                    )
                    db.add(history)
                notes = self._parse_history_notes(history.notes)
                notes["followups"].append(
                    {
                        "ts": datetime.utcnow().isoformat(),
                        "question": question,
                        "answer": answer[:2000],
                    }
                )
                notes["followups"] = notes["followups"][-30:]
                self._update_memory_from_interaction(
                    notes=notes,
                    memory_type="followup",
                    question=question,
                    answer=answer,
                    entities=entity_pool,
                    user_id=user_id,
                    news_id=news_id,
                )
                history.notes = json.dumps(notes, ensure_ascii=False)
                db.commit()

        result = {
            "question": question,
            "entities": entity_pool,
            "answer": answer,
            "news": local_news.get("news", []),
            "memory_used": bool(memory_context.get("digest")),
            "cache_hit": False,
            "cache_source": None,
        }
        news_cache.set_entity_analysis(followup_cache_key, result)
        return result

    def get_news_item_user_history(self, user_id: int, news_id: str) -> Dict[str, Any]:
        """获取用户在某条新闻下的完整历史（按图索骥记录 + 追问记录），用于刷新后恢复。"""
        with get_db_context() as db:
            history = db.query(UserNewsHistory).filter(
                UserNewsHistory.user_id == user_id,
                UserNewsHistory.news_id == news_id,
            ).first()
            if not history:
                empty_notes = self._parse_history_notes(None)
                return {
                    "analysis_runs": [],
                    "followups": [],
                    "short_term_memory": empty_notes.get("short_term_memory", {}),
                    "long_term_memory": empty_notes.get("long_term_memory", {}),
                    "user_profile": self._load_user_profile(user_id),
                }
            notes = self._parse_history_notes(history.notes)
            layered_short = self._load_layered_short_memory(user_id=user_id, news_id=news_id, notes=notes)
            return {
                "analysis_runs": notes.get("analysis_runs", []),
                "followups": notes.get("followups", []),
                "short_term_memory": layered_short,
                "long_term_memory": notes.get("long_term_memory", {}),
                "user_profile": self._load_user_profile(user_id),
            }

    def get_news_item_memory(self, user_id: int, news_id: str) -> Dict[str, Any]:
        """获取某条新闻下的结构化记忆（短期窗口 + 长期偏好/事实）。"""
        history_data = self.get_news_item_user_history(user_id=user_id, news_id=news_id)
        notes = {
            "short_term_memory": history_data.get("short_term_memory", {}),
            "long_term_memory": history_data.get("long_term_memory", {}),
        }
        profile = history_data.get("user_profile") if isinstance(history_data.get("user_profile"), dict) else self._load_user_profile(user_id)
        context = self._build_memory_context(notes, profile=profile)
        return {
            "short_term_memory": notes.get("short_term_memory", {}),
            "long_term_memory": notes.get("long_term_memory", {}),
            "user_profile": profile,
            "memory_context": context,
        }

    def get_user_news_history(
        self, 
        user_id: int, 
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """获取用户的雷达档案（查看历史）"""
        with get_db_context() as db:
            query = db.query(UserNewsHistory).filter(
                UserNewsHistory.user_id == user_id
            ).order_by(
                UserNewsHistory.last_viewed_at.desc()
            )

            total = query.count()
            items = query.offset(offset).limit(limit).all()

            return {
                "items": [
                    {
                        "id": item.id,
                        "news_id": item.news_id,
                        "news_title": item.news_title,
                        "news_url": item.news_url,
                        "news_snippet": item.news_snippet,
                        "view_count": item.view_count,
                        "analysis_count": item.analysis_count,
                        "report_generated": item.report_generated,
                        "last_viewed_at": item.last_viewed_at.isoformat() if item.last_viewed_at else None,
                        "first_viewed_at": item.first_viewed_at.isoformat() if item.first_viewed_at else None,
                        "notes": item.notes
                    }
                    for item in items
                ],
                "total": total,
                "offset": offset,
                "limit": limit
            }

    async def generate_news_report(
        self, 
        user_id: int, 
        news_id: str
    ) -> Dict[str, Any]:
        """生成雷达报告（用户在该新闻下的所有操作和分析结果）"""
        detail = await self.get_news_detail(news_id)
        if not detail:
            raise ValueError("新闻不存在")

        history_data = {
            "view_count": 1,
            "analysis_count": 0,
            "report_count": 1,
            "first_viewed": None,
            "last_viewed": None,
            "notes": None,
        }

        with get_db_context() as db:
            history = db.query(UserNewsHistory).filter(
                UserNewsHistory.user_id == user_id,
                UserNewsHistory.news_id == news_id
            ).first()

            if history:
                history.report_generated = (history.report_generated or 0) + 1
                db.commit()
                db.refresh(history)

                # 在 session 内将 ORM 字段实体化为普通 dict，避免 detached instance
                history_data = {
                    "view_count": history.view_count or 1,
                    "analysis_count": history.analysis_count or 0,
                    "report_count": history.report_generated or 1,
                    "first_viewed": history.first_viewed_at.isoformat() if history.first_viewed_at else None,
                    "last_viewed": history.last_viewed_at.isoformat() if history.last_viewed_at else None,
                    "notes": history.notes,
                }

        notes = self._parse_history_notes(history_data.get("notes"))
        layered_short = self._load_layered_short_memory(user_id=user_id, news_id=news_id, notes=notes)
        notes["short_term_memory"] = layered_short
        user_profile = self._load_user_profile(user_id)
        memory_context = self._build_memory_context(notes, profile=user_profile)
        search_archives = await self.get_search_archives(limit=30)
        related_searches = []
        title_hint = (detail.get("news", {}).get("title") or "").lower()
        for item in search_archives:
            topic = (item.get("search_topic") or item.get("title") or "").lower()
            if topic and (topic in title_hint or any(k in title_hint for k in topic.split()[:2])):
                related_searches.append(item)
        related_searches = related_searches[:10]
        user_history_stats = {
            "view_count": history_data["view_count"],
            "analysis_count": history_data["analysis_count"],
            "report_count": history_data["report_count"],
        }

        report_prompt = (
            f"新闻信息：{json.dumps(detail.get('news', {}), ensure_ascii=False)}\n"
            f"图谱信息：节点{len(detail.get('graph', {}).get('nodes', []))}，关系{len(detail.get('graph', {}).get('edges', []))}\n"
            f"用户历史：{json.dumps(user_history_stats, ensure_ascii=False)}\n"
            f"按图索骥记录：{json.dumps(notes.get('analysis_runs', []), ensure_ascii=False)}\n"
            f"追问记录：{json.dumps(notes.get('followups', []), ensure_ascii=False)}\n"
            f"短期记忆摘要：{memory_context.get('short_text', '')}\n"
            f"长期记忆摘要：{memory_context.get('long_text', '')}\n"
            f"作者历史搜索档案：{json.dumps(related_searches, ensure_ascii=False)}\n\n"
            "请生成完整中文雷达分析报告，包含：核心结论、事件时间线、实体关系、竞争合作、风险机会、可执行建议。"
        )
        report_markdown = self.analysis_agent.run(report_prompt)

        report = {
            "news": detail["news"],
            "graph": detail["graph"],
            "user_history": {
                "view_count": history_data["view_count"],
                "analysis_count": history_data["analysis_count"],
                "report_count": history_data["report_count"],
                "first_viewed": history_data["first_viewed"],
                "last_viewed": history_data["last_viewed"],
                "notes": history_data["notes"],
                "analysis_runs": notes.get("analysis_runs", []),
                "followups": notes.get("followups", []),
                "short_term_memory": layered_short,
                "long_term_memory": notes.get("long_term_memory", {}),
                "user_profile": user_profile,
            },
            "entities_summary": self._generate_entities_summary(detail["graph"]["nodes"]),
            "related_entities": self._find_related_entities(news_id),
            "related_searches": related_searches,
            "report_markdown": report_markdown,
            "generated_at": datetime.utcnow().isoformat()
        }

        return report

    def _generate_entities_summary(self, nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成实体摘要"""
        entities = [n for n in nodes if n.get("type") != "News"]
        
        by_type = {}
        for entity in entities:
            etype = entity.get("type", "other")
            if etype not in by_type:
                by_type[etype] = []
            by_type[etype].append(entity.get("name"))

        return {
            "total_count": len(entities),
            "by_type": by_type,
            "entity_list": entities
        }

    def _find_related_entities(self, news_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """查找相关实体（通过共同出现在其他新闻中）"""
        records = neo4j_client.run_query(
            """
            MATCH (n:News {id: $news_id})-[:MENTIONS]->(e:Entity)<-[:MENTIONS]-(other:News)
            WHERE other.id <> $news_id
            WITH e, count(other) AS co_occurrence
            ORDER BY co_occurrence DESC
            LIMIT $limit
            RETURN e.name AS name, e.type AS type, co_occurrence
            """,
            {"news_id": news_id, "limit": limit},
        )
        return [
            {
                "name": r["name"],
                "type": r["type"],
                "co_occurrence": r["co_occurrence"]
            }
            for r in records
        ]


news_radar_service = NewsRadarService()

