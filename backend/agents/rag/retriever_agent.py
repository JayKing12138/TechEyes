"""Retriever Agent - 文档混合检索"""

import httpx
from typing import List, Dict
from loguru import logger
from hello_agents import HelloAgentsLLM
from config import get_config
from services.hybrid_retriever import HybridRetriever


class RetrieverAgent:
    """Retriever Agent - 负责项目文档的混合检索"""
    
    def __init__(self):
        self.config = get_config()
        self.hybrid_retriever = HybridRetriever()
        self.embedding_model = "text-embedding-v4"
    
    async def retrieve(
        self,
        project_id: int,
        query: str,
        top_k: int = 15,
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3
    ) -> List[Dict]:
        """
        混合检索文档
        
        Args:
            project_id: 项目 ID
            query: 查询文本
            top_k: 返回候选数
            dense_weight: 向量检索权重
            sparse_weight: BM25 权重
        
        Returns:
            检索结果列表
        """
        try:
            logger.info(f"[RetrieverAgent] 开始检索: project_id={project_id}, query='{query[:50]}...'")
            
            # 1. 确保 BM25 索引已构建
            await self.hybrid_retriever.initialize_bm25_index(project_id)
            
            # 2. 生成查询向量
            query_embedding = await self._embed_query(query)
            
            # 3. 混合检索
            results = await self.hybrid_retriever.hybrid_search(
                project_id=project_id,
                query=query,
                query_embedding=query_embedding,
                top_k=top_k,
                dense_weight=dense_weight,
                sparse_weight=sparse_weight
            )
            
            logger.info(f"[RetrieverAgent] 检索完成: 返回 {len(results)} 个候选")
            return results
            
        except Exception as e:
            logger.error(f"[RetrieverAgent] 检索失败: {e}", exc_info=True)
            return []
    
    async def _embed_query(self, query: str) -> List[float]:
        """生成查询向量"""
        try:
            base_url = (self.config.llm.base_url or "").rstrip("/")
            url = f"{base_url}/embeddings"
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.llm.api_key}",
            }
            
            payload = {
                "model": self.embedding_model,
                "input": query
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                return data["data"][0]["embedding"]
                
        except Exception as e:
            logger.error(f"[RetrieverAgent] 向量化失败: {e}", exc_info=True)
            raise
