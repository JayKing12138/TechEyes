"""Router Agent - 意图识别和路由决策"""

import json
from typing import Dict
from loguru import logger
from agents.langchain_runtime import ReActLangChainAgent, LangChainLLM
from config import get_config


class RouterAgent:
    """Router Agent - 问题意图识别和路由决策"""
    
    def __init__(self):
        config = get_config()
        self.llm = LangChainLLM(
            model=config.llm.model_id,
            api_key=config.llm.api_key,
            base_url=config.llm.base_url if config.llm.base_url else None,
            provider=config.llm.provider
        )
        
        self.agent = ReActLangChainAgent(
            name="RouterAgent",
            llm=self.llm,
            system_prompt=self._get_system_prompt(),
            max_steps=4,
        )
    
    def _get_system_prompt(self) -> str:
        return """你是意图识别专家，负责分析用户问题并做出路由决策。

你需要判断以下维度：

1. **问题类型** (intent):
   - "fact_query": 事实查询（明确答案存在于文档中）
   - "comparison": 对比分析（需要比较多个实体）
   - "trend_analysis": 趋势判断（需要时间序列信息）
   - "exploration": 探索性问题（开放式、需要综合分析）
   - "strategy_recommendation": 针对宏观挑战、发展路径、治理策略给出系统性对策方案（例如“应该如何解决”“发展路径是什么”）

2. **复杂度** (complexity):
   - "simple": 简单问题（单一维度，直接检索）
   - "medium": 中等复杂（需要多个文档片段）
   - "high": 高复杂度（需要拆解为子问题）

3. **是否需要Web检索** (need_web):
   - true: 需要最新动态、实时信息、政策更新
   - false: 文档内容足够

4. **是否需要文档检索** (need_doc):
   - true: 需要项目文档支持
   - false: 纯外部信息

5. **是否允许使用模型通识知识补充答案** (allow_model_knowledge):
   - true: 可以在项目文档/新闻以外补充通用行业/领域知识，但需要在回答中说明哪些是“超出当前文档的一般性建议”
   - false: 回答尽量限制在项目文档和新闻证据内

返回 JSON 格式：
{
  "intent": "fact_query|comparison|trend_analysis|exploration|strategy_recommendation",
  "complexity": "simple|medium|high",
  "need_web": true|false,
  "need_doc": true|false,
  "allow_model_knowledge": true|false,
  "reasoning": "你的分析理由"
}

只返回 JSON，不要其他内容。"""
    
    async def route(self, query: str) -> Dict:
        """
        路由决策
        
        Args:
            query: 用户问题
        
        Returns:
            路由结果字典
        """
        try:
            prompt = f"用户问题：{query}\n\n请分析并返回 JSON 格式的路由决策。"
            response = self.agent.run(prompt)
            
            # 尝试解析 JSON
            try:
                # 提取 JSON（可能包含 markdown 代码块）
                if "```json" in response:
                    json_str = response.split("```json")[1].split("```")[0].strip()
                elif "```" in response:
                    json_str = response.split("```")[1].split("```")[0].strip()
                else:
                    json_str = response.strip()
                
                result = json.loads(json_str)
                
                # 验证必要字段
                required_fields = ["intent", "complexity", "need_web", "need_doc"]
                for field in required_fields:
                    if field not in result:
                        raise ValueError(f"缺少字段: {field}")
                
                # 填充可选字段的默认值
                if "allow_model_knowledge" not in result:
                    # 策略/对策类或探索类问题默认允许使用通识知识
                    intent = result.get("intent", "")
                    result["allow_model_knowledge"] = intent in ["strategy_recommendation", "exploration"]
                
                logger.info(
                    f"[RouterAgent] 路由决策: intent={result['intent']}, "
                    f"complexity={result['complexity']}, "
                    f"need_web={result['need_web']}, need_doc={result['need_doc']}"
                )
                
                return result
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"[RouterAgent] JSON 解析失败: {e}，使用默认路由")
                return self._default_routing()
            
        except Exception as e:
            logger.error(f"[RouterAgent] 路由失败: {e}", exc_info=True)
            return self._default_routing()
    
    def _default_routing(self) -> Dict:
        """默认路由策略"""
        return {
            "intent": "fact_query",
            "complexity": "medium",
            "need_web": False,
            "need_doc": True,
            "reasoning": "使用默认路由策略"
        }
