"""Critic Agent - 质量校验"""

import re
from typing import List, Dict
from loguru import logger
from agents.langchain_runtime import SimpleLangChainAgent, LangChainLLM
from config import get_config


class CriticAgent:
    """Critic Agent - 负责答案质量校验和幻觉检测"""
    
    def __init__(self):
        config = get_config()
        self.llm = LangChainLLM(
            model=config.llm.model_id,
            api_key=config.llm.api_key,
            base_url=config.llm.base_url if config.llm.base_url else None,
            provider=config.llm.provider
        )
        
        self.agent = SimpleLangChainAgent(
            name="CriticAgent",
            llm=self.llm,
            system_prompt=self._get_system_prompt()
        )
        # POC阶段默认宽松校验：优先保证可回答，只有明显问题才拦截
        self.validation_mode = "lenient"
    
    def _get_system_prompt(self) -> str:
        return """你是质量审查专家，负责检查 RAG 回答质量（POC宽松模式）。

检查维度：
1. **幻觉检测**：回答中的事实是否都有证据支持？
2. **引用验证**：所有引用的 [文档N] 编号是否存在？
3. **证据充分性**：证据是否足以支撑回答？
4. **逻辑一致性**：回答是否自相矛盾？

判断原则（POC宽松）：
- 只要回答大体能回应问题、且没有明显编造/引用错误，就判定 "✅ 通过"。
- 只有存在明确幻觉或引用错误时，才判定失败。
- 证据略少、表述不够完整时，给出改进建议但仍可通过。

返回判断（简洁）：
- "✅ 通过" - 可用回答（允许轻微不完整）
- "❌ 幻觉" - 发现明确不实信息
- "❌ 引用无效" - 引用了不存在的文档
- "⚠️ 可优化" - 基本可用但可补充细节

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

    @staticmethod
    def _contains_non_negated_keyword(text: str, keywords: List[str]) -> bool:
        """检测是否包含未被否定词修饰的关键词。"""
        negation_tokens = ["无", "没有", "未", "未见", "未发现", "并无", "不存在"]
        for keyword in keywords:
            for match in re.finditer(re.escape(keyword), text):
                prefix = text[max(0, match.start() - 10): match.start()]
                if any(token in prefix for token in negation_tokens):
                    continue
                return True
        return False
    
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
            
            # 解析判断：支持否定语义，避免把“没有发现不实信息/幻觉”误判为失败
            pass_cues = ["✅ 通过", "校验通过", "质量合格", "可用", "基本可用", "可回答"]
            hallucination_fail_terms = ["存在幻觉", "有幻觉", "发现幻觉", "虚假", "不实", "编造"]
            sufficient_fail_terms = ["证据不足", "不足以", "依据不足", "支撑不足", "证据不够"]

            has_hallucination = self._contains_non_negated_keyword(judgment_lower, hallucination_fail_terms)
            has_sufficient_fail = self._contains_non_negated_keyword(judgment_lower, sufficient_fail_terms)
            has_explicit_pass = any(cue.lower() in judgment_lower for cue in pass_cues)

            if has_explicit_pass and not has_hallucination:
                is_sufficient = True
            else:
                is_sufficient = not has_sufficient_fail

            # POC宽松模式：证据轻微不足不阻断，仅在明显幻觉时判失败
            if self.validation_mode == "lenient":
                valid = not has_hallucination
            else:
                valid = (not has_hallucination) and is_sufficient
            
            result = {
                "valid": valid,
                "hallucination": has_hallucination,
                "citation_invalid": False,
                "sufficient": is_sufficient,
                "issues": [judgment] if has_hallucination else ([] if is_sufficient else ["回答基本可用，可补充更多证据细节"]),
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
