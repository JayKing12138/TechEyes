"""Web/News Agent - 外部实时信息检索"""

from typing import List, Dict
from loguru import logger
from tools.search_tools import TavilyTool, SERPAPITool
from config import get_config


class WebNewsAgent:
    """Web/News Agent - 负责外部实时信息检索"""
    
    def __init__(self):
        self.config = get_config()
        
        # 初始化搜索工具
        self.primary_search = TavilyTool() if self.config.search.tavily_api_key else SERPAPITool()
        self.fallback_search = SERPAPITool() if self.config.search.tavily_api_key else None
        
        # 可信源白名单（可配置）
        self.trusted_domains = [
            "36kr.com",
            "sina.com.cn",
            "163.com",
            "sohu.com",
            "cnbc.com",
            "techcrunch.com",
            "theverge.com",
            "wired.com",
            "mit.edu",
            "arxiv.org",
        ]
    
    async def search_web(
        self,
        query: str,
        max_results: int = 5,
        time_filter: str = None,
        enable_domain_filter: bool = True,
        force_search: bool = False
    ) -> List[Dict]:
        """
        搜索Web信息
        
        Args:
            query: 查询文本
            max_results: 最大结果数
            time_filter: 时间过滤（"day", "week", "month", "year"）
            enable_domain_filter: 是否启用域名白名单过滤
            force_search: 强制搜索（跳过关键词检测，信任上游路由决策）
        
        Returns:
            搜索结果列表
        """
        try:
            logger.info(f"[WebNewsAgent] 开始搜索: query='{query}', time_filter={time_filter}, force={force_search}")
            
            # 1. 时效关键词触发检测（可被 force_search 跳过）
            if not force_search and not self._should_search_web(query):
                logger.info("[WebNewsAgent] 问题不需要Web检索（关键词检测未通过）")
                return []
            
            # 2. 执行搜索
            results = await self._execute_search(query, max_results)
            
            # 3. 去重（基于URL）
            results = self._deduplicate_results(results)
            
            # 4. 可信源过滤
            if enable_domain_filter:
                results = self._filter_by_trusted_domains(results)
            
            # 5. 标记来源
            for result in results:
                result["retrieval_method"] = "news"
            
            logger.info(f"[WebNewsAgent] 搜索完成: 返回 {len(results)} 个结果")
            return results
            
        except Exception as e:
            logger.error(f"[WebNewsAgent] 搜索失败: {e}", exc_info=True)
            return []
    
    def _should_search_web(self, query: str) -> bool:
        """判断是否需要Web检索（时效关键词触发）"""
        time_keywords = [
            "最新", "近期", "最近", "今年", "今天", "昨天",
            "现在", "当前", "目前", "实时", "即时",
            "latest", "recent", "current", "now", "today"
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in time_keywords)
    
    async def _execute_search(self, query: str, max_results: int) -> List[Dict]:
        """执行搜索"""
        try:
            # 尝试主搜索工具
            results = await self.primary_search.search(query, max_results=max_results)
            return results
            
        except Exception as e:
            logger.warning(f"[WebNewsAgent] 主搜索失败: {e}，尝试备用搜索")
            
            # 尝试备用搜索
            if self.fallback_search:
                try:
                    results = await self.fallback_search.search(query, max_results=max_results)
                    return results
                except Exception as e2:
                    logger.error(f"[WebNewsAgent] 备用搜索也失败: {e2}")
            
            return []
    
    def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """基于URL去重"""
        if not results:
            return results
        
        seen_urls = set()
        deduped = []
        
        for result in results:
            url = result.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                deduped.append(result)
        
        if len(deduped) < len(results):
            logger.info(f"[WebNewsAgent] URL去重: {len(results)} → {len(deduped)}")
        
        return deduped
    
    def _filter_by_trusted_domains(self, results: List[Dict]) -> List[Dict]:
        """按可信域名过滤"""
        if not results:
            return results
        
        filtered = []
        for result in results:
            url = result.get("url", "")
            
            # 检查是否在白名单中
            is_trusted = any(domain in url for domain in self.trusted_domains)
            
            if is_trusted:
                result["source_quality"] = "trusted"
                filtered.append(result)
            else:
                result["source_quality"] = "unknown"
                # 也保留，但标记为未知
                filtered.append(result)
        
        trusted_count = sum(1 for r in filtered if r.get("source_quality") == "trusted")
        logger.info(f"[WebNewsAgent] 域名过滤: {len(results)} → {len(filtered)} (可信: {trusted_count})")
        
        return filtered
