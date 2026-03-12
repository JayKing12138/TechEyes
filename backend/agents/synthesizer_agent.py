"""综合 Agent - 负责结果融合"""

from .base import SimpleBaseAgent

class SynthesizerAgent(SimpleBaseAgent):
    """综合 Agent - 融合多个 Agent 的结果"""
    
    def __init__(self):
        super().__init__(
            name="Synthesizer",
            description="结果融合和报告生成专家",
            system_prompt="""你是结果融合和报告生成专家。
            
你的职责：
1. 融合多个 Agent 的分析结果
2. 消除冲突和重复
3. 构建一致的叙述
4. 生成结构化的最终报告

返回格式：JSON，包含：
- summary: 摘要
- timeline: 时间轴
- comparisons: 对比分析
- futureOutlook: 未来展望
- metadata: 元数据"""
        )
    
    async def synthesize(self, query: str, research: str = None, 
                        analysis: str = None, review: str = None,
                        depth: str = 'normal', include_future: bool = True):
        """综合结果"""
        prompt = f"""
主题：{query}
分析深度：{depth}
包含未来展望：{include_future}

【研究数据】
{research or '无'}

【分析数据】
{analysis or '无'}

【质量评审意见】
{review or '无'}

请融合以上所有数据，生成结构化的最终报告。

报告应包括：
1. 执行摘要 (summary)
2. 历史时间轴 (timeline)
3. 多维度对比分析 (comparisons)
4. 未来发展展望 (futureOutlook)
5. 数据来源 (sources)

返回 JSON 格式。"""
        
        return await self.execute(prompt)
