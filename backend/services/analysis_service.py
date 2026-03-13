"""分析服务 - 核心的 Multi-Agent 分析逻辑"""

import asyncio
import json
import re
from datetime import datetime
from typing import AsyncGenerator, Optional
from loguru import logger
import httpx

from config import get_config
from agents.orchestrator_agent import OrchestratorAgent
from agents.researcher_agent import ResearcherAgent
from agents.analyzer_agent import AnalyzerAgent
from agents.synthesizer_agent import SynthesizerAgent
from agents.critic_agent import CriticAgent
from services.history_store import HistoryStore
from tools.search_tools import TavilyTool, SERPAPITool

config = get_config()

class AnalysisService:
    """分析服务 - 协调多个 Agent 完成分析任务"""
    
    def __init__(self):
        self.sessions = {}
        self.history_store = HistoryStore()

        # ReAct 多Agent工作流
        self.orchestrator_agent = OrchestratorAgent()
        self.researcher_agent = ResearcherAgent()
        self.analyzer_agent = AnalyzerAgent()
        self.synthesizer_agent = SynthesizerAgent()
        self.critic_agent = CriticAgent()
        
        # 初始化搜索工具（主+备用）
        self.primary_search = TavilyTool() if config.search.tavily_api_key else SERPAPITool()
        self.fallback_search = SERPAPITool() if config.search.tavily_api_key else None

    @staticmethod
    def _tool_name(tool) -> str:
        return tool.__class__.__name__ if tool else "None"

    @staticmethod
    def _extract_json_block(raw_text: str) -> Optional[dict]:
        """从模型输出中尽力提取 JSON 对象。"""
        text = (raw_text or "").strip()
        if not text:
            return None

        if "```json" in text:
            try:
                text = text.split("```json", 1)[1].split("```", 1)[0].strip()
            except Exception:
                pass
        elif "```" in text:
            try:
                text = text.split("```", 1)[1].split("```", 1)[0].strip()
            except Exception:
                pass

        try:
            obj = json.loads(text)
            return obj if isinstance(obj, dict) else None
        except Exception:
            pass

        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return None
        try:
            obj = json.loads(match.group(0))
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None
    
    async def analyze(self, session_id: str, request, owner_key: str):
        """执行完整的分析流程 - MVP版本"""
        try:
            # 初始化会话状态
            self.sessions[session_id] = {
                "session_id": session_id,
                "owner_key": owner_key,
                "query": request.query,
                "status": "analyzing",
                "progress": 0,
                "result": None,
                "start_time": datetime.now(),
                "errors": [],
                "steps": []
            }
            self.history_store.upsert_session(self.sessions[session_id])
            
            logger.info(f"[{session_id}] 开始分析：{request.query}")
            logger.info(f"[{session_id}] [MCP] 当前分析流程未接入 MCP 远程工具，使用本地 Tool 类执行")
            
            # 步骤 1：任务分解（ReAct-Orchestrator）
            logger.info(f"[{session_id}] 步骤 1/5：任务分解（ReAct）")
            self.sessions[session_id]["progress"] = 15
            self.sessions[session_id]["steps"].append("正在进行任务分解（ReAct）...")

            decompose_raw = await self.orchestrator_agent.decompose_task(request.query)
            decompose_result = self._extract_json_block(decompose_raw) or {}
            focus_companies = request.focus_companies or decompose_result.get("analysis_focus") or []
            subtasks = decompose_result.get("subtasks") or []

            # 步骤 2：搜索相关信息
            logger.info(f"[{session_id}] 步骤 2/5：搜索信息")
            self.sessions[session_id]["progress"] = 30
            self.sessions[session_id]["steps"].append("正在搜索相关信息...")
            
            logger.info(
                f"[{session_id}] [FunctionCall] {self._tool_name(self.primary_search)}.search(query='{request.query[:60]}', max_results=5)"
            )
            search_results = await self.primary_search.search(request.query, max_results=5)
            logger.info(f"[{session_id}] [FunctionReturn] {self._tool_name(self.primary_search)}.search -> {len(search_results)} results")
            
            # 主搜索失败时尝试备用搜索
            if not search_results and self.fallback_search:
                logger.warning(f"[{session_id}] 主搜索失败，尝试备用搜索...")
                self.sessions[session_id]["steps"].append("主搜索失败，切换备用搜索...")
                logger.info(
                    f"[{session_id}] [FunctionCall] {self._tool_name(self.fallback_search)}.search(query='{request.query[:60]}', max_results=5)"
                )
                search_results = await self.fallback_search.search(request.query, max_results=5)
                logger.info(f"[{session_id}] [FunctionReturn] {self._tool_name(self.fallback_search)}.search -> {len(search_results)} results")
            
            if not search_results:
                self.sessions[session_id]["status"] = "error"
                self.sessions[session_id]["steps"].append("所有搜索源均失败，请检查 API 配置或稍后重试")
                logger.error(f"[{session_id}] 所有搜索源均失败")
                raise RuntimeError("搜索失败：所有搜索源均不可用，请检查 TAVILY/SERPAPI 配置")
            
            # 步骤 3：研究与分析（ReAct-Researcher/Analyzer）
            logger.info(f"[{session_id}] 步骤 3/5：研究与分析（ReAct）")
            self.sessions[session_id]["progress"] = 55
            self.sessions[session_id]["steps"].append("正在进行研究与分析（ReAct）...")

            subtask_text = "\n".join(
                f"- {t.get('name') or t.get('id')}: {t.get('description', '')}" for t in subtasks[:6] if isinstance(t, dict)
            )
            enriched_query = request.query
            if subtask_text:
                enriched_query += f"\n\n子任务上下文:\n{subtask_text}"

            research_result = await self.researcher_agent.research(
                enriched_query,
                focus_companies=focus_companies,
            )
            analysis_result_text = await self.analyzer_agent.analyze(
                request.query,
                focus_companies=focus_companies,
            )

            # 步骤 4：质量审查（ReAct-Critic）
            logger.info(f"[{session_id}] 步骤 4/5：质量审查（ReAct）")
            self.sessions[session_id]["progress"] = 75
            self.sessions[session_id]["steps"].append("正在执行质量审查（ReAct）...")

            review_result = await self.critic_agent.review(
                research_result=research_result,
                analysis_result=analysis_result_text,
            )

            # 步骤 5：综合生成（ReAct-Synthesizer）
            logger.info(f"[{session_id}] 步骤 5/5：综合生成（ReAct）")
            self.sessions[session_id]["progress"] = 90
            self.sessions[session_id]["steps"].append("正在综合生成最终报告（ReAct）...")

            synthesis_raw = await self.synthesizer_agent.synthesize(
                query=request.query,
                research=research_result,
                analysis=analysis_result_text,
                review=review_result,
                depth=request.analysis_depth,
                include_future=request.include_future_prediction,
            )
            synthesis_json = self._extract_json_block(synthesis_raw)

            if not synthesis_json:
                logger.warning(f"[{session_id}] ReAct 综合结果未返回有效 JSON，回退到传统 LLM 结构化生成")
                synthesis_json = await self._call_llm_analysis(request.query, search_results)

            final_result = {
                "query": request.query,
                "summary": synthesis_json.get("summary", "分析完成"),
                "timeline": synthesis_json.get("timeline", []),
                "comparisons": synthesis_json.get("comparisons", []),
                "futureOutlook": synthesis_json.get("futureOutlook", ""),
                "sources": [{"title": r["title"], "url": r.get("url", "")} for r in search_results],
                "metadata": {
                    "analyzed_at": datetime.now().isoformat(),
                    "session_id": session_id,
                    "search_results_count": len(search_results),
                    "agent_mode": "react",
                    "focus_companies": focus_companies,
                    "subtask_count": len(subtasks),
                }
            }
            
            # 完成
            self.sessions[session_id]["progress"] = 100
            self.sessions[session_id]["status"] = "completed"
            self.sessions[session_id]["result"] = final_result
            self.sessions[session_id]["end_time"] = datetime.now()
            self.sessions[session_id]["steps"].append("分析完成！")
            self.history_store.upsert_session(self.sessions[session_id])
            
            logger.info(f"[{session_id}] 分析完成")
            
        except Exception as e:
            logger.error(f"[{session_id}] 分析失败：{str(e)}")
            self.sessions[session_id]["status"] = "error"
            self.sessions[session_id]["errors"].append(str(e))
            self.history_store.upsert_session(self.sessions[session_id])

    def record_cached_session(self, session_id: str, query: str, cached_result: dict, owner_key: str):
        """记录缓存命中的会话，便于前端展示历史记录"""
        self.sessions[session_id] = {
            "session_id": session_id,
            "owner_key": owner_key,
            "query": query,
            "status": "completed",
            "progress": 100,
            "result": cached_result,
            "start_time": datetime.now(),
            "end_time": datetime.now(),
            "errors": [],
            "steps": ["缓存命中，已直接返回结果"],
        }
        self.history_store.upsert_session(self.sessions[session_id])
    
    async def _call_llm_analysis(self, query: str, search_results: list) -> dict:
        """调用 LLM 进行分析"""
        try:
            # 构建上下文
            context = "\n\n".join([
                f"【来源 {i+1}】{r['title']}\n{r['snippet']}"
                for i, r in enumerate(search_results)
            ])
            
            prompt = f"""请基于以下搜索结果，对"{query}"进行深度分析。

搜索结果：
{context}

请以JSON格式返回分析结果，包含：
1. summary: 执行摘要（200字以内）
2. timeline: 关键时间节点数组，每项包含 date（时间）和 event（事件）
3. comparisons: 对比分析数组，每项包含 dimension（维度）、details（详情）
4. futureOutlook: 未来展望（200字以内）

返回纯JSON，不要其他文字。"""

            # 调用 LLM
            async with httpx.AsyncClient(timeout=60.0) as client:
                headers = {
                    "Content-Type": "application/json",
                }
                
                # 根据不同的provider设置不同的header和endpoint
                if config.llm.provider == "openai":
                    headers["Authorization"] = f"Bearer {config.llm.api_key}"
                    url = f"{config.llm.base_url or 'https://api.openai.com/v1'}/chat/completions"
                elif config.llm.provider == "anthropic":
                    headers["x-api-key"] = config.llm.api_key
                    headers["anthropic-version"] = "2023-06-01"
                    url = f"{config.llm.base_url or 'https://api.anthropic.com'}/v1/messages"
                else:
                    # 通用 OpenAI 兼容接口
                    headers["Authorization"] = f"Bearer {config.llm.api_key}"
                    url = f"{config.llm.base_url}/chat/completions"

                logger.info(
                    f"[FunctionCall] LLM.post provider={config.llm.provider} model={config.llm.model_id} "
                    f"url={url} sources={len(search_results)}"
                )
                
                payload = {
                    "model": config.llm.model_id,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000
                }
                
                # Anthropic 使用不同的格式
                if config.llm.provider == "anthropic":
                    payload = {
                        "model": config.llm.model_id,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 2000
                    }
                
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                logger.info(f"[FunctionReturn] LLM.post status={response.status_code}")
                
                data = response.json()
                
                # 提取响应内容
                if config.llm.provider == "anthropic":
                    content = data["content"][0]["text"]
                else:
                    content = data["choices"][0]["message"]["content"]
                
                # 尝试解析 JSON
                try:
                    # 移除可能的 markdown 代码块标记
                    content = content.strip()
                    if content.startswith("```json"):
                        content = content[7:]
                    if content.startswith("```"):
                        content = content[3:]
                    if content.endswith("```"):
                        content = content[:-3]
                    content = content.strip()
                    
                    result = json.loads(content)
                    return result
                except json.JSONDecodeError:
                    logger.warning("LLM 返回非 JSON 格式，使用默认结构")
                    return {
                        "summary": content[:200],
                        "timeline": [],
                        "comparisons": [],
                        "futureOutlook": "分析结果见摘要"
                    }
                    
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return {
                "summary": f"针对'{query}'的分析结果。基于搜索到的{len(search_results)}条信息进行综合分析。",
                "timeline": [
                    {"date": "2024", "event": "主要发展阶段"},
                    {"date": "2025", "event": "关键里程碑"},
                    {"date": "2026", "event": "当前状态"}
                ],
                "comparisons": [
                    {"dimension": "技术能力", "details": "综合评估中"},
                    {"dimension": "市场表现", "details": "数据分析中"}
                ],
                "futureOutlook": "基于当前趋势，预计该领域将持续发展。"
            }
    
    async def stream_progress(self, session_id: str, owner_key: str) -> AsyncGenerator[str, None]:
        """实时流式返回进度"""
        if session_id not in self.sessions:
            yield json.dumps({"error": "会话不存在"})
            return

        if self.sessions[session_id].get("owner_key") != owner_key:
            yield json.dumps({"error": "无权访问该会话"})
            return
        
        last_progress = 0
        last_step_count = 0
        while True:
            session = self.sessions[session_id]
            
            # 发送进度更新
            if session["progress"] != last_progress:
                yield json.dumps({
                    "type": "progress",
                    "progress": session["progress"],
                    "status": session["status"]
                })
                last_progress = session["progress"]
            
            # 发送步骤更新
            steps = session.get("steps", [])
            if len(steps) > last_step_count:
                for step in steps[last_step_count:]:
                    yield json.dumps({
                        "type": "step_update",
                        "message": step
                    })
                last_step_count = len(steps)
            
            # 完成或错误
            if session["status"] in ["completed", "error"]:
                yield json.dumps({
                    "type": "completed" if session["status"] == "completed" else "error",
                    "status": session["status"],
                    "result": session.get("result") if session["status"] == "completed" else None,
                    "errors": session.get("errors") if session["status"] == "error" else None
                })
                break
            
            await asyncio.sleep(0.5)
    
    def get_progress(self, session_id: str, owner_key: str) -> Optional[dict]:
        """获取当前进度"""
        session = self.sessions.get(session_id)
        if not session:
            return None
        if session.get("owner_key") != owner_key:
            return None
        return session
    
    def get_result(self, session_id: str, owner_key: str) -> Optional[dict]:
        """获取完整结果"""
        session = self.sessions.get(session_id)
        if session and session.get("owner_key") == owner_key and session["status"] == "completed":
            return session["result"]
        return self.history_store.get_result(session_id, owner_key)

    def list_history(self, owner_key: str, limit: int = 50, keyword: Optional[str] = None) -> list[dict]:
        """列出历史分析记录（按时间倒序）"""
        return self.history_store.list_history(owner_key=owner_key, limit=limit, keyword=keyword)

    def delete_history(self, session_id: str, owner_key: str) -> bool:
        """删除历史记录"""
        # 同时从内存会话中删除（如果存在）
        if session_id in self.sessions:
            session = self.sessions[session_id]
            if session.get("owner_key") == owner_key:
                del self.sessions[session_id]
        
        # 从持久化存储中删除
        return self.history_store.delete_session(session_id, owner_key)
