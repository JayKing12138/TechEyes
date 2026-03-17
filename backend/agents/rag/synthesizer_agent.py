"""Synthesizer Agent - 基于证据生成回答"""

from typing import List, Dict
from loguru import logger
from agents.langchain_runtime import SimpleLangChainAgent, LangChainLLM
from config import get_config


class SynthesizerAgent:
    """Synthesizer Agent - 负责基于证据生成带引用的回答"""
    
    def __init__(self):
        config = get_config()
        self.llm = LangChainLLM(
            model=config.llm.model_id,
            api_key=config.llm.api_key,
            base_url=config.llm.base_url if config.llm.base_url else None,
            provider=config.llm.provider
        )
        
        self.agent = SimpleLangChainAgent(
            name="SynthesizerAgent",
            llm=self.llm,
            system_prompt=self._get_system_prompt()
        )
    
    def _get_system_prompt(self) -> str:
        return """你是 TechEyes 的回答生成专家，负责基于证据生成高质量答案。

核心要求：
1. **强制引用**：每个事实陈述必须引用来源，使用 [文档N] 格式
2. **忠于证据**：只回答证据支持的内容，不编造信息
3. **结构清晰**：使用markdown格式，分段落、列表组织
4. **引用规范**：
   - 文档引用：[文档1]、[文档2]
   - 新闻引用：[新闻1]、[新闻2]
   - 引用编号与提供的证据编号一致

回答模板：
```
[简洁直接回答主问题]

[详细展开，分点论述]
- 论点1 [文档1]
- 论点2 [文档2][文档3]

[总结或展望]
```

如果证据不足：
"抱歉，基于当前项目文档，我无法完整回答这个问题。文档中提到了 [文档1的内容]，但缺乏XXX方面的信息。"

禁止行为：
- ❌ 不加引用的事实陈述
- ❌ 编造不存在于证据中的信息
- ❌ 模糊的引用（如"根据资料"）
- ❌ 引用不存在的文档编号"""
    
    async def synthesize(
        self,
        query: str,
        doc_chunks: List[Dict],
        news_sources: List[Dict],
        conversation_history: List[Dict] = None,
        project_memories: List[Dict] = None,
        allow_model_knowledge: bool = False,
    ) -> str:
        """
        生成带引用的回答
        
        Args:
            query: 用户问题
            doc_chunks: 文档证据块（已精排）
            news_sources: 新闻来源
            conversation_history: 对话历史
        
        Returns:
            带引用的回答文本
        """
        try:
            logger.info(
                f"[SynthesizerAgent] 开始生成回答: "
                f"doc={len(doc_chunks)}, news={len(news_sources)}, "
                f"memories={len(project_memories or [])}, "
                f"allow_model_knowledge={allow_model_knowledge}"
            )
            
            # 检查：如果没有任何证据，且不允许使用通识知识，则直接拒绝回答
            if not doc_chunks and not news_sources and not (project_memories or allow_model_knowledge):
                logger.warning("[SynthesizerAgent] 零证据且不允许使用通识知识，拒绝生成回答")
                return (
                    "抱歉，我无法在当前项目文档中找到足够信息来回答这个问题。"
                    "建议你：\n1. 上传更多相关文档；\n2. 调整提问角度；\n3. 如需行业/宏观背景，请允许我结合通用知识进行回答。"
                )
            
            # 构建证据上下文
            context_prompt = self._build_context(
                query=query,
                doc_chunks=doc_chunks,
                news_sources=news_sources,
                project_memories=project_memories or [],
                allow_model_knowledge=allow_model_knowledge,
            )
            
            # 添加对话历史（最近3轮）
            if conversation_history:
                history_text = "\n".join([
                    f"{msg['role']}: {msg.get('content', '')}"
                    for msg in conversation_history[-6:]  # 最近3轮（6条消息）
                ])
                context_prompt = f"对话历史：\n{history_text}\n\n{context_prompt}"
            
            # 生成回答
            answer = self.agent.run(context_prompt)
            
            logger.info("[SynthesizerAgent] 回答生成完成")
            return answer
            
        except Exception as e:
            logger.error(f"[SynthesizerAgent] 回答生成失败: {e}", exc_info=True)
            return f"抱歉，生成回答时出现错误：{str(e)}"
    
    def _build_context(
        self,
        query: str,
        doc_chunks: List[Dict],
        news_sources: List[Dict],
        project_memories: List[Dict],
        allow_model_knowledge: bool,
    ) -> str:
        """构建证据上下文提示"""
        lines = [f"用户问题：{query}\n"]
        
        # 文档证据
        if doc_chunks:
            lines.append("**项目文档证据**：")
            for i, chunk in enumerate(doc_chunks[:5], start=1):
                filename = chunk.get("filename", "未知文件")
                text = chunk.get("text", "")[:500]  # 限制长度
                lines.append(f"\n[文档{i}] 来源: {filename}")
                lines.append(f"内容: {text}")
        
        # 新闻证据
        if news_sources:
            lines.append("\n**最新新闻证据**：")
            for i, source in enumerate(news_sources[:3], start=1):
                title = source.get("title", "")
                snippet = source.get("snippet", "")[:300]
                lines.append(f"\n[新闻{i}] {title}")
                lines.append(f"内容: {snippet}")
        
        # 项目长期记忆（关键结论/摘要）
        if project_memories:
            lines.append("\n**项目长期记忆（关键结论/摘要）**：")
            for i, mem in enumerate(project_memories[:5], start=1):
                mem_type = mem.get("memory_type") or "memory"
                text = (mem.get("text") or "")[:500]
                lines.append(f"\n[记忆{i}] 类型: {mem_type}")
                lines.append(f"内容: {text}")
        
        # 生成指令
        if allow_model_knowledge:
            lines.append(
                "\n请基于以上证据回答用户问题，并在证据不足的部分，结合你对该领域的一般性知识给出合理的分析与建议。"
            )
            lines.append(
                "当使用通用知识（而非文档/新闻/记忆中的具体事实）时，请在表述中显式说明，例如“基于一般行业实践”或“超出当前项目文档的经验性建议”。"
            )
        else:
            lines.append("\n请严格基于以上证据回答用户问题，务必使用 [文档N] 或 [新闻N] 格式引用来源，不要编造文档中不存在的具体事实。")
        
        return "\n".join(lines)
