"""新闻雷达缓存服务 - 使用Redis缓存新闻数据"""

import json
import os
import threading
import time
from collections import OrderedDict
from typing import Dict, List, Optional, Any
from loguru import logger

try:
    import redis
    from config import get_config
    
    config = get_config()
    
    # 初始化Redis客户端
    redis_client = redis.from_url(
        config.cache.redis_url,
        decode_responses=True
    )
    REDIS_AVAILABLE = True
    logger.info("[NewsCache] Redis缓存已启用")
except Exception as e:
    redis_client = None
    REDIS_AVAILABLE = False
    logger.warning(f"[NewsCache] Redis不可用，缓存功能禁用: {e}")


class NewsCache:
    """新闻雷达缓存管理"""
    
    # 缓存键前缀
    HOT_NEWS_KEY = "news:hot"
    SEARCH_KEY_PREFIX = "news:search:"
    DETAIL_KEY_PREFIX = "news:detail:"
    ENTITY_KEY_PREFIX = "news:entity:"
    
    # 缓存过期时间
    HOT_NEWS_TTL = 300  # 5分钟
    SEARCH_TTL = 600  # 10分钟
    DETAIL_TTL = 1800  # 30分钟
    ENTITY_TTL = 600  # 10分钟

    # L1 内存缓存（进程内）
    L1_MAX_SIZE = int(os.getenv("NEWS_CACHE_L1_MAX_SIZE", "300"))
    _l1_lock = threading.Lock()
    _l1_cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    _stats = {
        "l1_hits": 0,
        "l2_hits": 0,
        "misses": 0,
    }

    @staticmethod
    def _normalize_token(value: str) -> str:
        return (value or "").strip()

    @staticmethod
    def _get_l1(cache_key: str) -> Optional[Any]:
        now = time.time()
        with NewsCache._l1_lock:
            item = NewsCache._l1_cache.get(cache_key)
            if not item:
                return None
            expires_at, payload = item
            if expires_at < now:
                NewsCache._l1_cache.pop(cache_key, None)
                return None
            NewsCache._l1_cache.move_to_end(cache_key)
            return payload

    @staticmethod
    def _set_l1(cache_key: str, payload: Any, ttl_seconds: int) -> None:
        expires_at = time.time() + max(1, int(ttl_seconds))
        with NewsCache._l1_lock:
            NewsCache._l1_cache[cache_key] = (expires_at, payload)
            NewsCache._l1_cache.move_to_end(cache_key)
            while len(NewsCache._l1_cache) > NewsCache.L1_MAX_SIZE:
                NewsCache._l1_cache.popitem(last=False)

    @staticmethod
    def _delete_l1(cache_key: str) -> int:
        """从 L1 删除指定键，返回实际删除数量（0 或 1）。"""
        with NewsCache._l1_lock:
            existed = cache_key in NewsCache._l1_cache
            NewsCache._l1_cache.pop(cache_key, None)
            return 1 if existed else 0

    @staticmethod
    def _record_hit(layer: str) -> None:
        if layer == "l1":
            NewsCache._stats["l1_hits"] += 1
        elif layer == "l2":
            NewsCache._stats["l2_hits"] += 1

    @staticmethod
    def _record_miss() -> None:
        NewsCache._stats["misses"] += 1
    
    @staticmethod
    def get_hot_news() -> Optional[List[Dict[str, Any]]]:
        """获取缓存的热榜新闻"""
        key = NewsCache.HOT_NEWS_KEY
        l1_payload = NewsCache._get_l1(key)
        if l1_payload is not None:
            NewsCache._record_hit("l1")
            logger.debug("[NewsCache] 热榜 L1缓存命中")
            return l1_payload

        if not REDIS_AVAILABLE:
            NewsCache._record_miss()
            return None

        try:
            data = redis_client.get(key)
            if data:
                payload = json.loads(data)
                NewsCache._set_l1(key, payload, NewsCache.HOT_NEWS_TTL)
                NewsCache._record_hit("l2")
                logger.debug("[NewsCache] 热榜 L2缓存命中")
                return payload
            NewsCache._record_miss()
            return None
        except Exception as e:
            logger.warning(f"[NewsCache] 读取热榜缓存失败: {e}")
            return None
    
    @staticmethod
    def set_hot_news(news_list: List[Dict[str, Any]]) -> None:
        """缓存热榜新闻"""
        key = NewsCache.HOT_NEWS_KEY
        NewsCache._set_l1(key, news_list, NewsCache.HOT_NEWS_TTL)
        if not REDIS_AVAILABLE:
            return
        
        try:
            redis_client.setex(
                key,
                NewsCache.HOT_NEWS_TTL,
                json.dumps(news_list, ensure_ascii=False)
            )
            logger.debug(f"[NewsCache] 热榜已缓存，TTL={NewsCache.HOT_NEWS_TTL}秒")
        except Exception as e:
            logger.warning(f"[NewsCache] 缓存热榜失败: {e}")
    
    @staticmethod
    def get_search_results(query: str) -> Optional[List[Dict[str, Any]]]:
        """获取缓存的搜索结果"""
        normalized_query = NewsCache._normalize_token(query)
        key = f"{NewsCache.SEARCH_KEY_PREFIX}{normalized_query}"
        l1_payload = NewsCache._get_l1(key)
        if l1_payload is not None:
            NewsCache._record_hit("l1")
            logger.debug(f"[NewsCache] 搜索 L1缓存命中: '{normalized_query[:30]}...'")
            return l1_payload

        if not REDIS_AVAILABLE:
            NewsCache._record_miss()
            return None

        try:
            data = redis_client.get(key)
            if data:
                payload = json.loads(data)
                NewsCache._set_l1(key, payload, NewsCache.SEARCH_TTL)
                NewsCache._record_hit("l2")
                logger.debug(f"[NewsCache] 搜索 L2缓存命中: '{normalized_query[:30]}...'")
                return payload
            NewsCache._record_miss()
            return None
        except Exception as e:
            logger.warning(f"[NewsCache] 读取搜索缓存失败: {e}")
            return None
    
    @staticmethod
    def set_search_results(query: str, results: List[Dict[str, Any]]) -> None:
        """缓存搜索结果"""
        normalized_query = NewsCache._normalize_token(query)
        key = f"{NewsCache.SEARCH_KEY_PREFIX}{normalized_query}"
        NewsCache._set_l1(key, results, NewsCache.SEARCH_TTL)
        if not REDIS_AVAILABLE:
            return
        
        try:
            redis_client.setex(
                key,
                NewsCache.SEARCH_TTL,
                json.dumps(results, ensure_ascii=False)
            )
            logger.debug(f"[NewsCache] 搜索结果已缓存: '{normalized_query[:30]}...', TTL={NewsCache.SEARCH_TTL}秒")
        except Exception as e:
            logger.warning(f"[NewsCache] 缓存搜索结果失败: {e}")
    
    @staticmethod
    def get_news_detail(news_id: str) -> Optional[Dict[str, Any]]:
        """获取缓存的新闻详情"""
        normalized_news_id = NewsCache._normalize_token(news_id)
        key = f"{NewsCache.DETAIL_KEY_PREFIX}{normalized_news_id}"
        l1_payload = NewsCache._get_l1(key)
        if l1_payload is not None:
            NewsCache._record_hit("l1")
            logger.debug(f"[NewsCache] 详情 L1缓存命中: {normalized_news_id}")
            return l1_payload

        if not REDIS_AVAILABLE:
            NewsCache._record_miss()
            return None

        try:
            data = redis_client.get(key)
            if data:
                payload = json.loads(data)
                NewsCache._set_l1(key, payload, NewsCache.DETAIL_TTL)
                NewsCache._record_hit("l2")
                logger.debug(f"[NewsCache] 详情 L2缓存命中: {normalized_news_id}")
                return payload
            NewsCache._record_miss()
            return None
        except Exception as e:
            logger.warning(f"[NewsCache] 读取详情缓存失败: {e}")
            return None
    
    @staticmethod
    def set_news_detail(news_id: str, detail: Dict[str, Any]) -> None:
        """缓存新闻详情"""
        normalized_news_id = NewsCache._normalize_token(news_id)
        key = f"{NewsCache.DETAIL_KEY_PREFIX}{normalized_news_id}"
        NewsCache._set_l1(key, detail, NewsCache.DETAIL_TTL)
        if not REDIS_AVAILABLE:
            return
        
        try:
            redis_client.setex(
                key,
                NewsCache.DETAIL_TTL,
                json.dumps(detail, ensure_ascii=False)
            )
            logger.debug(f"[NewsCache] 详情已缓存: {normalized_news_id}, TTL={NewsCache.DETAIL_TTL}秒")
        except Exception as e:
            logger.warning(f"[NewsCache] 缓存详情失败: {e}")
    
    @staticmethod
    def get_entity_analysis(entity_key: str) -> Optional[Dict[str, Any]]:
        """获取缓存的实体分析结果"""
        normalized_entity_key = NewsCache._normalize_token(entity_key)
        key = f"{NewsCache.ENTITY_KEY_PREFIX}{normalized_entity_key}"
        l1_payload = NewsCache._get_l1(key)
        if l1_payload is not None:
            NewsCache._record_hit("l1")
            logger.debug(f"[NewsCache] 实体分析 L1缓存命中: {normalized_entity_key}")
            return l1_payload

        if not REDIS_AVAILABLE:
            NewsCache._record_miss()
            return None

        try:
            data = redis_client.get(key)
            if data:
                payload = json.loads(data)
                NewsCache._set_l1(key, payload, NewsCache.ENTITY_TTL)
                NewsCache._record_hit("l2")
                logger.debug(f"[NewsCache] 实体分析 L2缓存命中: {normalized_entity_key}")
                return payload
            NewsCache._record_miss()
            return None
        except Exception as e:
            logger.warning(f"[NewsCache] 读取实体分析缓存失败: {e}")
            return None
    
    @staticmethod
    def set_entity_analysis(entity_key: str, analysis: Dict[str, Any]) -> None:
        """缓存实体分析结果"""
        normalized_entity_key = NewsCache._normalize_token(entity_key)
        key = f"{NewsCache.ENTITY_KEY_PREFIX}{normalized_entity_key}"
        NewsCache._set_l1(key, analysis, NewsCache.ENTITY_TTL)
        if not REDIS_AVAILABLE:
            return
        
        try:
            redis_client.setex(
                key,
                NewsCache.ENTITY_TTL,
                json.dumps(analysis, ensure_ascii=False)
            )
            logger.debug(f"[NewsCache] 实体分析已缓存: {normalized_entity_key}, TTL={NewsCache.ENTITY_TTL}秒")
        except Exception as e:
            logger.warning(f"[NewsCache] 缓存实体分析失败: {e}")
    
    @staticmethod
    def invalidate_hot_news() -> None:
        """清除热榜缓存（新闻更新时调用）"""
        NewsCache._delete_l1(NewsCache.HOT_NEWS_KEY)
        if not REDIS_AVAILABLE:
            return
        
        try:
            redis_client.delete(NewsCache.HOT_NEWS_KEY)
            logger.debug("[NewsCache] 热榜缓存已清除")
        except Exception as e:
            logger.warning(f"[NewsCache] 清除热榜缓存失败: {e}")
    
    @staticmethod
    def invalidate_news_detail(news_id: str) -> None:
        """清除指定新闻的详情缓存"""
        normalized_news_id = NewsCache._normalize_token(news_id)
        key = f"{NewsCache.DETAIL_KEY_PREFIX}{normalized_news_id}"
        NewsCache._delete_l1(key)
        if not REDIS_AVAILABLE:
            return
        
        try:
            redis_client.delete(key)
            logger.debug(f"[NewsCache] 新闻详情缓存已清除: {normalized_news_id}")
        except Exception as e:
            logger.warning(f"[NewsCache] 清除新闻详情缓存失败: {e}")
    
    @staticmethod
    def invalidate_all() -> None:
        """清除所有新闻相关缓存"""
        with NewsCache._l1_lock:
            NewsCache._l1_cache.clear()
        if not REDIS_AVAILABLE:
            return
        
        try:
            keys = redis_client.keys("news:*")
            if keys:
                redis_client.delete(*keys)
                logger.info(f"[NewsCache] 已清除 {len(keys)} 个新闻缓存")
        except Exception as e:
            logger.warning(f"[NewsCache] 清除所有缓存失败: {e}")

    @staticmethod
    def get_stats() -> Dict[str, Any]:
        """返回缓存统计信息。"""
        redis_keys = 0
        if REDIS_AVAILABLE:
            try:
                redis_keys = int(redis_client.dbsize())
            except Exception:
                redis_keys = -1
        return {
            "backend": "redis" if REDIS_AVAILABLE else "memory-only",
            "l1_entries": len(NewsCache._l1_cache),
            "l2_keys": redis_keys,
            "stats": dict(NewsCache._stats),
        }


# 创建全局实例
news_cache = NewsCache()
