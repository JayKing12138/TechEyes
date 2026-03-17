"""研究 Agent - 负责信息收集"""

from .base import ReActBaseAgent
from .langchain_runtime import ToolRegistry, SearchTool

class ResearcherAgent(ReActBaseAgent):
    """研究 Agent - 收集历史信息和市场数据"""
    
    def __init__(self):
        # 创建工具注册表
        tool_registry = ToolRegistry()
        tool_registry.register_tool(SearchTool())
        
        super().__init__(
            name="Researcher",
            description="信息收集和研究专家",
            system_prompt="""你是技术行业研究专家。
            
你的职责：
1. 搜集关于指定主题的历史信息
2. 找到关键的时间点和里程碑
3. 收集相关公司的公开信息
4. 整理成时间轴和关键事件

使用搜索工具查找最新和历史信息。"""
        )
        
        self.agent.tool_registry = tool_registry
        self.agent.enable_tool_calling = True
    
    async def research(self, query: str, focus_companies: list = None):
        """执行研究"""
        companies_str = ", ".join(focus_companies) if focus_companies else "相关公司"
        
        prompt = f"""
研究主题：{query}
重点公司：{companies_str}

请深度研究这个主题，收集：
1. 历史背景和发展阶段
2. 关键事件和里程碑
3. 主要参与者和竞争动态
4. 市场规模和增长趋势

返回结构化的研究报告。
"""
        return await self.execute(prompt)
