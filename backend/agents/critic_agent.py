"""批评 Agent - 负责质量审查"""

from .base import SimpleBaseAgent

class CriticAgent(SimpleBaseAgent):
    """批评 Agent - 质量审查和事实核实"""
    
    def __init__(self):
        super().__init__(
            name="Critic",
            description="质量审查和事实核实专家",
            system_prompt="""你是严格的质量审查专家。
            
你的职责：
1. 检查分析的逻辑完整性
2. 识别潜在的事实错误
3. 发现数据不一致
4. 指出分析漏洞
5. 建议改进方向

返回：
- 发现的问题列表
- 每个问题的严重程度（高/中/低）
- 改进建议"""
        )
    
    async def review(self, research_result: str = None, analysis_result: str = None):
        """执行质量审查"""
        prompt = f"""
请审查以下分析结果，找出问题：

【研究结果】
{research_result or '无'}

【分析结果】
{analysis_result or '无'}

请返回：
1. 发现的问题
2. 问题的严重程度
3. 改进建议"""
        
        return await self.execute(prompt)
