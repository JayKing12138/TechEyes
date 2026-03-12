"""分析 Agent - 负责数据分析"""

from .base import SimpleBaseAgent

class AnalyzerAgent(SimpleBaseAgent):
    """分析 Agent - 处理数据分析和对比"""
    
    def __init__(self):
        super().__init__(
            name="Analyzer",
            description="数据分析和对比专家",
            system_prompt="""你是数据分析和对比专家。
            
你的职责：
1. 分析行业数据和指标
2. 进行公司之间的对比分析
3. 识别优劣势和差异
4. 提供量化的分析结果

分析维度：
- 技术能力
- 市场份额
- 融资情况
- 产品策略
- 用户规模

返回结构化的分析结果。"""
        )
    
    async def analyze(self, query: str, focus_companies: list = None):
        """执行分析"""
        companies_str = ", ".join(focus_companies) if focus_companies else "相关公司"
        
        prompt = f"""
分析主题：{query}
对比对象：{companies_str}

请进行深度数据分析和对比，包括：
1. 主要指标对比表
2. 优劣势分析
3. 市场位置分析
4. 增长趋势预测

返回具体的数据和分析。
"""
        return await self.execute(prompt)
