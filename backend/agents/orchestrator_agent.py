"""协调 Agent - 负责任务分解"""

from .base import SimpleBaseAgent

class OrchestratorAgent(SimpleBaseAgent):
    """协调 Agent - 分解复杂任务为子任务"""
    
    def __init__(self):
        super().__init__(
            name="Orchestrator",
            description="任务分解和协调专家",
            system_prompt="""你是任务分解和协调专家。
            
你的职责：
1. 分析用户的分析请求
2. 将其分解为多个可执行的子任务
3. 为每个子任务确定责任 Agent
4. 规划执行顺序和依赖关系

返回格式（JSON）：
{
  "main_topic": "主题",
  "subtasks": [
    {
      "id": "task_id",
      "name": "任务名",
      "description": "详细描述",
      "agent": "Agent名称",
      "dependencies": ["task_id1", "task_id2"],
      "priority": "high/medium/low"
    }
  ],
  "analysis_focus": ["公司1", "公司2"],
  "required_depth": "quick/normal/deep"
}"""
        )
    
    async def decompose_task(self, query: str):
        """分解任务"""
        prompt = f"""
用户分析请求：{query}

请分解这个请求为具体的子任务，返回 JSON 格式。
"""
        return await self.execute(prompt)
