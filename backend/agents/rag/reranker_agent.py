"""Reranker Agent - 统一精排"""

from typing import List, Dict
from loguru import logger
from services.reranker_service import RerankerService
from config import get_config


class RerankerAgent:
    """Reranker Agent - 负责候选结果的精排和多样性控制"""
    
    def __init__(self):
        self.config = get_config()
        
        # 初始化 Reranker 服务
        reranker_model = getattr(self.config.retrieval, "reranker_model", "BAAI/bge-reranker-base")
        self.reranker = RerankerService(model_name=reranker_model)
    
    async def rerank(
        self,
        query: str,
        candidates: List[Dict],
        top_k: int = 5,
        enable_diversity: bool = True,
        max_per_doc: int = 2
    ) -> List[Dict]:
        """
        重排序候选结果
        
        Args:
            query: 查询文本
            candidates: 候选列表（来自不同检索源）
            top_k: 最终返回数
            enable_diversity: 是否启用多样性约束
            max_per_doc: 单个文档最多贡献几个chunk
        
        Returns:
            精排后的结果列表
        """
        try:
            if not candidates:
                logger.warning("[RerankerAgent] 无候选结果需要重排序")
                return []
            
            logger.info(f"[RerankerAgent] 开始重排序: {len(candidates)} 个候选 → TopK={top_k}")
            
            # 1. Cross-Encoder 评分 + 多样性约束
            ranked_results = self.reranker.rerank(
                query=query,
                candidates=candidates,
                top_k=top_k,
                enable_diversity=enable_diversity,
                max_per_doc=max_per_doc
            )
            
            # 2. 添加排名信息
            for i, chunk in enumerate(ranked_results, start=1):
                chunk["final_rank"] = i
            
            logger.info(f"[RerankerAgent] 重排序完成: 返回 {len(ranked_results)} 个精选结果")
            return ranked_results
            
        except Exception as e:
            logger.error(f"[RerankerAgent] 重排序失败: {e}", exc_info=True)
            # 降级：返回原始候选的 TopK
            return candidates[:top_k]
