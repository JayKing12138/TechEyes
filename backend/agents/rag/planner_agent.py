"""Planner Agent - 复杂问题拆解"""

import json
from typing import List, Dict
from loguru import logger
from agents.langchain_runtime import ReActLangChainAgent, LangChainLLM
from config import get_config


class PlannerAgent:
    """Planner Agent - 负责复杂问题拆解为子查询"""
    
    def __init__(self):
        config = get_config()
        self.llm = LangChainLLM(
            model=config.llm.model_id,
            api_key=config.llm.api_key,
            base_url=config.llm.base_url if config.llm.base_url else None,
            provider=config.llm.provider
        )
        
        self.agent = ReActLangChainAgent(
            name="PlannerAgent",
            llm=self.llm,
            system_prompt=self._get_system_prompt(),
            max_steps=4,
        )
    
    def _get_system_prompt(self) -> str:
        return """你是问题拆解专家，负责将复杂问题分解为多个子查询。

你的任务：
1. 分析用户的复杂问题
2. 识别问题中的多个维度或子问题
3. 将其拆解为 2-4 个独立的子查询
4. 每个子查询应该是独立可检索的

拆解原则：
- 对比问题 → 拆解为各实体的独立查询
- 趋势问题 → 拆解为不同时间段的查询
- 多维问题 → 拆解为各维度的查询
- 因果问题 → 拆解为原因查询和影响查询

返回 JSON 格式：
{
  "sub_queries": [
    {
      "id": 1,
      "query": "子查询1的具体文本",
      "focus": "该查询的重点是什么"
    },
    {
      "id": 2,
      "query": "子查询2的具体文本",
      "focus": "该查询的重点是什么"
    }
  ],
  "reasoning": "拆解理由"
}

只返回 JSON，不要其他内容。"""
    
    async def decompose(self, query: str, max_sub_queries: int = 4) -> List[str]:
        """
        拆解问题为子查询
        
        Args:
            query: 原始复杂问题
            max_sub_queries: 最大子查询数量
        
        Returns:
            子查询列表
        """
        try:
            logger.info(f"[PlannerAgent] 开始拆解问题: '{query[:50]}...'")
            
            prompt = f"用户问题：{query}\n\n请拆解为 2-{max_sub_queries} 个子查询，返回 JSON 格式。"
            response = self.agent.run(prompt)
            
            # 解析 JSON
            try:
                if "```json" in response:
                    json_str = response.split("```json")[1].split("```")[0].strip()
                elif "```" in response:
                    json_str = response.split("```")[1].split("```")[0].strip()
                else:
                    json_str = response.strip()
                
                result = json.loads(json_str)
                
                # 提取子查询
                sub_queries = [item["query"] for item in result.get("sub_queries", [])]
                
                if not sub_queries:
                    logger.warning("[PlannerAgent] 未拆解出子查询，使用原始问题")
                    return [query]
                
                logger.info(f"[PlannerAgent] 拆解完成: {len(sub_queries)} 个子查询")
                return sub_queries[:max_sub_queries]
                
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                logger.warning(f"[PlannerAgent] JSON 解析失败: {e}，使用原始问题")
                return [query]
            
        except Exception as e:
            logger.error(f"[PlannerAgent] 拆解失败: {e}", exc_info=True)
            return [query]
