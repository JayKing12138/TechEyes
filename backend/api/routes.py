"""API 路由"""

from fastapi import APIRouter, HTTPException, Query, Depends, Header, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional
import uuid
import asyncio
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, OperationalError

from database import get_db
from models.user import User
from services.analysis_service import AnalysisService
from services.chat_service import ChatService
from services.project_rag_service import project_rag_service
from services.news_cache import news_cache
from services.auth_service import (
    hash_password,
    verify_password,
    issue_access_token,
    verify_access_token,
)

router = APIRouter()

# 服务实例
analysis_service = AnalysisService()
chat_service = ChatService()

# 数据模型
class AnalysisRequest(BaseModel):
    query: str
    focus_companies: Optional[list[str]] = None
    analysis_depth: str = 'normal'  # quick, normal, deep
    include_future_prediction: bool = True

class CacheCheckRequest(BaseModel):
    query: str


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class ConversationCreateRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=120)


class ConversationMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=6000)


# 存储活跃的分析会话
active_sessions = {}


def _extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    value = authorization.strip()
    if not value.lower().startswith("bearer "):
        return None
    token = value[7:].strip()
    return token or None


def _extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    """从Authorization header中提取Bearer token"""
    if not authorization:
        return None
    value = authorization.strip()
    if value.lower().startswith("bearer "):
        return value[7:].strip()
    return None


def resolve_owner_key(
    authorization: Optional[str] = None,
    x_client_id: Optional[str] = None,
    access_token: Optional[str] = None,
    client_id: Optional[str] = None,
) -> str:
    """解析 owner_key：登录用户优先，否则使用游客 client_id。"""
    token = _extract_bearer_token(authorization) or access_token
    if token:
        payload = verify_access_token(token)
        user_id = None
        if payload:
            # 兼容两种字段名，避免误判为游客。
            user_id = payload.get("id") or payload.get("user_id")
        if user_id:
            return f"user:{user_id}"
        # Token无效时，降级为游客身份，而不是抛出401错误
        logger.warning("Token验证失败，降级为游客身份")

    anonymous_id = (x_client_id or client_id or "").strip()
    if not anonymous_id:
        raise HTTPException(status_code=400, detail="缺少客户端标识，请刷新页面后重试")
    return f"guest:{anonymous_id}"


@router.post("/auth/register")
async def register_user(request: RegisterRequest, db: Session = Depends(get_db)):
    """用户注册（用户名+密码）"""
    username = request.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="用户名不能为空")

    try:
        existing = db.query(User).filter(User.username == username).first()
    except OperationalError:
        raise HTTPException(
            status_code=503,
            detail="PostgreSQL 不可用或数据库不存在，请先创建数据库并重启后端",
        )
    except SQLAlchemyError as e:
        logger.error(f"注册查询失败: {e}")
        raise HTTPException(status_code=500, detail="数据库查询失败")

    if existing:
        raise HTTPException(status_code=409, detail="用户名已存在")

    user = User(
        username=username,
        password_hash=hash_password(request.password),
    )
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"注册写入失败: {e}")
        raise HTTPException(status_code=500, detail="注册失败，请稍后重试")

    return {
        "id": user.id,
        "username": user.username,
        "created_at": user.created_at.isoformat(),
    }


@router.post("/auth/login")
async def login_user(
    request: LoginRequest,
    db: Session = Depends(get_db),
    x_client_id: Optional[str] = Header(default=None),
):
    """用户登录"""
    username = request.username.strip()
    try:
        user = db.query(User).filter(User.username == username).first()
    except OperationalError:
        raise HTTPException(
            status_code=503,
            detail="PostgreSQL 不可用或数据库不存在，请先创建数据库并重启后端",
        )
    except SQLAlchemyError as e:
        logger.error(f"登录查询失败: {e}")
        raise HTTPException(status_code=500, detail="数据库查询失败")

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = issue_access_token(user.id, user.username)

    # 智能决策问答是独立模块：登录后把同浏览器 guest 会话并入当前账号。
    if x_client_id:
        moved = chat_service.claim_guest_conversations(guest_client_id=x_client_id, user_id=user.id)
        if moved["conversations"] or moved["messages"]:
            logger.info(
                f"登录会话归并 user={user.id} guest={x_client_id[:12]} "
                f"moved_conversations={moved['conversations']} moved_messages={moved['messages']}"
            )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
        },
    }

@router.post("/analyze")
async def submit_analysis(
    request: AnalysisRequest,
    authorization: Optional[str] = Header(default=None),
    x_client_id: Optional[str] = Header(default=None),
):
    """提交分析请求"""
    try:
        owner_key = resolve_owner_key(authorization=authorization, x_client_id=x_client_id)
        session_id = str(uuid.uuid4())

        # 统一缓存入口：命中则直接记录完成态会话，避免重复启动 ReAct 流程
        cached_result = await analysis_service.try_get_cached_result(request, owner_key)
        if cached_result is not None:
            analysis_service.record_cached_session(
                session_id=session_id,
                query=request.query,
                cached_result=cached_result,
                owner_key=owner_key,
            )
            logger.info(f"[{session_id}] 分析请求缓存命中，直接返回")
            return {"session_id": session_id, "cached": True}

        # 启动后台分析任务
        task = asyncio.create_task(
            analysis_service.analyze(session_id, request, owner_key)
        )
        active_sessions[session_id] = task
        
        logger.info(f"[{session_id}] 分析请求已接收：{request.query}")
        
        return {"session_id": session_id, "cached": False}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分析请求失败：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analysis/{session_id}/progress")
async def get_progress(
    session_id: str,
    authorization: Optional[str] = Header(default=None),
    x_client_id: Optional[str] = Header(default=None),
):
    """获取分析进度"""
    try:
        owner_key = resolve_owner_key(authorization=authorization, x_client_id=x_client_id)
        progress = analysis_service.get_progress(session_id, owner_key)
        if progress is None:
            raise HTTPException(status_code=404, detail="会话不存在")
        return progress
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取进度失败：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analysis/{session_id}/stream")
async def stream_analysis(
    session_id: str,
    access_token: Optional[str] = Query(default=None),
    client_id: Optional[str] = Query(default=None),
    authorization: Optional[str] = Header(default=None),
    x_client_id: Optional[str] = Header(default=None),
):
    """流式获取分析数据"""
    owner_key = resolve_owner_key(
        authorization=authorization,
        x_client_id=x_client_id,
        access_token=access_token,
        client_id=client_id,
    )

    async def event_generator():
        try:
            async for event in analysis_service.stream_progress(session_id, owner_key):
                yield f"data: {event}\n\n"
        except Exception as e:
            logger.error(f"流式分析失败：{str(e)}")
            yield f"data: {{'error': '{str(e)}'}}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )

@router.get("/analysis/{session_id}/result")
async def get_result(
    session_id: str,
    authorization: Optional[str] = Header(default=None),
    x_client_id: Optional[str] = Header(default=None),
):
    """获取完整分析结果"""
    try:
        owner_key = resolve_owner_key(authorization=authorization, x_client_id=x_client_id)
        result = analysis_service.get_result(session_id, owner_key)
        if result is None:
            raise HTTPException(status_code=404, detail="结果不存在或分析未完成")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取结果失败：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analysis/{session_id}/cancel")
async def cancel_analysis(
    session_id: str,
    authorization: Optional[str] = Header(default=None),
    x_client_id: Optional[str] = Header(default=None),
):
    """取消分析"""
    try:
        owner_key = resolve_owner_key(authorization=authorization, x_client_id=x_client_id)
        task = active_sessions.get(session_id)
        session = analysis_service.get_progress(session_id, owner_key)

        if task and session:
            task.cancel()
            del active_sessions[session_id]
            logger.info(f"[{session_id}] 分析已取消")
        
        return {"status": "cancelled"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消分析失败：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cache/check")
async def check_cache(
    request: CacheCheckRequest,
    authorization: Optional[str] = Header(default=None),
    x_client_id: Optional[str] = Header(default=None),
):
    """检查智能决策问答缓存（owner 维度私有缓存）。"""
    owner_key = resolve_owner_key(authorization=authorization, x_client_id=x_client_id)
    probe_request = AnalysisRequest(query=request.query)
    cached = await analysis_service.try_get_cached_result(probe_request, owner_key)
    return {
        "enabled": True,
        "hit": cached is not None,
        "result": cached,
        "message": "ok",
    }


@router.get("/history")
async def get_history(
    limit: int = Query(default=50, ge=1, le=200),
    query: Optional[str] = Query(default=None),
    authorization: Optional[str] = Header(default=None),
    x_client_id: Optional[str] = Header(default=None),
):
    """获取历史分析记录，支持关键词过滤"""
    try:
        owner_key = resolve_owner_key(authorization=authorization, x_client_id=x_client_id)
        items = analysis_service.list_history(owner_key=owner_key, limit=limit, keyword=query)
        return {
            "items": items,
            "total": len(items),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取历史记录失败：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/conversations")
async def create_conversation(
    request: ConversationCreateRequest,
    authorization: Optional[str] = Header(default=None),
    x_client_id: Optional[str] = Header(default=None),
):
    """创建多轮对话会话"""
    try:
        owner_key = resolve_owner_key(authorization=authorization, x_client_id=x_client_id)
        conv_id = str(uuid.uuid4())
        conversation = chat_service.create_conversation(
            conversation_id=conv_id,
            owner_key=owner_key,
            title=request.title,
        )
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/conversations")
async def list_conversations(
    limit: int = Query(default=50, ge=1, le=200),
    authorization: Optional[str] = Header(default=None),
    x_client_id: Optional[str] = Header(default=None),
    response: Response = None,
):
    """获取当前用户的会话列表"""
    try:
        owner_key = resolve_owner_key(authorization=authorization, x_client_id=x_client_id)
        
        # 检查是否降级为游客（token过期）
        token = _extract_bearer_token(authorization)
        is_token_expired = token and owner_key.startswith("guest:")
        
        items = chat_service.list_conversations(owner_key=owner_key, limit=limit)
        
        result = {"items": items, "total": len(items)}
        
        # 如果token过期，在响应中添加标识
        if is_token_expired and response:
            response.headers["X-Token-Expired"] = "true"
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    authorization: Optional[str] = Header(default=None),
    x_client_id: Optional[str] = Header(default=None),
):
    """获取会话消息"""
    try:
        owner_key = resolve_owner_key(authorization=authorization, x_client_id=x_client_id)
        items = chat_service.list_messages(conversation_id=conversation_id, owner_key=owner_key, limit=limit)
        if not items:
            return {"items": [], "total": 0}
        return {"items": items, "total": len(items)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话消息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/conversations/{conversation_id}/messages")
async def send_conversation_message(
    conversation_id: str,
    request: ConversationMessageRequest,
    authorization: Optional[str] = Header(default=None),
    x_client_id: Optional[str] = Header(default=None),
):
    """发送一条消息并获取助手回复"""
    try:
        owner_key = resolve_owner_key(authorization=authorization, x_client_id=x_client_id)
        data = await chat_service.send_message(
            conversation_id=conversation_id,
            owner_key=owner_key,
            content=request.content,
        )
        return data
    except ValueError as e:
        if str(e) == "conversation_not_found":
            raise HTTPException(status_code=404, detail="会话不存在")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发送会话消息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/chat/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    authorization: Optional[str] = Header(default=None),
    x_client_id: Optional[str] = Header(default=None),
):
    """删除指定会话"""
    try:
        owner_key = resolve_owner_key(authorization=authorization, x_client_id=x_client_id)
        deleted = chat_service.delete_conversation(conversation_id=conversation_id, owner_key=owner_key)

        if not deleted:
            raise HTTPException(status_code=404, detail="会话不存在或无权限删除")

        return {"status": "deleted", "conversation_id": conversation_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/stats")
async def get_cache_stats():
    """返回全局缓存统计（智能决策 / 项目知识工作台 / 科技新闻雷达）。"""
    try:
        return {
            "chat": chat_service.get_cache_stats(),
            "analysis": analysis_service.kv_cache.get_cache_stats(),
            "project_rag": project_rag_service.kv_cache.get_cache_stats(),
            "news_radar": news_cache.get_stats(),
        }
    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{session_id}")
async def delete_history(
    session_id: str,
    authorization: Optional[str] = Header(default=None),
    x_client_id: Optional[str] = Header(default=None),
):
    """删除指定的历史记录"""
    try:
        owner_key = resolve_owner_key(authorization=authorization, x_client_id=x_client_id)
        deleted = analysis_service.delete_history(session_id, owner_key)
        
        if not deleted:
            raise HTTPException(status_code=404, detail="记录不存在或无权删除")
        
        logger.info(f"[{session_id}] 历史记录已删除 (owner: {owner_key})")
        return {"status": "deleted", "session_id": session_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除历史记录失败：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
