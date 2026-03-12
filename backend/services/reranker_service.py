"""Cross-Encoder Reranker - 精排服务"""

from typing import List, Dict
from loguru import logger
from sentence_transformers import CrossEncoder
from collections import defaultdict


class RerankerService:
    """Cross-Encoder 重排序服务"""
    
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        """
        初始化 Reranker
        
        Args:
            model_name: Cross-Encoder 模型名称
                - BAAI/bge-reranker-base: 中文优化，速度快
                - BAAI/bge-reranker-large: 精度更高，速度慢
                - cross-encoder/ms-marco-MiniLM-L-12-v2: 英文优化
        """
        try:
            self.model = CrossEncoder(model_name, max_length=512)
            logger.info(f"[Reranker] 加载模型成功: {model_name}")
        except Exception as e:
            logger.error(f"[Reranker] 模型加载失败: {e}，使用降级方案")
            self.model = None
    
    def rerank(
        self,
        query: str,
        candidates: List[Dict],
        top_k: int = 5,
        enable_diversity: bool = True,
        max_per_doc: int = 2
    ) -> List[Dict]:
        """
        重排序候选文档
        
        Args:
            query: 查询文本
            candidates: 候选文档列表
            top_k: 最终返回数量
            enable_diversity: 是否启用多样性约束
            max_per_doc: 单个文档最多贡献几个chunk
        
        Returns:
            重排序后的文档列表
        """
        if not candidates:
            return []
        
        # 如果模型未加载，使用原始排序
        if self.model is None:
            logger.warning("[Reranker] 模型未加载，使用原始排序")
            return candidates[:top_k]
        
        try:
            # 1. Cross-Encoder 评分
            pairs = [[query, chunk.get("text", "")] for chunk in candidates]
            scores = self.model.predict(pairs)
            
            # 2. 添加分数到候选
            for i, chunk in enumerate(candidates):
                chunk["rerank_score"] = float(scores[i])
            
            # 3. 按分数排序
            ranked_candidates = sorted(
                candidates,
                key=lambda x: x.get("rerank_score", 0),
                reverse=True
            )
            
            # 4. 多样性约束（避免单一文档垄断）
            if enable_diversity:
                ranked_candidates = self._apply_diversity_constraint(
                    ranked_candidates,
                    max_per_doc=max_per_doc
                )
            
            # 5. 返回 TopK
            final_results = ranked_candidates[:top_k]
            
            logger.info(
                f"[Reranker] 重排序完成: {len(candidates)} → {len(final_results)} "
                f"(diversity={'✅' if enable_diversity else '❌'})"
            )
            
            return final_results
            
        except Exception as e:
            logger.error(f"[Reranker] 重排序失败: {e}", exc_info=True)
            return candidates[:top_k]
    
    def _apply_diversity_constraint(
        self,
        candidates: List[Dict],
        max_per_doc: int = 2
    ) -> List[Dict]:
        """
        应用多样性约束 - 避免结果全来自同一文档
        
        Args:
            candidates: 排序后的候选列表
            max_per_doc: 单个文档最多保留几个chunk
        
        Returns:
            应用约束后的候选列表
        """
        doc_count = defaultdict(int)
        diverse_results = []
        
        for chunk in candidates:
            doc_id = chunk.get("document_id")
            
            # 检查该文档是否已达上限
            if doc_count[doc_id] < max_per_doc:
                diverse_results.append(chunk)
                doc_count[doc_id] += 1
        
        unique_docs = len(doc_count)
        logger.info(f"[Diversity] 应用多样性约束: {len(candidates)} → {len(diverse_results)} chunks, 来自 {unique_docs} 个文档")
        
        return diverse_results
    
    def _deduplicate(self, candidates: List[Dict], threshold: float = 0.95) -> List[Dict]:
        """
        去重 - 移除高度相似的文档块
        
        Args:
            candidates: 候选列表
            threshold: 相似度阈值
        
        Returns:
            去重后的列表
        """
        # 简单的文本相似度去重（可以用更复杂的方法）
        seen_texts = set()
        unique_candidates = []
        
        for chunk in candidates:
            text = chunk.get("text", "")[:200]  # 使用前200字符
            text_hash = hash(text)
            
            if text_hash not in seen_texts:
                seen_texts.add(text_hash)
                unique_candidates.append(chunk)
        
        if len(unique_candidates) < len(candidates):
            logger.info(f"[Dedup] 去重: {len(candidates)} → {len(unique_candidates)}")
        
        return unique_candidates
