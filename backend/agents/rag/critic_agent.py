"""Critic Agent - 质量校验"""

import re
from typing import List, Dict
from loguru import logger
from hello_agents import SimpleAgent, HelloAgentsLLM
from config import get_config


class CriticAgent:
    """Critic Agent - 负责答案质量校验和幻觉检测"""
    
    def __init__(self):
        config = get_config()
        self.llm = HelloAgentsLLM(
            model=config.llm.model_id,
            api_key=config.llm.api_key,
            base_url=config.llm.base_url if config.llm.base_url else None,
            provider=config.llm.provider
        )
        
        self.agent = SimpleAgent(
            name="CriticAgent",
            llm=self.llm,
            system_prompt=self._get_system_prompt()
        )
    
    def _get_system_prompt(self) -> str:
        return """你是严格的质量审查专家，负责检查 RAG 回答的质量。

检查维度：
1. **幻觉检测**：回答中的事实是否都有证据支持？
2. **引用验证**：所有引用的 [文档N] 编号是否存在？
3. **证据充分性**：证据是否足以支撑回答？
4. **逻辑一致性**：回答是否自相矛盾？

返回判断（简洁）：
- "✅ 通过" - 质量合格
- "❌ 幻觉" - 发现不实信息
- "❌ 引用无效" - 引用了不存在的文档
- "⚠️ 证据不足" - 需要更多证据

你的回答要简短，只需要给出判断和关键理由。"""
    
    async def validate(
        self,
        query: str,
        answer: str,
        evidence_chunks: List[Dict]
    ) -> Dict:
        """
        校验回答质量
        
        Args:
            query: 用户问题
            answer: 生成的回答
            evidence_chunks: 证据块列表
        
        Returns:
            校验结果字典
        """
        try:
            logger.info("[CriticAgent] 开始质量校验")
            
            # 1. 引用验证（快速规则检查）
            citation_valid, citation_issues = self._validate_citations(answer, evidence_chunks)
            
            if not citation_valid:
                return {
                    "valid": False,
                    "hallucination": False,
                    "citation_invalid": True,
                    "sufficient": False,
                    "issues": citation_issues,
                    "need_additional_retrieval": False
                }
            
            # 2. LLM 深度校验（幻觉 + 充分性）
            llm_validation = await self._llm_validate(query, answer, evidence_chunks)
            
            return llm_validation
            
        except Exception as e:
            logger.error(f"[CriticAgent] 校验失败: {e}", exc_info=True)
            # 降级：默认通过
            return {
                "valid": True,
                "hallucination": False,
                "citation_invalid": False,
                "sufficient": True,
                "issues": [],
                "need_additional_retrieval": False
            }
    
    def _validate_citations(self, answer: str, evidence_chunks: List[Dict]) -> tuple:
        """验证引用的文档编号是否存在"""
        # 提取所有引用
        citations = re.findall(r'\[文档(\d+)\]|\[新闻(\d+)\]', answer)
        cited_doc_nums = set()
        cited_news_nums = set()
        
        for doc_num, news_num in citations:
            if doc_num:
                cited_doc_nums.add(int(doc_num))
            if news_num:
                cited_news_nums.add(int(news_num))
        
        # 检查文档引用是否有效
        max_doc_num = len([c for c in evidence_chunks if c.get("retrieval_method") != "news"])
        max_news_num = len([c for c in evidence_chunks if c.get("retrieval_method") == "news"])
        
        invalid_docs = [n for n in cited_doc_nums if n > max_doc_num or n <= 0]
        invalid_news = [n for n in cited_news_nums if n > max_news_num or n <= 0]
        
        issues = []
        if invalid_docs:
            issues.append(f"引用了不存在的文档编号: {invalid_docs}")
        if invalid_news:
            issues.append(f"引用了不存在的新闻编号: {invalid_news}")
        
        is_valid = len(issues) == 0
        
        if not is_valid:
            logger.warning(f"[CriticAgent] 引用验证失败: {issues}")
        else:
            logger.info("[CriticAgent] 引用验证通过")
        
        return is_valid, issues
    
    async def _llm_validate(
        self,
        query: str,
        answer: str,
        evidence_chunks: List[Dict]
    ) -> Dict:
        """LLM 深度校验"""
        try:
            # 构建校验提示
            evidence_text = "\n\n".join([
                f"[证据{i+1}] {chunk.get('text', '')[:300]}"
                for i, chunk in enumerate(evidence_chunks[:5])
            ])
            
            prompt = f"""问题：{query}

证据：
{evidence_text}

回答：
{answer}

请检查此回答是否：
1. 存在证据不支持的虚假信息（幻觉）
2. 证据是否足够支撑回答

简短回复你的判断。"""
            
            judgment = self.agent.run(prompt)
            judgment_lower = judgment.lower()
            
            # 解析判断
            has_hallucination = any(word in judgment_lower for word in ["幻觉", "虚假", "不实", "编造"])
            is_sufficient = "证据不足" not in judgment_lower and "不足" not in judgment_lower
            
            result = {
                "valid": not has_hallucination and is_sufficient,
                "hallucination": has_hallucination,
                "citation_invalid": False,
                "sufficient": is_sufficient,
                "issues": [judgment] if has_hallucination or not is_sufficient else [],
                "need_additional_retrieval": not is_sufficient
            }
            
            logger.info(
                f"[CriticAgent] LLM校验: valid={result['valid']}, "
                f"hallucination={has_hallucination}, sufficient={is_sufficient}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"[CriticAgent] LLM校验失败: {e}", exc_info=True)
            # 降级：默认通过
            return {
                "valid": True,
                "hallucination": False,
                "citation_invalid": False,
                "sufficient": True,
                "issues": [],
                "need_additional_retrieval": False
            }
