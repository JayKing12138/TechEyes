"""项目管理 API 路由"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from models.project import Project, ProjectDocument, ProjectConversation
from services.project_service import ProjectService
from services.document_service import DocumentService
from services.project_rag_service import project_rag_service
from services.auth_service import get_current_user
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import os
import asyncio
import re
from loguru import logger

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _build_conversation_title_from_message(message: str) -> str:
    """将首条用户问题转为对话标题，并去掉中英文标点符号。"""
    text = (message or "").strip()
    if not text:
        return "新对话"

    # 保留中英文、数字、空格，移除标点和其他符号。
    text = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return "新对话"

    return text[:40]

# ========== Pydantic Schema ==========

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    domain: Optional[str] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    domain: Optional[str] = None

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    domain: Optional[str]
    doc_count: int
    conversation_count: int
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True
        
    @classmethod
    def from_orm(cls, obj):
        return cls(
            id=obj.id,
            name=obj.name,
            description=obj.description,
            domain=obj.domain,
            doc_count=obj.doc_count or 0,
            conversation_count=obj.conversation_count or 0,
            created_at=obj.created_at.isoformat() if obj.created_at else None,
            updated_at=obj.updated_at.isoformat() if obj.updated_at else None
        )

class ProjectDetailResponse(ProjectResponse):
    stats: dict

class DocumentResponse(BaseModel):
    id: int
    filename: str
    source_type: str
    chunk_count: int
    file_size_kb: Optional[int]
    authority_score: float
    uploaded_at: str
    status: str  # "completed" or "processing"
    
    class Config:
        from_attributes = True
        
    @classmethod
    def from_orm(cls, obj):
        return cls(
            id=obj.id,
            filename=obj.filename,
            source_type=obj.source_type,
            chunk_count=obj.chunk_count or 0,
            file_size_kb=obj.file_size_kb,
            authority_score=obj.authority_score or 0.7,
            uploaded_at=obj.uploaded_at.isoformat() if obj.uploaded_at else None,
            status="completed" if obj.processed_at else "processing"
        )

class ConversationResponse(BaseModel):
    id: int
    title: str
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True
        
    @classmethod
    def from_orm(cls, obj):
        return cls(
            id=obj.id,
            title=obj.title or "未命名对话",
            created_at=obj.created_at.isoformat() if obj.created_at else None,
            updated_at=obj.updated_at.isoformat() if obj.updated_at else None
        )

class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    rag_info: Optional[dict] = None
    created_at: str
    
    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None

class ChatResponse(BaseModel):
    conversation_id: int
    message_id: int
    response: str
    rag_info: dict

# ========== 依赖注入 ==========

async def get_current_user_id(current_user: Optional[dict] = Depends(get_current_user)) -> int:
    """获取当前用户ID（从JWT token）"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或登录已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user["id"]

# ========== API 端点 ==========

@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    req: ProjectCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """创建项目"""
    service = ProjectService(db)
    try:
        project = service.create_project(
            user_id=user_id,
            name=req.name,
            description=req.description,
            domain=req.domain
        )
        return ProjectResponse.from_orm(project)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("", response_model=dict)
async def list_projects(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """列出用户的所有项目"""
    service = ProjectService(db)
    projects = service.get_projects(user_id)
    return {
        "projects": [ProjectResponse.from_orm(p) for p in projects]
    }

@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取项目详情"""
    service = ProjectService(db)
    project = service.get_project(project_id, user_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    stats = service.get_project_stats(project_id)
    
    response = ProjectResponse.from_orm(project)
    return ProjectDetailResponse(
        **response.dict(),
        stats=stats
    )

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    req: ProjectUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """更新项目"""
    service = ProjectService(db)
    
    update_data = req.dict(exclude_unset=True)
    project = service.update_project(project_id, user_id, **update_data)
    
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    return ProjectResponse.from_orm(project)

@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """删除项目"""
    service = ProjectService(db)
    success = service.delete_project(project_id, user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 删除项目后同步清理该项目的 KV 缓存（L1/L2/L3）
    await project_rag_service.invalidate_project_cache(project_id)
    
    return None

# ========== 文档管理 ==========

@router.get("/{project_id}/documents", response_model=dict)
async def get_documents(
    project_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取项目文档列表"""
    service = ProjectService(db)
    
    # 验证项目权限
    project = service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    documents = service.get_documents(project_id)
    return {
        "documents": [DocumentResponse.from_orm(d) for d in documents]
    }

@router.post("/{project_id}/documents", response_model=DocumentResponse, status_code=201)
async def upload_document(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """上传文档并进行向量化处理"""
    service = ProjectService(db)
    doc_service = DocumentService()
    
    # 验证项目权限
    project = service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 检查文件类型
    allowed_extensions = ['.pdf', '.docx', '.txt']
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file_ext}")
    
    # 读取文件内容
    file_content = await file.read()
    file_size_kb = len(file_content) // 1024
    
    # 确定source_type
    source_type_map = {
        '.pdf': 'user_pdf',
        '.docx': 'user_docx',
        '.txt': 'user_txt'
    }
    source_type = source_type_map.get(file_ext, 'user_file')
    
    # 创建文档记录（file_path 将在处理时更新）
    document = service.create_document(
        project_id=project_id,
        filename=file.filename,
        source_type=source_type,
        file_path=None,  # 将在 process_uploaded_file 中设置实际路径
        file_size_kb=file_size_kb if file_size_kb > 0 else 1,
        upload_user_id=user_id
    )
    
    # 后台任务：处理文档（解析、分块、向量化）
    logger.info(f"📤 开始处理文档: {file.filename} (doc_id={document.id})")
    
    # 异步处理文档，不阻塞响应
    async def _process_and_invalidate():
        await doc_service.process_uploaded_file(
            project_id=project_id,
            doc_id=document.id,
            file_content=file_content,
            filename=file.filename
        )
        # 文档处理完成后删除项目的 KV cache，避免旧缓存污染新文档
        await project_rag_service.invalidate_project_cache(project_id)

    asyncio.create_task(_process_and_invalidate())
    
    logger.info(f"📤 文档已提交处理: {file.filename} -> project {project_id}")
    
    return DocumentResponse.from_orm(document)

@router.delete("/{project_id}/documents/{doc_id}", status_code=204)
async def delete_document(
    project_id: int,
    doc_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """删除文档"""
    service = ProjectService(db)
    
    # 验证项目权限
    project = service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    success = service.delete_document(project_id, doc_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 同步清理 Chroma 中该文档的向量索引
    doc_service = DocumentService()
    doc_service.delete_document_vectors(doc_id)
    doc_service.delete_document_assets(project_id=project_id, doc_id=doc_id)
    # 文档删除后同步删除项目 KV cache
    await project_rag_service.invalidate_project_cache(project_id)
    
    return None


@router.get("/{project_id}/chunks/{chunk_id}", response_model=dict)
async def get_chunk_detail(
    project_id: int,
    chunk_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取引用的原文 chunk 详情"""
    service = ProjectService(db)

    project = service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    detail = service.get_chunk_detail(project_id, chunk_id)
    if not detail:
        raise HTTPException(status_code=404, detail="引用片段不存在")

    return detail

# ========== 对话管理 ==========

@router.get("/{project_id}/conversations", response_model=dict)
async def get_conversations(
    project_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取项目对话列表"""
    service = ProjectService(db)
    
    # 验证项目权限
    project = service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    conversations = service.get_conversations(project_id)
    return {
        "conversations": [ConversationResponse.from_orm(c) for c in conversations]
    }

@router.get("/{project_id}/conversations/{conversation_id}", response_model=dict)
async def get_conversation(
    project_id: int,
    conversation_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取对话详情（含消息）"""
    service = ProjectService(db)
    
    # 验证项目权限
    project = service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    conversation = service.get_conversation(project_id, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")
    
    messages = service.get_messages(conversation_id)
    
    message_list = []
    for msg in messages:
        msg_data = {
            "id": str(msg.id),
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat() if msg.created_at else None
        }
        
        # 添加RAG信息
        if msg.rag_used:
            msg_data["rag_info"] = {
                "used": True,
                "doc_used": msg.doc_used,
                "news_used": msg.news_used,
                "doc_count": len(msg.doc_ids) if msg.doc_ids else 0,
                "news_count": msg.search_results_count or 0,
                "doc_ids": msg.doc_ids or [],
                "chunk_ids": msg.chunk_ids or []
            }
        
        message_list.append(msg_data)
    
    return {
        "messages": message_list
    }


@router.delete("/{project_id}/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    project_id: int,
    conversation_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """删除指定对话及其消息"""
    service = ProjectService(db)

    # 验证项目权限
    project = service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    success = service.delete_conversation(project_id, conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="对话不存在")

    return None

@router.post("/{project_id}/chat", response_model=ChatResponse)
async def send_message(
    project_id: int,
    req: ChatRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """发送消息（双通道RAG：项目文档 + 新闻）"""
    service = ProjectService(db)
    
    # 验证项目权限
    project = service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 获取或创建对话
    if req.conversation_id:
        conversation = service.get_conversation(project_id, req.conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")
    else:
        conversation_title = _build_conversation_title_from_message(req.message)
        conversation = service.create_conversation(project_id, user_id, title=conversation_title)
    
    # 添加用户消息
    user_message = service.add_message(
        conversation_id=conversation.id,
        role="user",
        content=req.message
    )
    
    # 获取对话历史
    messages = service.get_messages(conversation_id=conversation.id)
    conversation_history = [
        {"role": msg.role, "content": msg.content}
        for msg in messages[-10:]  # 最近 10 条
    ]
    
    # 准备项目级长期记忆（摘要/关键结论）
    memories = service.get_recent_memories(
        project_id=project_id,
        limit=20,
        memory_types=["assistant_fact", "summary"],
    )
    project_memories_payload = [
        {
            "id": m.id,
            "memory_type": m.memory_type,
            "text": m.text_content,
            "strength": m.strength,
            "hit_count": m.hit_count,
        }
        for m in memories
    ]
    
    # 调用 RAG 服务生成回答
    logger.info(f"[ProjectChat] 开始 RAG 问答: project_id={project_id}, question='{req.message[:50]}...'")
    
    rag_result = await project_rag_service.answer_with_rag(
        project_id=project_id,
        question=req.message,
        conversation_history=conversation_history,
        enable_news=True,
        project_memories=project_memories_payload,
    )
    
    assistant_response = rag_result["answer"]
    rag_info = rag_result["rag_info"]
    
    # 添加助手消息
    assistant_message = service.add_message(
        conversation_id=conversation.id,
        role="assistant",
        content=assistant_response,
        rag_info=rag_info
    )
    
    logger.info(
        f"💬 项目对话完成: project_id={project_id}, conversation_id={conversation.id}, "
        f"doc_used={rag_info.get('doc_used')}, news_used={rag_info.get('news_used')}"
    )
    
    return ChatResponse(
        conversation_id=conversation.id,
        message_id=assistant_message.id,
        response=assistant_response,
        rag_info={
            "used": rag_info.get("used", False),
            "doc_used": rag_info.get("doc_used", False),
            "news_used": rag_info.get("news_used", False),
            "doc_count": rag_info.get("doc_count", 0),
            "news_count": rag_info.get("news_count", 0),
            "doc_ids": rag_info.get("doc_ids", []),
            "chunk_ids": rag_info.get("chunk_ids", []),
            "memory_used": rag_info.get("memory_used", False),
            "memory_count": rag_info.get("memory_count", 0),
            "cache_hit": rag_info.get("cache_hit", False),
            "cache_source": rag_info.get("cache_source"),
        }
    )
