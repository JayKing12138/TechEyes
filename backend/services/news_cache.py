"""新闻雷达缓存服务 - 使用Redis缓存新闻数据"""

import json
from typing import Dict, List, Optional, Any
from datetime import timedelta
from loguru import logger

try:
    import redis
    from config import get_config
    
    config = get_config()
    
    # 初始化Redis客户端
    redis_client = redis.from_url(
        config.redis.redis_url,
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
    
    @staticmethod
    def get_hot_news() -> Optional[List[Dict[str, Any]]]:
        """获取缓存的热榜新闻"""
        if not REDIS_AVAILABLE:
            return None
        
        try:
            data = redis_client.get(NewsCache.HOT_NEWS_KEY)
            if data:
                logger.debug("[NewsCache] 热榜缓存命中")
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning(f"[NewsCache] 读取热榜缓存失败: {e}")
            return None
    
    @staticmethod
    def set_hot_news(news_list: List[Dict[str, Any]]) -> None:
        """缓存热榜新闻"""
        if not REDIS_AVAILABLE:
            return
        
        try:
            redis_client.setex(
                NewsCache.HOT_NEWS_KEY,
                NewsCache.HOT_NEWS_TTL,
                json.dumps(news_list, ensure_ascii=False)
            )
            logger.debug(f"[NewsCache] 热榜已缓存，TTL={NewsCache.HOT_NEWS_TTL}秒")
        except Exception as e:
            logger.warning(f"[NewsCache] 缓存热榜失败: {e}")
    
    @staticmethod
    def get_search_results(query: str) -> Optional[List[Dict[str, Any]]]:
        """获取缓存的搜索结果"""
        if not REDIS_AVAILABLE:
            return None
        
        try:
            key = f"{NewsCache.SEARCH_KEY_PREFIX}{query}"
            data = redis_client.get(key)
            if data:
                logger.debug(f"[NewsCache] 搜索缓存命中: '{query[:30]}...'")
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning(f"[NewsCache] 读取搜索缓存失败: {e}")
            return None
    
    @staticmethod
    def set_search_results(query: str, results: List[Dict[str, Any]]) -> None:
        """缓存搜索结果"""
        if not REDIS_AVAILABLE:
            return
        
        try:
            key = f"{NewsCache.SEARCH_KEY_PREFIX}{query}"
            redis_client.setex(
                key,
                NewsCache.SEARCH_TTL,
                json.dumps(results, ensure_ascii=False)
            )
            logger.debug(f"[NewsCache] 搜索结果已缓存: '{query[:30]}...', TTL={NewsCache.SEARCH_TTL}秒")
        except Exception as e:
            logger.warning(f"[NewsCache] 缓存搜索结果失败: {e}")
    
    @staticmethod
    def get_news_detail(news_id: str) -> Optional[Dict[str, Any]]:
        """获取缓存的新闻详情"""
        if not REDIS_AVAILABLE:
            return None
        
        try:
            key = f"{NewsCache.DETAIL_KEY_PREFIX}{news_id}"
            data = redis_client.get(key)
            if data:
                logger.debug(f"[NewsCache] 详情缓存命中: {news_id}")
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning(f"[NewsCache] 读取详情缓存失败: {e}")
            return None
    
    @staticmethod
    def set_news_detail(news_id: str, detail: Dict[str, Any]) -> None:
        """缓存新闻详情"""
        if not REDIS_AVAILABLE:
            return
        
        try:
            key = f"{NewsCache.DETAIL_KEY_PREFIX}{news_id}"
            redis_client.setex(
                key,
                NewsCache.DETAIL_TTL,
                json.dumps(detail, ensure_ascii=False)
            )
            logger.debug(f"[NewsCache] 详情已缓存: {news_id}, TTL={NewsCache.DETAIL_TTL}秒")
        except Exception as e:
            logger.warning(f"[NewsCache] 缓存详情失败: {e}")
    
    @staticmethod
    def get_entity_analysis(entity_key: str) -> Optional[Dict[str, Any]]:
        """获取缓存的实体分析结果"""
        if not REDIS_AVAILABLE:
            return None
        
        try:
            key = f"{NewsCache.ENTITY_KEY_PREFIX}{entity_key}"
            data = redis_client.get(key)
            if data:
                logger.debug(f"[NewsCache] 实体分析缓存命中: {entity_key}")
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning(f"[NewsCache] 读取实体分析缓存失败: {e}")
            return None
    
    @staticmethod
    def set_entity_analysis(entity_key: str, analysis: Dict[str, Any]) -> None:
        """缓存实体分析结果"""
        if not REDIS_AVAILABLE:
            return
        
        try:
            key = f"{NewsCache.ENTITY_KEY_PREFIX}{entity_key}"
            redis_client.setex(
                key,
                NewsCache.ENTITY_TTL,
                json.dumps(analysis, ensure_ascii=False)
            )
            logger.debug(f"[NewsCache] 实体分析已缓存: {entity_key}, TTL={NewsCache.ENTITY_TTL}秒")
        except Exception as e:
            logger.warning(f"[NewsCache] 缓存实体分析失败: {e}")
    
    @staticmethod
    def invalidate_hot_news() -> None:
        """清除热榜缓存（新闻更新时调用）"""
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
        if not REDIS_AVAILABLE:
            return
        
        try:
            key = f"{NewsCache.DETAIL_KEY_PREFIX}{news_id}"
            redis_client.delete(key)
            logger.debug(f"[NewsCache] 新闻详情缓存已清除: {news_id}")
        except Exception as e:
            logger.warning(f"[NewsCache] 清除新闻详情缓存失败: {e}")
    
    @staticmethod
    def invalidate_all() -> None:
        """清除所有新闻相关缓存"""
        if not REDIS_AVAILABLE:
            return
        
        try:
            keys = redis_client.keys("news:*")
            if keys:
                redis_client.delete(*keys)
                logger.info(f"[NewsCache] 已清除 {len(keys)} 个新闻缓存")
        except Exception as e:
            logger.warning(f"[NewsCache] 清除所有缓存失败: {e}")


# 创建全局实例
news_cache = NewsCache()
