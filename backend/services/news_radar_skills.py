"""科技新闻雷达 Skills 服务：提供技能清单、技能执行与一键工作流。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from services.news_radar_service import news_radar_service


class NewsRadarSkillsService:
    """将新闻雷达模块封装为可编排的 skill 集。"""

    def list_skills(self) -> List[Dict[str, Any]]:
        """返回可用技能元数据。"""
        return [
            {
                "name": "refresh_hot_news",
                "description": "刷新科技新闻热榜并重建部分图谱数据",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "default": 20, "minimum": 5, "maximum": 50}
                    },
                },
                "requires_auth": False,
            },
            {
                "name": "get_hot_news",
                "description": "获取新闻热榜",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 50},
                        "force_refresh": {"type": "boolean", "default": False},
                    },
                },
                "requires_auth": False,
            },
            {
                "name": "get_news_detail",
                "description": "获取新闻详情与实体图谱",
                "input_schema": {
                    "type": "object",
                    "required": ["news_id"],
                    "properties": {
                        "news_id": {"type": "string"},
                    },
                },
                "requires_auth": False,
            },
            {
                "name": "analyze_entities",
                "description": "按图索骥分析（本地知识+互联网新闻联合检索）",
                "input_schema": {
                    "type": "object",
                    "required": ["entities"],
                    "properties": {
                        "entities": {"type": "array", "items": {"type": "string"}},
                        "news_id": {"type": "string"},
                        "question": {"type": "string"},
                    },
                },
                "requires_auth": False,
            },
            {
                "name": "followup",
                "description": "针对当前新闻项目进行追问",
                "input_schema": {
                    "type": "object",
                    "required": ["news_id", "question"],
                    "properties": {
                        "news_id": {"type": "string"},
                        "question": {"type": "string"},
                        "entities": {"type": "array", "items": {"type": "string"}},
                        "analysis_history": {"type": "array"},
                    },
                },
                "requires_auth": False,
            },
            {
                "name": "generate_report",
                "description": "生成雷达分析报告",
                "input_schema": {
                    "type": "object",
                    "required": ["news_id"],
                    "properties": {
                        "news_id": {"type": "string"},
                    },
                },
                "requires_auth": True,
            },
            {
                "name": "run_full_workflow",
                "description": "一键完成：抓取/刷新 -> 选新闻 -> 图谱分析 -> 追问 -> 报告生成",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "hot_limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
                        "ingest_limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 30},
                        "force_refresh": {"type": "boolean", "default": False},
                        "news_id": {"type": "string"},
                        "entities": {"type": "array", "items": {"type": "string"}},
                        "analysis_question": {"type": "string"},
                        "followup_question": {"type": "string"},
                        "generate_report": {"type": "boolean", "default": True},
                    },
                },
                "requires_auth": False,
            },
        ]

    async def execute_skill(
        self,
        skill_name: str,
        args: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """执行单个技能。"""
        args = args or {}

        dispatch = {
            "refresh_hot_news": self._skill_refresh_hot_news,
            "get_hot_news": self._skill_get_hot_news,
            "get_news_detail": self._skill_get_news_detail,
            "analyze_entities": self._skill_analyze_entities,
            "followup": self._skill_followup,
            "generate_report": self._skill_generate_report,
            "run_full_workflow": self._skill_run_full_workflow,
        }

        if skill_name not in dispatch:
            raise ValueError(f"未知技能: {skill_name}")

        result = await dispatch[skill_name](args=args, user_id=user_id)
        return {
            "skill": skill_name,
            "status": "ok",
            "result": result,
            "executed_at": datetime.utcnow().isoformat(),
        }

    async def _skill_refresh_hot_news(self, args: Dict[str, Any], user_id: Optional[int]) -> Dict[str, Any]:
        limit = int(args.get("limit", 20))
        await news_radar_service.refresh_hot_news(limit=limit)
        return {"message": "热榜刷新完成", "limit": limit}

    async def _skill_get_hot_news(self, args: Dict[str, Any], user_id: Optional[int]) -> Dict[str, Any]:
        limit = int(args.get("limit", 20))
        force_refresh = bool(args.get("force_refresh", False))
        items = await news_radar_service.get_hot_news(limit=limit, force_refresh=force_refresh)
        return {"items": items, "count": len(items)}

    async def _skill_get_news_detail(self, args: Dict[str, Any], user_id: Optional[int]) -> Dict[str, Any]:
        news_id = (args.get("news_id") or "").strip()
        if not news_id:
            raise ValueError("参数 news_id 不能为空")

        detail = await news_radar_service.get_news_detail(news_id)
        if not detail:
            raise ValueError("新闻不存在")
        return detail

    async def _skill_analyze_entities(self, args: Dict[str, Any], user_id: Optional[int]) -> Dict[str, Any]:
        entities = args.get("entities") or []
        if not isinstance(entities, list) or not entities:
            raise ValueError("参数 entities 不能为空")

        entity_names = [str(item).strip() for item in entities if str(item).strip()]
        if not entity_names:
            raise ValueError("参数 entities 至少包含一个有效实体")

        return await news_radar_service.analyze_entities(
            entity_names=entity_names,
            user_question=args.get("question"),
            news_id=args.get("news_id"),
            user_id=user_id,
        )

    async def _skill_followup(self, args: Dict[str, Any], user_id: Optional[int]) -> Dict[str, Any]:
        news_id = (args.get("news_id") or "").strip()
        question = (args.get("question") or "").strip()
        if not news_id:
            raise ValueError("参数 news_id 不能为空")
        if not question:
            raise ValueError("参数 question 不能为空")

        return await news_radar_service.generate_followup_answer(
            news_id=news_id,
            question=question,
            entities=args.get("entities"),
            analysis_history=args.get("analysis_history"),
            user_id=user_id,
        )

    async def _skill_generate_report(self, args: Dict[str, Any], user_id: Optional[int]) -> Dict[str, Any]:
        news_id = (args.get("news_id") or "").strip()
        if not news_id:
            raise ValueError("参数 news_id 不能为空")
        if not user_id:
            raise ValueError("生成报告需要登录用户身份")

        return await news_radar_service.generate_news_report(user_id=user_id, news_id=news_id)

    async def _skill_run_full_workflow(self, args: Dict[str, Any], user_id: Optional[int]) -> Dict[str, Any]:
        """一键执行雷达技能全流程。"""
        started_at = datetime.utcnow().isoformat()
        steps: List[Dict[str, Any]] = []

        query = (args.get("query") or "").strip()
        hot_limit = int(args.get("hot_limit", 10))
        ingest_limit = int(args.get("ingest_limit", 10))
        force_refresh = bool(args.get("force_refresh", False))

        if query:
            ingest_result = await news_radar_service.fetch_and_ingest_news(query=query, max_items=ingest_limit)
            steps.append(
                {
                    "name": "fetch_and_ingest_news",
                    "status": "ok",
                    "input": {"query": query, "ingest_limit": ingest_limit},
                    "output": ingest_result,
                }
            )

        if force_refresh:
            await news_radar_service.refresh_hot_news(limit=max(10, hot_limit))
            steps.append(
                {
                    "name": "refresh_hot_news",
                    "status": "ok",
                    "input": {"limit": max(10, hot_limit)},
                    "output": {"message": "热榜已刷新"},
                }
            )

        hot_items = await news_radar_service.get_hot_news(limit=hot_limit, force_refresh=False)
        steps.append(
            {
                "name": "get_hot_news",
                "status": "ok",
                "input": {"limit": hot_limit},
                "output": {"count": len(hot_items)},
            }
        )

        if not hot_items and not args.get("news_id"):
            raise ValueError("未获取到任何热榜新闻，无法继续执行工作流")

        target_news_id = (args.get("news_id") or (hot_items[0].get("id") if hot_items else "") or "").strip()
        if not target_news_id:
            raise ValueError("无法确定目标新闻，请传入 news_id")

        detail = await news_radar_service.get_news_detail(target_news_id)
        if not detail:
            raise ValueError(f"目标新闻不存在: {target_news_id}")

        steps.append(
            {
                "name": "get_news_detail",
                "status": "ok",
                "input": {"news_id": target_news_id},
                "output": {
                    "title": detail.get("news", {}).get("title"),
                    "entity_count": len(detail.get("graph", {}).get("nodes", [])),
                    "relation_count": len(detail.get("graph", {}).get("edges", [])),
                },
            }
        )

        entities = args.get("entities")
        if not entities:
            entities = [
                n.get("name")
                for n in detail.get("graph", {}).get("nodes", [])
                if n.get("name")
            ][:4]

        if not entities:
            title_fallback = detail.get("news", {}).get("title") or "科技新闻"
            entities = [title_fallback]

        analysis = await news_radar_service.analyze_entities(
            entity_names=entities,
            user_question=args.get("analysis_question"),
            news_id=target_news_id,
            user_id=user_id,
        )
        steps.append(
            {
                "name": "analyze_entities",
                "status": "ok",
                "input": {
                    "entities": entities,
                    "question": args.get("analysis_question"),
                },
                "output": {
                    "news_count": analysis.get("news_count", 0),
                    "local_news_count": analysis.get("local_news_count", 0),
                    "web_news_count": analysis.get("web_news_count", 0),
                },
            }
        )

        followup_result: Optional[Dict[str, Any]] = None
        followup_question = (args.get("followup_question") or "").strip()
        if followup_question:
            followup_result = await news_radar_service.generate_followup_answer(
                news_id=target_news_id,
                question=followup_question,
                entities=entities,
                analysis_history=[
                    {
                        "question": analysis.get("question"),
                        "answer": analysis.get("answer"),
                    }
                ],
                user_id=user_id,
            )
            steps.append(
                {
                    "name": "followup",
                    "status": "ok",
                    "input": {"question": followup_question},
                    "output": {"answer_preview": (followup_result.get("answer") or "")[:120]},
                }
            )

        report: Optional[Dict[str, Any]] = None
        should_generate_report = bool(args.get("generate_report", True))
        if should_generate_report and user_id:
            report = await news_radar_service.generate_news_report(user_id=user_id, news_id=target_news_id)
            steps.append(
                {
                    "name": "generate_report",
                    "status": "ok",
                    "input": {"news_id": target_news_id},
                    "output": {"generated_at": report.get("generated_at")},
                }
            )
        elif should_generate_report and not user_id:
            steps.append(
                {
                    "name": "generate_report",
                    "status": "skipped",
                    "reason": "未登录用户，跳过报告生成",
                }
            )

        ended_at = datetime.utcnow().isoformat()
        logger.info(f"[RadarSkills] 完成全流程执行 news_id={target_news_id} steps={len(steps)}")

        return {
            "workflow": "news_radar_full_workflow",
            "started_at": started_at,
            "ended_at": ended_at,
            "target_news_id": target_news_id,
            "hot_news_preview": hot_items[:5],
            "detail": detail,
            "analysis": analysis,
            "followup": followup_result,
            "report": report,
            "steps": steps,
        }


news_radar_skills_service = NewsRadarSkillsService()
