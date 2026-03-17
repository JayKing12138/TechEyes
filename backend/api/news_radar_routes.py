"""科技新闻雷达 API 路由"""

from typing import List, Optional
from loguru import logger

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse
from io import BytesIO
from pydantic import BaseModel, Field

from services.news_radar_service import news_radar_service
from services.news_radar_skills import news_radar_skills_service
from services.news_trend_analyzer import trend_analyzer
from services.auth_service import get_current_user


router = APIRouter(prefix="/api/radar", tags=["news-radar"])


class HotNewsItem(BaseModel):
    id: str
    title: str
    url: Optional[str] = None
    snippet: Optional[str] = None
    created_at: Optional[str] = None


class HotNewsResponse(BaseModel):
    items: List[HotNewsItem]


class NewsDetailResponse(BaseModel):
    news: dict
    graph: dict


class AnalyzeEntitiesRequest(BaseModel):
    entities: List[str] = Field(min_length=1, description="一个或多个实体名称")
    news_id: Optional[str] = Field(default=None, description="当前雷达项目的新闻ID")
    question: Optional[str] = Field(
        default=None,
        description="可选的分析问题，不填则使用默认问题模板",
    )


class AnalyzeEntitiesResponse(BaseModel):
    question: str
    entities: List[str]
    news_count: int
    news: list
    local_news_count: Optional[int] = 0
    web_news_count: Optional[int] = 0
    answer: str
    memory_used: Optional[bool] = False
    cache_hit: Optional[bool] = False
    cache_source: Optional[str] = None


class FollowupRequest(BaseModel):
    news_id: str
    question: str = Field(min_length=1, description="追问内容")
    entities: Optional[List[str]] = Field(default=None, description="当前选中的实体")
    analysis_history: Optional[list] = Field(default=None, description="前端已有分析记录")


class FollowupResponse(BaseModel):
    question: str
    entities: List[str]
    answer: str
    news: list
    memory_used: Optional[bool] = False
    cache_hit: Optional[bool] = False
    cache_source: Optional[str] = None


class SearchNewsRequest(BaseModel):
    query: str = Field(min_length=1, description="搜索关键词")
    limit: int = Field(default=20, ge=1, le=50)


class ReportResponse(BaseModel):
    news: dict
    graph: dict
    user_history: dict
    entities_summary: dict
    related_entities: list
    related_searches: list
    report_markdown: Optional[str] = None
    generated_at: str


class RadarSkillExecuteRequest(BaseModel):
    skill: str = Field(min_length=1, description="技能名称")
    args: dict = Field(default_factory=dict, description="技能输入参数")


class RadarWorkflowRequest(BaseModel):
    query: Optional[str] = Field(default=None, description="可选：先按关键词抓取并入库")
    hot_limit: int = Field(default=10, ge=1, le=50)
    ingest_limit: int = Field(default=10, ge=1, le=30)
    force_refresh: bool = Field(default=False, description="是否先刷新热榜")
    news_id: Optional[str] = Field(default=None, description="指定目标新闻ID，不填则使用热榜第一条")
    entities: Optional[List[str]] = Field(default=None, description="指定分析实体")
    analysis_question: Optional[str] = Field(default=None, description="按图索骥分析问题")
    followup_question: Optional[str] = Field(default=None, description="可选追问")
    generate_report: bool = Field(default=True, description="是否在流程末尾生成报告")


@router.get("/hot", response_model=HotNewsResponse)
async def get_hot_news(
    limit: int = Query(default=20, ge=1, le=50),
    force_refresh: bool = Query(default=False, description="强制刷新，获取最新新闻")
):
    """获取科技新闻热榜（优先搜索工具获取最新新闻）。"""
    items = await news_radar_service.get_hot_news(limit=limit, force_refresh=force_refresh)
    return {"items": items}


@router.get("/search", response_model=HotNewsResponse)
async def search_news(
    query: str = Query(min_length=1, description="搜索关键词"),
    limit: int = Query(default=20, ge=1, le=50)
):
    """搜索新闻（基于标题和摘要）"""
    items = await news_radar_service.search_news(query=query, limit=limit)
    return {"items": items}


@router.get("/archives", response_model=HotNewsResponse)
async def get_search_archives(
    limit: int = Query(default=50, ge=1, le=100)
):
    """获取搜索档案（用户搜索过的主题档案列表）"""
    items = await news_radar_service.get_search_archives(limit=limit)
    return {"items": items}


@router.get("/news/{news_id}", response_model=NewsDetailResponse)
async def get_news_detail(news_id: str, current_user: Optional[dict] = Depends(get_current_user)):
    """获取某条新闻的详情 + 实体图谱数据。"""
    detail = await news_radar_service.get_news_detail(news_id)
    if not detail:
        raise HTTPException(status_code=404, detail="新闻不存在")
    
    # 日志记录：确保source_urls被返回
    source_urls = detail.get("news", {}).get("source_urls", [])
    logger.debug(f"[NewsRadar API] 返回新闻{news_id}，包含{len(source_urls)}条source_urls")
    
    if current_user:
        news_radar_service.record_news_view(
            user_id=current_user["id"],
            news_id=news_id,
            news_data=detail["news"]
        )
    
    return detail


@router.post("/analyze-entities", response_model=AnalyzeEntitiesResponse)
async def analyze_entities(payload: AnalyzeEntitiesRequest, current_user: Optional[dict] = Depends(get_current_user)):
    """按图索骥：基于实体组合和近期新闻做综合分析。"""
    result = await news_radar_service.analyze_entities(
        entity_names=payload.entities,
        user_question=payload.question,
        news_id=payload.news_id,
        user_id=current_user["id"] if current_user and payload.news_id else None,
    )
    return result


@router.post("/followup", response_model=FollowupResponse)
async def followup_question(payload: FollowupRequest, current_user: Optional[dict] = Depends(get_current_user)):
    """在当前雷达项目下继续追问。"""
    try:
        result = await news_radar_service.generate_followup_answer(
            news_id=payload.news_id,
            question=payload.question,
            entities=payload.entities,
            analysis_history=payload.analysis_history,
            user_id=current_user["id"] if current_user else None,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/history")
async def get_news_history(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """获取用户的雷达档案（查看历史）"""
    result = news_radar_service.get_user_news_history(
        user_id=current_user["id"],
        limit=limit,
        offset=offset
    )
    return result


@router.get("/news/{news_id}/my-history")
async def get_news_my_history(
    news_id: str,
    current_user: Optional[dict] = Depends(get_current_user)
):
    """获取当前用户在该新闻下的按图索骥与追问历史，供前端刷新后恢复。"""
    if not current_user:
        return {
            "analysis_runs": [],
            "followups": [],
            "short_term_memory": {"window": [], "summary": "", "last_topics": []},
            "long_term_memory": {
                "facts": [],
                "preferences": {"focus_areas": [], "response_style": "evidence-first"},
                "entity_interests": {},
            },
            "user_profile": {
                "focus_areas": [],
                "style_preferences": {"response_style": "evidence-first"},
                "entity_interest": {},
                "topic_interest": {},
                "updated_at": "",
            },
        }
    return news_radar_service.get_news_item_user_history(
        user_id=current_user["id"],
        news_id=news_id,
    )


@router.get("/news/{news_id}/memory")
async def get_news_memory(
    news_id: str,
    current_user: Optional[dict] = Depends(get_current_user)
):
    """获取当前用户在该新闻下的短期/长期记忆快照。"""
    if not current_user:
        return {
            "short_term_memory": {"window": [], "summary": "", "last_topics": []},
            "long_term_memory": {
                "facts": [],
                "preferences": {"focus_areas": [], "response_style": "evidence-first"},
                "entity_interests": {},
            },
            "user_profile": {
                "focus_areas": [],
                "style_preferences": {"response_style": "evidence-first"},
                "entity_interest": {},
                "topic_interest": {},
                "updated_at": "",
            },
            "memory_context": {"short_text": "- 无短期记忆", "long_text": "- 无长期记忆", "digest": ""},
        }
    return news_radar_service.get_news_item_memory(
        user_id=current_user["id"],
        news_id=news_id,
    )


@router.get("/news/{news_id}/report", response_model=ReportResponse)
async def generate_news_report(
    news_id: str,
    current_user: dict = Depends(get_current_user)
):
    """生成雷达报告（用户在该新闻下的所有操作和分析结果）"""
    try:
        report = await news_radar_service.generate_news_report(
            user_id=current_user["id"],
            news_id=news_id
        )
        return report
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/news/{news_id}/report/pdf")
async def download_news_report_pdf(
    news_id: str,
    current_user: dict = Depends(get_current_user)
):
    """导出雷达报告 PDF。"""
    try:
        report = await news_radar_service.generate_news_report(
            user_id=current_user["id"],
            news_id=news_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfgen import canvas

        pdf_buffer = BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=A4)
        width, height = A4

        # 中文字体优先尝试系统字体，不可用时回退英文显示
        font_name = "Helvetica"
        for fpath, fname in [
            ("/System/Library/Fonts/PingFang.ttc", "PingFang"),
            ("/System/Library/Fonts/STHeiti Light.ttc", "STHeiti"),
        ]:
            try:
                pdfmetrics.registerFont(TTFont(fname, fpath))
                font_name = fname
                break
            except Exception:
                continue

        c.setFont(font_name, 13)
        y = height - 48
        lines = []
        lines.append(f"TechEyes 雷达报告 - {report.get('news', {}).get('title', '新闻项目')}")
        lines.append(f"生成时间: {report.get('generated_at', '')}")
        lines.append("")
        lines.append((report.get("report_markdown") or "").replace("#", "").replace("*", ""))

        for raw_line in lines:
            chunks = [raw_line[i:i + 52] for i in range(0, len(raw_line), 52)] or [""]
            for line in chunks:
                c.drawString(36, y, line)
                y -= 20
                if y < 40:
                    c.showPage()
                    c.setFont(font_name, 13)
                    y = height - 48

        c.save()
        pdf_buffer.seek(0)
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=radar-report-{news_id}.pdf"},
        )
    except Exception:
        raise HTTPException(status_code=500, detail="PDF 生成失败，请安装 reportlab")


@router.get("/trends/entities")
async def get_trending_entities(
    days: int = Query(default=7, ge=1, le=30, description="分析时间范围（天）"),
    limit: int = Query(default=20, ge=1, le=50)
):
    """获取趋势实体（最近N天最频繁出现的实体）"""
    try:
        results = trend_analyzer.get_trending_entities(days=days, limit=limit)
        return {"items": results, "days": days}
    except Exception as e:
        logger.error(f"获取趋势实体失败: {e}")
        raise HTTPException(status_code=500, detail="获取趋势实体失败")


@router.get("/trends/topics")
async def get_hot_topics(
    days: int = Query(default=7, ge=1, le=30, description="分析时间范围（天）"),
    limit: int = Query(default=10, ge=1, le=30)
):
    """获取热门话题（基于实体共现分析）"""
    try:
        results = trend_analyzer.get_hot_topics(days=days, limit=limit)
        return {"topics": results, "days": days}
    except Exception as e:
        logger.error(f"获取热门话题失败: {e}")
        raise HTTPException(status_code=500, detail="获取热门话题失败")


@router.get("/trends/entity/{entity_name}/timeline")
async def get_entity_timeline(
    entity_name: str,
    days: int = Query(default=30, ge=1, le=365, description="时间范围（天）")
):
    """获取实体的时间线（每天出现的新闻数）"""
    try:
        result = trend_analyzer.get_entity_timeline(entity_name=entity_name, days=days)
        return result
    except Exception as e:
        logger.error(f"获取实体时间线失败: {e}")
        raise HTTPException(status_code=500, detail="获取实体时间线失败")


@router.delete("/news/{news_id}")
async def delete_news(
    news_id: str,
    current_user: Optional[dict] = Depends(get_current_user)
):
    """删除新闻（仅管理员或本人可删除）"""
    try:
        success = await news_radar_service.delete_news(news_id)
        if success:
            return {"message": "新闻删除成功", "news_id": news_id}
        else:
            raise HTTPException(status_code=404, detail="新闻不存在")
    except Exception as e:
        logger.error(f"删除新闻失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除新闻失败: {str(e)}")


@router.delete("/news")
async def delete_all_news():
    """删除全部新闻数据（用于全量重建最新热榜）。"""
    try:
        result = await news_radar_service.delete_all_news()
        return {"message": "已清空全部新闻", **result}
    except Exception as e:
        logger.error(f"清空全部新闻失败: {e}")
        raise HTTPException(status_code=500, detail=f"清空失败: {str(e)}")


@router.delete("/cache")
async def invalidate_news_cache(
    scope: str = Query(default="all", description="失效范围: all | hot | detail"),
    news_id: Optional[str] = Query(default=None, description="scope=detail 时指定新闻 ID")
):
    """
    清除科技新闻雷达缓存（L1+L2）。
    - scope=all: 清除全部新闻缓存
    - scope=hot: 仅清除热榜缓存
    - scope=detail&news_id=xxx: 清除指定新闻详情缓存
    """
    try:
        if scope == "hot":
            result = news_cache.invalidate_hot_news()
            return {"scope": "hot", **result}
        elif scope == "detail":
            if not news_id:
                raise HTTPException(status_code=400, detail="scope=detail 时必须提供 news_id")
            result = news_cache.invalidate_news_detail(news_id)
            return {"scope": "detail", "news_id": news_id, **result}
        else:
            result = news_cache.invalidate_all()
            return {"scope": "all", **result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清除雷达缓存失败: {e}")
        raise HTTPException(status_code=500, detail=f"清除缓存失败: {str(e)}")


@router.post("/refresh")
async def refresh_hot_news(
    limit: int = Query(default=20, ge=5, le=50, description="抓取新闻数量")
):
    """手动刷新热榜（从搜索工具获取最新新闻）"""
    try:
        await news_radar_service.refresh_hot_news(limit=limit)
        return {"message": f"已刷新热榜，抓取 {limit} 条最新新闻"}
    except Exception as e:
        logger.error(f"刷新热榜失败: {e}")
        raise HTTPException(status_code=500, detail=f"刷新失败: {str(e)}")


@router.get("/skills")
async def list_radar_skills():
    """列出科技新闻雷达模块可用技能。"""
    skills = news_radar_skills_service.list_skills()
    return {
        "items": skills,
        "count": len(skills),
    }


@router.post("/skills/execute")
async def execute_radar_skill(
    payload: RadarSkillExecuteRequest,
    current_user: Optional[dict] = Depends(get_current_user),
):
    """执行单个科技新闻雷达技能。"""
    try:
        result = await news_radar_skills_service.execute_skill(
            skill_name=payload.skill,
            args=payload.args,
            user_id=current_user["id"] if current_user else None,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"执行雷达技能失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="执行雷达技能失败")


@router.post("/skills/workflow")
async def run_radar_skill_workflow(
    payload: RadarWorkflowRequest,
    current_user: Optional[dict] = Depends(get_current_user),
):
    """一键执行新闻雷达技能全流程。"""
    try:
        result = await news_radar_skills_service.execute_skill(
            skill_name="run_full_workflow",
            args=payload.model_dump(),
            user_id=current_user["id"] if current_user else None,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"执行雷达全流程失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="执行雷达全流程失败")


