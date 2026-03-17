"""Retriever Agent - 文档混合检索"""

import httpx
from typing import List, Dict, Optional
from loguru import logger
from config import get_config
from services.hybrid_retriever import HybridRetriever
from agents.langchain_runtime import LangChainLLM, SimpleLangChainAgent


class RetrieverAgent:
    """Retriever Agent - 负责项目文档的混合检索"""
    
    def __init__(self):
        self.config = get_config()
        self.hybrid_retriever = HybridRetriever()
        self.embedding_model = "text-embedding-v4"
        self.enable_mqe = bool(getattr(self.config.retrieval, "enable_mqe", True))
        self.enable_hyde = bool(getattr(self.config.retrieval, "enable_hyde", True))
        self.mqe_query_count = max(1, int(getattr(self.config.retrieval, "mqe_query_count", 2)))

        self.llm = LangChainLLM(
            model=self.config.llm.model_id,
            api_key=self.config.llm.api_key,
            base_url=self.config.llm.base_url if self.config.llm.base_url else None,
            provider=self.config.llm.provider,
            temperature=0.2,
            timeout=self.config.llm.timeout,
        )
        self.query_expander = SimpleLangChainAgent(
            name="RetrieverQueryExpander",
            llm=self.llm,
            system_prompt=(
                "你是检索查询增强助手。"
                "请基于用户问题输出用于检索的改写查询，保持语义一致、覆盖不同表述角度。"
            ),
        )
        self.hyde_generator = SimpleLangChainAgent(
            name="RetrieverHyDEGenerator",
            llm=self.llm,
            system_prompt=(
                "你是 HyDE 生成器。"
                "请针对用户问题生成一段可能出现在技术文档中的假设性答案摘要（80-180字），"
                "内容要客观、术语化，便于向量检索，不要编造具体数字来源。"
            ),
        )
    
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

            # 2. 构建增强查询集合（原始查询 + MQE 改写）
            expanded_queries = await self._build_mqe_queries(query)

            # 3. 生成 HyDE 假设文档并加入 Dense 查询
            hyde_text = await self._build_hyde_text(query)

            # 4. 对每个查询执行混合检索并融合
            results = await self._retrieve_with_query_set(
                project_id=project_id,
                original_query=query,
                expanded_queries=expanded_queries,
                hyde_text=hyde_text,
                top_k=top_k,
                dense_weight=dense_weight,
                sparse_weight=sparse_weight,
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

    async def _build_mqe_queries(self, query: str) -> List[str]:
        """构建 MQE 多查询（包含原始查询）。"""
        queries = [query.strip()]
        if not self.enable_mqe or not self.config.llm.api_key:
            return queries

        try:
            prompt = (
                f"原始问题：{query}\n\n"
                f"请生成 {self.mqe_query_count} 条检索改写，每行一条，不要编号，不要解释。"
            )
            raw = self.query_expander.run(prompt)
            candidates = [line.strip(" -\t") for line in raw.splitlines() if line.strip()]
            for cand in candidates:
                if cand and cand not in queries:
                    queries.append(cand)
                if len(queries) >= 1 + self.mqe_query_count:
                    break
            logger.info(f"[RetrieverAgent] MQE 启用: 原始+改写共 {len(queries)} 条查询")
        except Exception as exc:
            logger.warning(f"[RetrieverAgent] MQE 生成失败，回退原始查询: {exc}")

        return queries

    async def _build_hyde_text(self, query: str) -> Optional[str]:
        """生成 HyDE 假设文档文本。"""
        if not self.enable_hyde or not self.config.llm.api_key:
            return None

        try:
            hyde = self.hyde_generator.run(f"用户问题：{query}")
            hyde = (hyde or "").strip()
            if hyde:
                logger.info(f"[RetrieverAgent] HyDE 启用: 生成假设文档 {len(hyde)} 字")
                return hyde
        except Exception as exc:
            logger.warning(f"[RetrieverAgent] HyDE 生成失败，跳过: {exc}")
        return None

    async def _retrieve_with_query_set(
        self,
        project_id: int,
        original_query: str,
        expanded_queries: List[str],
        hyde_text: Optional[str],
        top_k: int,
        dense_weight: float,
        sparse_weight: float,
    ) -> List[Dict]:
        """对多查询执行检索并做跨查询融合。"""
        all_runs: List[List[Dict]] = []

        for q in expanded_queries:
            dense_input = hyde_text if (hyde_text and q == original_query) else q
            query_embedding = await self._embed_query(dense_input)

            run_results = await self.hybrid_retriever.hybrid_search(
                project_id=project_id,
                query=q,
                query_embedding=query_embedding,
                top_k=max(top_k, 12),
                dense_weight=dense_weight,
                sparse_weight=sparse_weight,
            )
            all_runs.append(run_results)

        fused = self._fuse_multi_query_results(all_runs)
        return fused[:top_k]

    @staticmethod
    def _fuse_multi_query_results(result_runs: List[List[Dict]]) -> List[Dict]:
        """跨查询 RRF 融合，提升召回鲁棒性。"""
        score_map: Dict[int, float] = {}
        chunk_map: Dict[int, Dict] = {}
        k = 60

        for run in result_runs:
            for rank, item in enumerate(run, start=1):
                chunk_id = item.get("chunk_id")
                if chunk_id is None:
                    continue
                cid = int(chunk_id)
                score_map[cid] = score_map.get(cid, 0.0) + (1.0 / (k + rank))
                if cid not in chunk_map:
                    chunk_map[cid] = dict(item)

        merged = sorted(score_map.items(), key=lambda x: x[1], reverse=True)
        results: List[Dict] = []
        for cid, score in merged:
            item = chunk_map[cid]
            item["mqe_rrf_score"] = float(score)
            item["retrieval_method"] = "mqe_hyde_fusion"
            results.append(item)
        return results
