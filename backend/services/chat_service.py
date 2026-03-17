"""多轮对话服务（短期上下文 + 长期记忆）"""

import json
import os
from datetime import datetime
from typing import Optional

import httpx
from loguru import logger

from config import get_config
from services.conversation_store import ConversationStore
from services.memory_service import MemoryService
from tools.search_tools import SERPAPITool, TavilyTool


class ChatService:
    """多轮对话服务，负责会话管理、短期上下文和长期记忆召回"""

    def __init__(self):
        self.config = get_config()
        self.store = ConversationStore()
        self.memory = MemoryService()
        self.primary_search = TavilyTool() if self.config.search.tavily_api_key else SERPAPITool()
        self.fallback_search = SERPAPITool() if self.config.search.tavily_api_key else None
        self.force_web_search = os.getenv("CHAT_FORCE_WEB_SEARCH", "false").strip().lower() in {"1", "true", "yes", "on"}
        self.working_window = max(4, int(os.getenv("MEMORY_WORKING_WINDOW", "12")))
        self.memory_top_k = max(1, int(os.getenv("MEMORY_RETRIEVE_TOPK", "5")))
        
        # 获取 API 密钥，确保从环境变量正确加载
        api_key_raw = self.config.llm.api_key
        
        # 如果从配置中加载为空，尝试直接从环境变量读取
        if not api_key_raw:
            api_key_raw = os.getenv('LLM_API_KEY', '')
            if api_key_raw:
                # 更新配置对象
                self.config.llm.api_key = api_key_raw
                logger.info(f"[API密钥修复] 从环境变量加载: api_key长度={len(api_key_raw)}")
        
        # 详细调试 API 密钥加载
        logger.info(f"[API密钥检查] 原始值长度: {len(api_key_raw)}")
        logger.info(f"[API密钥检查] 前5个字符: {api_key_raw[:5] if api_key_raw else '(空)'}")
        
        self._llm_key_invalid = self._is_placeholder_api_key(api_key_raw)
        logger.info(f"[API密钥检查] _is_placeholder_api_key 返回: {self._llm_key_invalid}")
        
        if self._llm_key_invalid:
            logger.warning(f"⚠️ LLM_API_KEY 无效或占位符。将不生成自动标题。")
        else:
            logger.info(f"✅ LLM_API_KEY 有效，自动标题生成已启用")

        logger.info(
            f"[搜索配置] primary={self.primary_search.__class__.__name__} "
            f"fallback={self.fallback_search.__class__.__name__ if self.fallback_search else 'None'}"
        )
        logger.info(f"[搜索配置] CHAT_FORCE_WEB_SEARCH={self.force_web_search}")
        logger.info(f"[记忆配置] MEMORY_WORKING_WINDOW={self.working_window}, MEMORY_RETRIEVE_TOPK={self.memory_top_k}")

    @staticmethod
    def _is_placeholder_api_key(value: str) -> bool:
        key = (value or "").strip().lower()
        if not key:
            return True
        return (
            "your_" in key
            or "api_key_here" in key
            or "replace" in key
            or key in {"test", "demo", "placeholder"}
        )

    def create_conversation(self, conversation_id: str, owner_key: str, title: Optional[str]) -> dict:
        return self.store.create_conversation(conversation_id=conversation_id, owner_key=owner_key, title=title)

    def list_conversations(self, owner_key: str, limit: int = 50) -> list[dict]:
        return self.store.list_conversations(owner_key=owner_key, limit=limit)

    def list_messages(self, conversation_id: str, owner_key: str, limit: int = 100) -> list[dict]:
        return self.store.list_messages(conversation_id=conversation_id, owner_key=owner_key, limit=limit)

    def claim_guest_conversations(self, guest_client_id: str, user_id: int) -> dict:
        """登录成功后，把同一浏览器的游客会话归档到当前用户。"""
        client_id = (guest_client_id or "").strip()
        if not client_id:
            return {"conversations": 0, "messages": 0}
        return self.store.reassign_owner_key(
            from_owner_key=f"guest:{client_id}",
            to_owner_key=f"user:{user_id}",
        )

    async def send_message(self, conversation_id: str, owner_key: str, content: str) -> dict:
        conversation = self.store.get_conversation(conversation_id=conversation_id, owner_key=owner_key)
        if not conversation:
            raise ValueError("conversation_not_found")

        user_msg = self.store.add_message(
            conversation_id=conversation_id,
            owner_key=owner_key,
            role="user",
            content=content,
        )

        context_messages = self.store.list_messages(
            conversation_id=conversation_id,
            owner_key=owner_key,
            limit=max(self.working_window * 2, 8),
        )
        context_for_model = self._build_model_messages(context_messages)

        memory_hits = await self.memory.search_memories(owner_key=owner_key, query=content, top_k=self.memory_top_k)
        if memory_hits:
            context_for_model = self._inject_memory_context(context_for_model, memory_hits)

        search_sources: list[dict] = []
        force_fresh = self.force_web_search or self._needs_web_search(content)
        if force_fresh:
            logger.info(f"[搜索增强] 检测到时效性问题，启用联网搜索: {content[:80]}")
            search_sources = await self._search_latest_sources(content)
            if search_sources:
                context_for_model = self._inject_search_context(context_for_model, search_sources)
                logger.info(f"[搜索增强] 注入来源 {len(search_sources)} 条到模型上下文")
            else:
                logger.warning("[搜索增强] 未获取到外部来源，继续使用纯模型回答")

        llm_answer = await self._call_chat_llm(context_for_model)

        assistant_msg = self.store.add_message(
            conversation_id=conversation_id,
            owner_key=owner_key,
            role="assistant",
            content=llm_answer,
            meta={
                "memory_used": bool(memory_hits),
                "memory_count": len(memory_hits),
                "sources": search_sources,
            } if search_sources else {
                "memory_used": bool(memory_hits),
                "memory_count": len(memory_hits),
            },
        )

        try:
            await self.memory.capture_from_turn(
                owner_key=owner_key,
                conversation_id=conversation_id,
                user_text=content,
                assistant_text=llm_answer,
            )
        except Exception as exc:
            logger.warning(f"长期记忆写入失败: {exc}")


        # 第一条消息时自动生成标题
        if user_msg.get("turn_id") == 1:
            try:
                logger.info(f"[标题生成] 开始为对话 {conversation_id[:8]}... 生成标题")
                title = await self._generate_title_from_query(content)
                logger.info(f"[标题生成] 生成的标题: '{title}'")
                update_result = self.store.update_title(conversation_id=conversation_id, owner_key=owner_key, new_title=title)
                logger.info(f"[标题生成] update_title 返回: {update_result}")
            except Exception as e:
                logger.warning(f"自动生成标题失败: {e}", exc_info=True)

        return {
            "conversation_id": conversation_id,
            "user_message": user_msg,
            "assistant_message": assistant_msg,
            "cache": {"hit": False, "tier": None},
            "memory": {"used": bool(memory_hits), "count": len(memory_hits)},
        }

    def _build_model_messages(self, messages: list[dict]) -> list[dict]:
        trimmed = messages[-self.working_window:]
        model_messages = [
            {
                "role": "system",
                "content": "你是 TechEyes 的分析助手。回答要准确、简洁、结构化，优先给出可执行建议。",
            }
        ]
        for item in trimmed:
            role = item.get("role")
            if role not in {"user", "assistant"}:
                continue
            model_messages.append({"role": role, "content": item.get("content", "")})
        return model_messages

    @staticmethod
    def _needs_web_search(query: str) -> bool:
        text = (query or "").lower()
        fresh_keys = [
            "最新",
            "实时",
            "最近",
            "今日",
            "昨天",
            "本周",
            "本月",
            "当前",
            "股市",
            "美股",
            "港股",
            "a股",
            "news",
            "latest",
            "real-time",
            "today",
            "breaking",
        ]
        return any(key in text for key in fresh_keys)

    async def _search_latest_sources(self, query: str) -> list[dict]:
        try:
            logger.info(f"[FunctionCall] {self.primary_search.__class__.__name__}.search(query='{query[:80]}', max_results=5)")
            results = await self.primary_search.search(query, max_results=5)
            logger.info(f"[FunctionReturn] {self.primary_search.__class__.__name__}.search -> {len(results)}")
            if results:
                return results

            if self.fallback_search:
                logger.info(f"[FunctionCall] {self.fallback_search.__class__.__name__}.search(query='{query[:80]}', max_results=5)")
                fallback = await self.fallback_search.search(query, max_results=5)
                logger.info(f"[FunctionReturn] {self.fallback_search.__class__.__name__}.search -> {len(fallback)}")
                return fallback
            return []
        except Exception as exc:
            logger.warning(f"[搜索增强] 外部搜索失败: {type(exc).__name__}: {exc}")
            return []

    @staticmethod
    def _inject_search_context(model_messages: list[dict], sources: list[dict]) -> list[dict]:
        if not sources:
            return model_messages

        lines = []
        for idx, item in enumerate(sources[:5], start=1):
            title = item.get("title") or f"来源{idx}"
            snippet = (item.get("snippet") or "").strip()
            url = item.get("url") or ""
            source_name = item.get("source") or "WEB"
            lines.append(f"[{idx}] {title} ({source_name})")
            if snippet:
                lines.append(f"摘要: {snippet[:280]}")
            if url:
                lines.append(f"链接: {url}")
            lines.append("")

        search_prompt = (
            "以下为刚刚检索到的外部信息，请优先基于这些来源回答，并在关键结论后标注 [1]/[2] 这样的来源编号。"
            "若已给出来源，不要再回答'无法获取最新信息'这类泛化免责声明。\n\n"
            + "\n".join(lines)
        )

        return [model_messages[0], {"role": "system", "content": search_prompt}, *model_messages[1:]]

    @staticmethod
    def _inject_memory_context(model_messages: list[dict], memories: list[dict]) -> list[dict]:
        if not memories:
            return model_messages

        lines = []
        for idx, memory in enumerate(memories[:8], start=1):
            lines.append(f"[{idx}] ({memory.get('memory_type', 'memory')}) {memory.get('text', '')[:280]}")

        memory_prompt = (
            "以下是与当前用户相关的长期记忆，请在不编造事实的前提下用于提升回答连续性；"
            "若与当前问题无关可忽略。\n\n" + "\n".join(lines)
        )
        return [model_messages[0], {"role": "system", "content": memory_prompt}, *model_messages[1:]]

    async def _call_chat_llm(self, messages: list[dict]) -> str:
        if self._llm_key_invalid:
            return "LLM_API_KEY 未正确配置（当前为占位符或空值），请在 backend/.env 中设置真实 DashScope Key 后重启后端。"

        try:
            base = (self.config.llm.base_url or "").rstrip("/")
            url = f"{base}/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.llm.api_key}",
            }
            payload = {
                "model": self.config.llm.model_id,
                "messages": messages,
                "temperature": self.config.llm.temperature,
                "max_tokens": min(self.config.llm.max_tokens, 1200),
            }

            async with httpx.AsyncClient(timeout=float(self.config.llm.timeout)) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            content = data.get("choices", [{}])[0].get("message", {}).get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()

            return "我已收到你的问题，但当前模型没有返回有效文本。请稍后再试。"

        except Exception as exc:
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 401:
                logger.error("多轮对话 LLM 鉴权失败(401): 请检查 LLM_API_KEY 是否有效")
                return "LLM 鉴权失败（401）。请检查 backend/.env 中的 LLM_API_KEY 是否为真实有效值，并重启后端。"
            logger.error(f"多轮对话 LLM 调用失败: {exc}")
            return "当前对话服务暂时不可用，请稍后重试。"

    def delete_conversation(self, conversation_id: str, owner_key: str) -> bool:
        """删除对话"""
        return self.store.delete_conversation(conversation_id=conversation_id, owner_key=owner_key)

    def delete_message(self, conversation_id: str, owner_key: str, turn_id: int) -> bool:
        """删除消息"""
        return self.store.delete_message(conversation_id=conversation_id, owner_key=owner_key, turn_id=turn_id)


    async def _generate_title_from_query(self, query: str) -> str:
        """根据用户问题生成对话标题（简短摘要）"""
        logger.info(f"[标题生成] _llm_key_invalid={self._llm_key_invalid}, api_key长度={len(self.config.llm.api_key)}")
        if self._llm_key_invalid:
            logger.warning(f"[标题生成] LLM_API_KEY 无效或未配置，回退为用户问题标题")
            return self._fallback_title_from_query(query)
        
        try:
            base = (self.config.llm.base_url or "").rstrip("/")
            url = f"{base}/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.llm.api_key}",
            }
            
            # 让LLM生成简短的标题
            system_prompt = "你是一个助手，负责为对话生成简短的标题。请根据用户的问题生成一个5-10个字的简洁标题，直接返回标题内容，不要加引号或其他说明。"
            payload = {
                "model": self.config.llm.model_id,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"请为这个问题生成简短标题：{query[:200]}"}
                ],
                "temperature": 0.3,
                "max_tokens": 30,
            }
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                result = resp.json()
                
            if result and "choices" in result and result["choices"]:
                title = result["choices"][0]["message"]["content"].strip()
                # 移除可能的引号
                title = title.strip('\'"\"\"\"')
                # 限制长度
                return title[:50] if title else self._fallback_title_from_query(query)
            
            return self._fallback_title_from_query(query)
            
        except Exception as e:
            logger.warning(f"生成对话标题失败: {type(e).__name__}: {e!r}", exc_info=True)
            return self._fallback_title_from_query(query)

    @staticmethod
    def _fallback_title_from_query(query: str) -> str:
        text = (query or "").strip().replace("\n", " ")
        if not text:
            return "新对话"
        return text[:50]

    def get_cache_stats(self) -> dict:
        """保留旧接口兼容性，返回记忆统计。"""
        return {
            "backend": "memory-only",
            "cache_enabled": False,
            "memory": self.memory.get_stats(),
        }
