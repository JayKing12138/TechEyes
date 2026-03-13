"""项目 RAG 服务 - 多智能体编排架构"""

from typing import List, Dict, Optional
from loguru import logger

from config import get_config
from agents.rag.router_agent import RouterAgent
from agents.rag.planner_agent import PlannerAgent
from agents.rag.retriever_agent import RetrieverAgent
from agents.rag.web_news_agent import WebNewsAgent
from agents.rag.reranker_agent import RerankerAgent
from agents.rag.synthesizer_agent import SynthesizerAgent
from agents.rag.critic_agent import CriticAgent
from services.cache_service import CacheService


class ProjectRAGService:
    """项目 RAG 服务 - 7个Agent协作架构"""
    
    def __init__(self):
        self.config = get_config()
        
        # 初始化 7 个 RAG Agent
        self.router = RouterAgent()
        self.planner = PlannerAgent()
        self.retriever = RetrieverAgent()
        self.web_news = WebNewsAgent()
        self.reranker = RerankerAgent()
        self.synthesizer = SynthesizerAgent()
        self.critic = CriticAgent()

        # KV cache：L1(内存LRU) + L2(Redis) + L3(语义向量)
        self.kv_cache = CacheService()
        
        logger.info("[ProjectRAGService] 多智能体架构初始化完成（含 KV cache）")
    
    # -------------------- 缓存辅助 --------------------

    def _build_owner_key(self, project_id: int) -> str:
        """KV cache 的域键，按项目隔离。"""
        return f"project:{project_id}"

    def _build_context_text_for_cache(self, question: str, conversation_history: Optional[List[Dict]]) -> str:
        """将最近 3 轮对话历史拼成 context 文本，用于区分不同对话状态下对同一问题的缓存。"""
        if not conversation_history:
            return question
        recent = conversation_history[-6:]  # 最近 3 轮 = 6 条消息
        turns = " | ".join(
            f"{m.get('role','')}: {(m.get('content') or '')[:80]}" for m in recent
        )
        return f"{turns} | question: {question}"

    async def invalidate_project_cache(self, project_id: int) -> dict:
        """文档上传/删除后清理项目缓存（L1/L2/L3 全层失效）。"""
        owner_key = self._build_owner_key(project_id)
        try:
            stats = await self.kv_cache.invalidate_chat_cache_by_owner(owner_key)
            logger.info(f"[KVCache] 项目 {project_id} 缓存失效完成: {stats}")
            return stats
        except Exception as exc:
            logger.warning(f"[KVCache] 项目 {project_id} 缓存失效失败: {exc}")
            return {"owner_key": owner_key, "l1_deleted": 0, "l2_deleted": 0, "l3_deleted": 0}

    # -------------------- 主流程 --------------------

    async def answer_with_rag(
        self,
        project_id: int,
        question: str,
        conversation_history: List[Dict] = None,
        enable_news: bool = True,
        project_memories: Optional[List[Dict]] = None,
    ) -> Dict:
        """基于多智能体协作生成回答
        
        工作流程：
        0. KV Cache 命中短路（L1 内存 → L2 Redis → L3 语义向量）
        1. Router Agent: 意图识别和路由决策
        2. Planner Agent: 复杂问题拆解（可选）
        3. Retriever + WebNews Agent: 并行检索
        4. Reranker Agent: 统一精排
        5. Synthesizer Agent: 生成带引用的回答
        6. Critic Agent: 质量校验
        7. 回写 KV Cache
        """
        # ========== 阶段0: KV Cache 命中短路 ==========
        owner_key = self._build_owner_key(project_id)
        context_text = self._build_context_text_for_cache(question, conversation_history)
        model_sig = f"{self.config.llm.provider}:{self.config.llm.model_id}"

        cached_result, cache_source = await self.kv_cache.get_chat_cached_result(
            owner_key=owner_key,
            query=question,
            context_text=context_text,
            model_signature=model_sig,
            allow_public=False,
        )
        if cached_result is not None:
            logger.info(f"[ProjectRAG] KV Cache 命中 ({cache_source})，跳过 Agent 流水线")
            cached_result.setdefault("rag_info", {})
            cached_result["rag_info"]["cache_hit"] = True
            cached_result["rag_info"]["cache_source"] = cache_source
            return cached_result

        try:
            logger.info(f"[ProjectRAG] Cache miss，开始处理问题: '{question[:50]}...'")
            
            # ========== 阶段1: 路由决策 ==========
            routing = await self.router.route(question)
            logger.info(f"[ProjectRAG] 路由结果: {routing}")

            intent = routing.get("intent")
            allow_model_knowledge = bool(routing.get("allow_model_knowledge"))
            
            # ========== 阶段2: 问题拆解（复杂问题） ==========
            queries = [question]
            if routing.get("complexity") == "high":
                queries = await self.planner.decompose(question, max_sub_queries=3)
                logger.info(f"[ProjectRAG] 拆解为 {len(queries)} 个子查询")
            
            # ========== 阶段3: 并行检索 ==========
            all_doc_chunks = []
            all_news_sources = []
            
            # 3.1 文档检索
            # 为了尽量“多用项目文档”，这里不再尊重 Router 的 need_doc=False，
            # 而是始终尝试基于项目文档做检索；若项目本身无文档，Retriever 会自然返回空。
            for query in queries:
                chunks = await self.retriever.retrieve(
                    project_id=project_id,
                    query=query,
                    top_k=15,  # 召回阶段多召回一些
                )
                all_doc_chunks.extend(chunks)
            
            # 去重（基于 chunk_id）
            seen_ids = set()
            unique_chunks = []
            for chunk in all_doc_chunks:
                cid = chunk.get("chunk_id")
                if cid not in seen_ids:
                    seen_ids.add(cid)
                    unique_chunks.append(chunk)
            all_doc_chunks = unique_chunks
            
            logger.info(f"[ProjectRAG] 文档检索: {len(all_doc_chunks)} 个候选")
            
            # 3.2 Web/新闻检索
            if enable_news and routing.get("need_web", False):
                news_sources = await self.web_news.search_web(
                    query=question,
                    max_results=5,
                    force_search=True,
                    enable_domain_filter=False  # 开发阶段不过滤域名
                )
                all_news_sources = news_sources
                logger.info(f"[ProjectRAG] 新闻检索: {len(all_news_sources)} 个来源")
            
            # ========== 阶段4: 统一精排 ==========
            # 合并所有候选
            all_candidates = all_doc_chunks + all_news_sources
            
            final_chunks = await self.reranker.rerank(
                query=question,
                candidates=all_candidates,
                top_k=5,
                enable_diversity=True,
                max_per_doc=2
            )
            
            logger.info(f"[ProjectRAG] 精排完成: {len(final_chunks)} 个精选证据")
            
            # ========== 阶段5: 生成回答 ==========
            # 分离文档和新闻
            doc_chunks = [c for c in final_chunks if c.get("retrieval_method") != "news"]
            news_sources = [c for c in final_chunks if c.get("retrieval_method") == "news"]
            
            answer = await self.synthesizer.synthesize(
                query=question,
                doc_chunks=doc_chunks,
                news_sources=news_sources,
                conversation_history=conversation_history or [],
                project_memories=project_memories or [],
                allow_model_knowledge=allow_model_knowledge,
            )
            
            logger.info("[ProjectRAG] 回答生成完成")
            
            # ========== 阶段6: 质量校验 ==========
            # 保留 Critic 仅作“诊断与打分”，不再干预最终回答内容，
            # 以保证用户总能拿到完整回答。
            validation = await self.critic.validate(
                query=question,
                answer=answer,
                evidence_chunks=final_chunks,
            )
            logger.info(
                f"[ProjectRAG] 质量校验: valid={validation.get('valid')}, "
                f"hallucination={validation.get('hallucination')}, "
                f"sufficient={validation.get('sufficient')}"
            )
            
            # ========== 返回结果 ==========
            result = {
                "answer": answer,
                "doc_chunks": doc_chunks,
                "news_sources": news_sources,
                "rag_info": {
                    "used": True,
                    "doc_used": len(doc_chunks) > 0,
                    "news_used": len(news_sources) > 0,
                    "doc_count": len(doc_chunks),
                    "news_count": len(news_sources),
                    "doc_ids": [c.get("document_id") for c in doc_chunks if c.get("document_id")],
                    "chunk_ids": [c.get("chunk_id") for c in doc_chunks if c.get("chunk_id")],
                    "memory_used": bool(project_memories),
                    "memory_count": len(project_memories or []),
                    "routing": routing,
                    "validation": validation,
                    "cache_hit": False,
                    "agent_workflow": {
                        "router": True,
                        "planner": routing.get("complexity") == "high",
                        "retriever": routing.get("need_doc", True),
                        "web_news": routing.get("need_web", False),
                        "reranker": True,
                        "synthesizer": True,
                        "critic": True
                    }
                }
            }

            # ========== 阶段7: 回写 KV Cache ==========
            # 只缓存 Critic 认为有效的回答，避免低质量内容污染缓存
            if validation.get("valid", True) is not False:
                try:
                    # doc_chunks 和 news_sources 可能含不可序列化对象，先做浅拷贝保平安
                    cache_payload = {
                        "answer": answer,
                        "doc_chunks": doc_chunks,
                        "news_sources": news_sources,
                        "rag_info": result["rag_info"],
                    }
                    await self.kv_cache.set_chat_cache(
                        owner_key=owner_key,
                        query=question,
                        context_text=context_text,
                        model_signature=model_sig,
                        result=cache_payload,
                        allow_public=False,
                    )
                    logger.info("[ProjectRAG] 回答已写入 KV Cache")
                except Exception as cache_exc:
                    logger.warning(f"[ProjectRAG] KV Cache 写入失败（不影响返回）: {cache_exc}")

            return result
            
        except Exception as e:
            logger.error(f"[ProjectRAG] 多智能体协作失败: {e}", exc_info=True)
            return {
                "answer": f"抱歉，生成回答时出现错误：{str(e)}",
                "doc_chunks": [],
                "news_sources": [],
                "rag_info": {"used": False, "doc_used": False, "news_used": False, "cache_hit": False}
            }

# 模块级单例，复用 KV Cache 连接
project_rag_service = ProjectRAGService()