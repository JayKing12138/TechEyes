"""新闻趋势分析服务 - 分析热门话题和实体趋势"""

from typing import Dict, List, Any,  Optional
from datetime import datetime, timedelta
from loguru import logger
from collections import Counter

from services.neo4j_client import neo4j_client
from services.news_cache import news_cache


class NewsTrendAnalyzer:
    """新闻趋势分析器"""
    
    @staticmethod
    def get_trending_entities(days: int = 7, limit: int = 20) -> List[Dict[str, Any]]:
        """获取趋势实体（最近N天最频繁出现的实体）"""
        cache_key = f"trending_entities_{days}d"
        cached = news_cache.get_entity_analysis(cache_key)
        if cached:
            logger.info(f"[TrendAnalyzer] 从缓存返回趋势实体")
            return cached[:limit]
        
        try:
            # 计算时间范围
            cutoff = datetime.utcnow() - timedelta(days=days)
            cutoff_str = cutoff.isoformat()
            
            records = neo4j_client.run_query(
                """
                MATCH (n:News)-[:MENTIONS]->(e:Entity)
                WHERE datetime(n.created_at) >= datetime($cutoff)
                WITH e, count(n) as news_count
                RETURN e.id as entity_id, 
                       e.name as name, 
                       e.type as type, 
                       news_count
                ORDER BY news_count DESC
                LIMIT $limit
                """,
                {"cutoff": cutoff_str, "limit": limit * 2}
            )
            
            trending = []
            for r in records:
                trending.append({
                    "entity_id": r["entity_id"],
                    "name": r["name"],
                    "type": r["type"],
                    "news_count": r["news_count"],
                    "trend_score": float(r["news_count"]) / max(days, 1)
                })
            
            # 缓存结果
            news_cache.set_entity_analysis(cache_key, trending)
            
            logger.info(f"[TrendAnalyzer] 分析完成: {len(trending)} 个趋势实体")
            return trending[:limit]
            
        except Exception as e:
            logger.error(f"[TrendAnalyzer] 趋势实体分析失败: {e}", exc_info=True)
            return cached[:limit] if cached else []
    
    @staticmethod
    def get_hot_topics(days: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
        """获取热门话题（基于实体共现分析）"""
        cache_key = f"hot_topics_{days}d"
        cached = news_cache.get_entity_analysis(cache_key)
        if cached:
            logger.info(f"[TrendAnalyzer] 从缓存返回热门话题")
            return cached[:limit]
        
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            cutoff_str = cutoff.isoformat()
            
            # 查找共现频率高的实体组合
            records = neo4j_client.run_query(
                """
                MATCH (n:News)-[:MENTIONS]->(e1:Entity)
                WHERE datetime(n.created_at) >= datetime($cutoff)
                MATCH (n)-[:MENTIONS]->(e2:Entity)
                WHERE e1.id < e2.id
                WITH e1, e2, count(DISTINCT n) as co_occurrence
                WHERE co_occurrence >= 2
                RETURN e1.name as entity1, 
                       e2.name as entity2,
                       e1.type as type1,
                       e2.type as type2,
                       co_occurrence
                ORDER BY co_occurrence DESC
                LIMIT $limit
                """,
                {"cutoff": cutoff_str, "limit": limit * 2}
            )
            
            topics = []
            for r in records:
                topics.append({
                    "entities": [r["entity1"], r["entity2"]],
                    "types": [r["type1"], r["type2"]],
                    "co_occurrence": r["co_occurrence"],
                    "topic_score": float(r["co_occurrence"])
                })
            
            # 缓存结果
            news_cache.set_entity_analysis(cache_key, topics)
            
            logger.info(f"[TrendAnalyzer] 分析完成: {len(topics)} 个热门话题")
            return topics[:limit]
            
        except Exception as e:
            logger.error(f"[TrendAnalyzer] 热门话题分析失败: {e}", exc_info=True)
            return cached[:limit] if cached else []
    
    @staticmethod
    def get_entity_timeline(entity_name: str, days: int = 30) -> Dict[str, Any]:
        """获取实体的时间线（每天出现的新闻数）"""
        cache_key = f"entity_timeline_{entity_name}_{days}d"
        cached = news_cache.get_entity_analysis(cache_key)
        if cached:
            logger.info(f"[TrendAnalyzer] 从缓存返回实体时间线: {entity_name}")
            return cached
        
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            cutoff_str = cutoff.isoformat()
            
            records = neo4j_client.run_query(
                """
                MATCH (n:News)-[:MENTIONS]->(e:Entity {name: $name})
                WHERE datetime(n.created_at) >= datetime($cutoff)
                RETURN date(datetime(n.created_at)) as day, count(n) as count
                ORDER BY day ASC
                """,
                {"name": entity_name, "cutoff": cutoff_str}
            )
            
            timeline = []
            for r in records:
                timeline.append({
                    "date": str(r["day"]),
                    "count": r["count"]
                })
            
            result = {
                "entity": entity_name,
                "days": days,
                "timeline": timeline,
                "total_news": sum(item["count"] for item in timeline)
            }
            
            # 缓存结果
            news_cache.set_entity_analysis(cache_key, result)
            
            logger.info(f"[TrendAnalyzer] 实体时间线分析完成: {entity_name}")
            return result
            
        except Exception as e:
            logger.error(f"[TrendAnalyzer] 实体时间线分析失败: {e}", exc_info=True)
            return cached if cached else {"entity": entity_name, "days": days, "timeline": [], "total_news": 0}
    
    @staticmethod
    def analyze_news_sentiment(news_ids: List[str]) -> Dict[str, Any]:
        """分析新闻情感倾向（简化版，基于关键词）"""
        # 这里是简化实现，可以后续集成更复杂的情感分析模型
        positive_keywords = ["突破", "创新", "成功", "领先", "增长", "提升", "优化", "合作"]
        negative_keywords = ["失败", "下降", "问题", "危机", "风险", "裁员", "亏损", "延迟"]
        
        try:
            records = neo4j_client.run_query(
                """
                MATCH (n:News)
                WHERE n.id IN $news_ids
                RETURN n.id as id, n.title as title, n.snippet as snippet
                """,
                {"news_ids": news_ids}
            )
            
            sentiment_scores = {"positive": 0, "negative": 0, "neutral": 0}
            
            for r in records:
                text = f"{r.get('title', '')} {r.get('snippet', '')}".lower()
                pos_count = sum(1 for kw in positive_keywords if kw in text)
                neg_count = sum(1 for kw in negative_keywords if kw in text)
                
                if pos_count > neg_count:
                    sentiment_scores["positive"] += 1
                elif neg_count > pos_count:
                    sentiment_scores["negative"] += 1
                else:
                    sentiment_scores["neutral"] += 1
            
            total = sum(sentiment_scores.values())
            if total > 0:
                for key in sentiment_scores:
                    sentiment_scores[f"{key}_percent"] = round(sentiment_scores[key] / total * 100, 1)
            
            return sentiment_scores
            
        except Exception as e:
            logger.error(f"[TrendAnalyzer] 情感分析失败: {e}", exc_info=True)
            return {"positive": 0, "negative": 0, "neutral": 0}


# 创建全局实例
trend_analyzer = NewsTrendAnalyzer()
