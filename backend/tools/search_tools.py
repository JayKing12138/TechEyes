"""Tools 工具模块"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import httpx
from loguru import logger

from config import get_config

config = get_config()

class SearchTool(ABC):
    """搜索工具基类"""
    
    @abstractmethod
    async def search(self, query: str, max_results: int = 5, days: int = 7, topic: str = "news") -> list[Dict[str, Any]]:
        """执行搜索
        
        Args:
            query: 搜索关键词
            max_results: 返回结果数量
            days: 搜索最近几天的内容
            topic: 搜索主题类型（news/general）
        """
        pass

class SERPAPITool(SearchTool):
    """SERPAPI 搜索工具"""
    
    def __init__(self):
        self.api_key = config.search.serpapi_api_key
        self.base_url = "https://serpapi.com/search"
    
    async def search(self, query: str, max_results: int = 5, days: int = 7, topic: str = "news") -> list[Dict[str, Any]]:
        """使用 SERPAPI 搜索（days和topic参数用于接口兼容，SERPAPI不支持）"""
        if not self.api_key:
            logger.warning("⚠️ SERPAPI 未配置 API Key")
            return []
        
        try:
            logger.info(
                f"[FunctionCall] SERPAPITool.search query='{query[:60]}' max_results={max_results} endpoint={self.base_url}"
            )
            params = {
                "q": query,
                "api_key": self.api_key,
                "num": max_results,
                "engine": "google"
            }
            
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                results = []
                for item in data.get("organic_results", [])[:max_results]:
                    results.append({
                        "title": item.get("title"),
                        "url": item.get("link"),
                        "snippet": item.get("snippet"),
                        "source": "SERPAPI"
                    })
                
                logger.info(f"[FunctionReturn] SERPAPITool.search status={response.status_code} results={len(results)}")
                logger.info(f"✅ SERPAPI 搜索成功: {query} ({len(results)} 结果)")
                return results
        
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ SERPAPI API 错误 [{e.response.status_code}]: {e.response.text[:200]}")
            return []
        except httpx.TimeoutException:
            logger.error(f"❌ SERPAPI 请求超时: {query}")
            return []
        except Exception as e:
            logger.error(f"❌ SERPAPI 搜索异常: {type(e).__name__} - {str(e)}")
            return []

class TavilyTool(SearchTool):
    """TAVILY 搜索工具"""
    
    def __init__(self):
        self.api_key = config.search.tavily_api_key
        self.base_url = "https://api.tavily.com/search"
    
    async def search(self, query: str, max_results: int = 5, days: int = 7, topic: str = "news") -> list[Dict[str, Any]]:
        """使用 TAVILY 搜索
        
        Args:
            query: 搜索关键词
            max_results: 返回结果数量
            days: 搜索最近几天的内容（默认7天）
            topic: 搜索主题类型，"news"只搜索新闻，"general"搜索所有内容
        """
        if not self.api_key:
            logger.warning("⚠️ TAVILY 未配置 API Key")
            return []
        
        try:
            logger.info(
                f"[FunctionCall] TavilyTool.search query='{query[:60]}' max_results={max_results} topic={topic} days={days} endpoint={self.base_url}"
            )
            payload = {
                "api_key": self.api_key,
                "query": query,
                "max_results": max_results,
                "include_raw_content": config.search.tavily_include_raw_content,
                "topic": topic,  # 限定为新闻搜索
                "days": days,  # 只搜索最近N天的新闻
                "search_depth": "advanced"  # 使用高级搜索获得更准确的结果
            }
            
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(self.base_url, json=payload)
                response.raise_for_status()
                data = response.json()
                
                results = []
                for item in data.get("results", [])[:max_results]:
                    results.append({
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "snippet": item.get("content"),
                        "source": "TAVILY",
                        "raw_content": item.get("raw_content") if config.search.tavily_include_raw_content else None
                    })
                
                logger.info(f"[FunctionReturn] TavilyTool.search status={response.status_code} results={len(results)}")
                logger.info(f"✅ TAVILY 搜索成功: {query} ({len(results)} 结果)")
                return results
        
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ TAVILY API 错误 [{e.response.status_code}]: {e.response.text[:200]}")
            return []
        except httpx.TimeoutException:
            logger.error(f"❌ TAVILY 请求超时: {query}")
            return []
        except Exception as e:
            logger.error(f"❌ TAVILY 搜索异常: {type(e).__name__} - {str(e)}")
            return []

class DocumentProcessorTool:
    """文档处理工具（MineRU）"""
    
    def __init__(self):
        self.api_key = config.document.mineru_api_key
        self.api_url = config.document.mineru_api_url
    
    async def parse_document(self, file_path: str) -> Optional[Dict[str, Any]]:
        """解析文档"""
        if not self.api_key:
            logger.warning("⚠️ MineRU 未配置")
            return None
        
        try:
            logger.info(f"[FunctionCall] DocumentProcessorTool.parse_document file_path={file_path}")
            with open(file_path, 'rb') as f:
                files = {'file': f}
                headers = {'Authorization': f'Bearer {self.api_key}'}
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.api_url}/api/parse",
                        headers=headers,
                        files=files
                    )
                    
                    if response.status_code == 200:
                        logger.info(f"[FunctionReturn] DocumentProcessorTool.parse_document status={response.status_code}")
                        logger.info(f"✅ 文档解析成功: {file_path}")
                        return response.json()
                    else:
                        logger.error(f"❌ 文档解析失败: {response.status_code}")
                        return None
        
        except Exception as e:
            logger.error(f"❌ 文档处理异常: {e}")
            return None

# 工厂函数
def get_search_tool() -> SearchTool:
    """获取搜索工具（优先顺序：TAVILY > SERPAPI）"""
    if config.search.tavily_api_key:
        logger.info("📚 使用 TAVILY 搜索工具")
        return TavilyTool()
    elif config.search.serpapi_api_key:
        logger.info("📚 使用 SERPAPI 搜索工具")
        return SERPAPITool()
    else:
        logger.warning("⚠️ 未配置任何搜索工具")
        return None

def get_document_processor() -> Optional[DocumentProcessorTool]:
    """获取文档处理工具"""
    if config.document.mineru_api_key:
        logger.info("📄 使用 MineRU 文档处理工具")
        return DocumentProcessorTool()
    else:
        logger.warning("⚠️ 未配置文档处理工具")
        return None
