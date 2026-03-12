"""混合检索器 - Dense + Sparse (BM25) + RRF 融合"""

import jieba
from typing import List, Dict, Optional
from loguru import logger
from rank_bm25 import BM25Okapi
from collections import defaultdict
import os

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb
from chromadb.config import Settings
from config import get_config
from database import engine
from sqlalchemy import text


class BM25Retriever:
    """BM25 稀疏检索器 - 基于关键词匹配"""
    
    def __init__(self):
        self.config = get_config()
        # 项目维度的 BM25 索引缓存
        self.bm25_index_cache = {}  # {project_id: (bm25_model, chunk_ids)}
        
    def _tokenize(self, text: str) -> List[str]:
        """中文分词"""
        return list(jieba.cut_for_search(text))
    
    def build_index(self, project_id: int, chunks: List[Dict]) -> None:
        """为项目构建 BM25 索引"""
        if not chunks:
            logger.warning(f"[BM25] 项目 {project_id} 无文档块，跳过索引构建")
            return
        
        # 提取文本并分词
        tokenized_corpus = []
        chunk_ids = []
        
        for chunk in chunks:
            text = chunk.get("text", "")
            tokenized_corpus.append(self._tokenize(text))
            chunk_ids.append(chunk.get("chunk_id"))
        
        # 构建 BM25 模型
        bm25_model = BM25Okapi(tokenized_corpus)
        self.bm25_index_cache[project_id] = (bm25_model, chunk_ids, chunks)
        
        logger.info(f"[BM25] 为项目 {project_id} 构建索引完成，共 {len(chunks)} 个文档块")
    
    def search(self, project_id: int, query: str, top_k: int = 10) -> List[Dict]:
        """BM25 检索"""
        if project_id not in self.bm25_index_cache:
            logger.warning(f"[BM25] 项目 {project_id} 索引未构建，返回空结果")
            return []
        
        bm25_model, chunk_ids, chunks = self.bm25_index_cache[project_id]
        
        # 查询分词
        tokenized_query = self._tokenize(query)
        
        # BM25 评分
        scores = bm25_model.get_scores(tokenized_query)
        
        # 排序并获取 TopK
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        
        results = []
        for idx in ranked_indices:
            if scores[idx] > 0:  # 只返回有分数的结果
                results.append({
                    **chunks[idx],
                    "bm25_score": float(scores[idx]),
                    "retrieval_method": "bm25"
                })
        
        logger.info(f"[BM25] 检索到 {len(results)} 个相关文档块")
        return results


class RRFFusion:
    """Reciprocal Rank Fusion - 融合多路检索结果"""
    
    @staticmethod
    def fuse(
        dense_results: List[Dict],
        sparse_results: List[Dict],
        k: int = 60,
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3
    ) -> List[Dict]:
        """
        RRF 融合算法
        
        Args:
            dense_results: 向量检索结果
            sparse_results: BM25 检索结果
            k: RRF 常数（通常取 60）
            dense_weight: 向量检索权重
            sparse_weight: BM25 权重
        
        Returns:
            融合后的排序结果
        """
        # 计算 RRF 分数
        rrf_scores = defaultdict(float)
        chunk_map = {}
        
        # Dense 召回的 RRF 分数
        for rank, item in enumerate(dense_results, start=1):
            chunk_id = item.get("chunk_id")
            rrf_scores[chunk_id] += dense_weight * (1 / (k + rank))
            if chunk_id not in chunk_map:
                chunk_map[chunk_id] = item
        
        # Sparse 召回的 RRF 分数
        for rank, item in enumerate(sparse_results, start=1):
            chunk_id = item.get("chunk_id")
            rrf_scores[chunk_id] += sparse_weight * (1 / (k + rank))
            if chunk_id not in chunk_map:
                chunk_map[chunk_id] = item
        
        # 按 RRF 分数排序
        sorted_chunks = sorted(
            rrf_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # 构建融合结果
        fused_results = []
        for chunk_id, rrf_score in sorted_chunks:
            chunk = chunk_map[chunk_id]
            chunk["rrf_score"] = float(rrf_score)
            chunk["retrieval_method"] = "rrf_fusion"
            fused_results.append(chunk)
        
        logger.info(f"[RRF] 融合 Dense({len(dense_results)}) + Sparse({len(sparse_results)}) → {len(fused_results)} 个候选")
        return fused_results


class HybridRetriever:
    """混合检索器 - 统一接口"""
    
    def __init__(self):
        self.config = get_config()
        self.bm25_retriever = BM25Retriever()
        
        # Chroma 客户端
        chroma_dir = self.config.app.chroma_path
        self.chroma_client = chromadb.PersistentClient(
            path=str(chroma_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        self.chroma_collection = self.chroma_client.get_or_create_collection(
            name="project_document_chunks",
            metadata={"hnsw:space": "cosine"},
        )
    
    async def initialize_bm25_index(self, project_id: int) -> bool:
        """初始化项目的 BM25 索引"""
        try:
            # 从数据库加载所有文档块
            with engine.connect() as conn:
                result = conn.execute(
                    text(
                        """
                        SELECT c.id as chunk_id,
                               c.text_content as text,
                               c.document_id,
                               d.filename
                        FROM project_document_chunks c
                        JOIN project_documents d ON c.document_id = d.id
                        WHERE d.project_id = :project_id
                        ORDER BY c.chunk_index
                        """
                    ),
                    {"project_id": project_id},
                )
                chunks = [dict(row._mapping) for row in result]
            
            if not chunks:
                logger.warning(f"[HybridRetriever] 项目 {project_id} 无文档块")
                return False
            
            # 构建 BM25 索引
            self.bm25_retriever.build_index(project_id, chunks)
            return True
            
        except Exception as e:
            logger.error(f"[HybridRetriever] 初始化 BM25 索引失败: {e}", exc_info=True)
            return False
    
    async def hybrid_search(
        self,
        project_id: int,
        query: str,
        query_embedding: List[float],
        top_k: int = 15,
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3
    ) -> List[Dict]:
        """
        混合检索：Dense (Chroma) + Sparse (BM25) → RRF 融合
        
        Args:
            project_id: 项目 ID
            query: 查询文本
            query_embedding: 查询向量
            top_k: 最终返回的候选数
            dense_weight: 向量检索权重
            sparse_weight: BM25 权重
        
        Returns:
            RRF 融合后的结果列表
        """
        # 1. Dense 向量检索
        dense_results = await self._dense_search(project_id, query_embedding, top_k=10)
        
        # 2. Sparse BM25 检索
        sparse_results = self.bm25_retriever.search(project_id, query, top_k=10)
        
        # 3. RRF 融合
        fused_results = RRFFusion.fuse(
            dense_results,
            sparse_results,
            k=60,
            dense_weight=dense_weight,
            sparse_weight=sparse_weight
        )
        
        # 返回 TopK
        return fused_results[:top_k]
    
    async def _dense_search(
        self,
        project_id: int,
        query_embedding: List[float],
        top_k: int = 10
    ) -> List[Dict]:
        """Chroma 向量检索"""
        try:
            results = self.chroma_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k * 5,
                # 不在 Chroma 侧使用 where 过滤，避免旧数据缺少 project_id 元数据导致错误；
                # 在应用侧根据 metadata 再按 project_id 过滤。
                include=["metadatas", "documents", "distances"],
            )
            
            if not results["ids"] or not results["ids"][0]:
                return []
            
            chunks = []
            for i, chunk_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i]

                # 如果元数据里带有 project_id，则按项目过滤；否则回退为当前 project_id
                meta_project_id = metadata.get("project_id")
                if meta_project_id is not None and int(meta_project_id) != int(project_id):
                    continue

                chunks.append({
                    "chunk_id": int(chunk_id),
                    "document_id": metadata.get("document_id"),
                    "filename": metadata.get("filename"),
                    "project_id": metadata.get("project_id", project_id),
                    "text": results["documents"][0][i],
                    "distance": results["distances"][0][i],
                    "dense_score": 1 - results["distances"][0][i],  # 转为相似度
                    "retrieval_method": "dense"
                })
            
            logger.info(f"[Dense] 检索到 {len(chunks)} 个相关文档块")
            return chunks
            
        except Exception as e:
            logger.error(f"[Dense] 检索失败: {e}", exc_info=True)
            return []
