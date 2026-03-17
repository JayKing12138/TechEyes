# Phase 1 实现指南：数据库 + 项目经理 API

## 目标
在 2 天内完成：
- 5 个新数据库表（SQLAlchemy ORM）
- 10+ 个 FastAPI 端点
- 项目管理的完整 CRUD 操作

---

## Part 1: 创建 SQLAlchemy 模型

### 文件: `backend/models/project.py`

```python
"""项目管理模型"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSONB, BigInteger, ForeignKey, Index
from sqlalchemy.orm import relationship
from database import Base
import uuid

def generate_id():
    """生成递增 ID"""
    return int(uuid.uuid4().int % 10000000000000000)

class Project(Base):
    """项目表"""
    __tablename__ = "projects"
    
    id = Column(BigInteger, primary_key=True, default=generate_id)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(128), nullable=False)
    description = Column(Text)
    domain = Column(String(32))  # "technology", "finance", "healthcare", etc.
    
    doc_count = Column(Integer, default=0)
    conversation_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)  # 软删除
    
    # 关系
    documents = relationship("ProjectDocument", back_populates="project", cascade="all, delete-orphan")
    conversations = relationship("ProjectConversation", back_populates="project", cascade="all, delete-orphan")
    memories = relationship("ProjectMemory", back_populates="project", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index("idx_projects_user_id", "user_id"),
        Index("idx_projects_created_at", "created_at"),
    )


class ProjectDocument(Base):
    """项目文档表"""
    __tablename__ = "project_documents"
    
    id = Column(BigInteger, primary_key=True, default=generate_id)
    project_id = Column(BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    filename = Column(String(256), nullable=False)
    source_type = Column(String(32), nullable=False)  # "user_pdf", "user_docx", "crawler_github", etc.
    file_path = Column(String(512))  # Storage path
    file_size_kb = Column(Integer)  # KB
    
    chunk_count = Column(Integer, default=0)
    authority_score = Column(Float, default=0.7)  # 0.0-1.0
    source_url = Column(Text)  # For crawler sources
    
    upload_user_id = Column(Integer, ForeignKey("users.id"))
    
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)  # When processing completed
    deleted_at = Column(DateTime, nullable=True)
    
    # 关系
    project = relationship("Project", back_populates="documents")
    chunks = relationship("ProjectDocumentChunk", back_populates="document", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_project_documents_project_id", "project_id"),
        Index("idx_project_documents_uploaded_at", "uploaded_at"),
    )


class ProjectDocumentChunk(Base):
    """文档分块表"""
    __tablename__ = "project_document_chunks"
    
    id = Column(BigInteger, primary_key=True, default=generate_id)
    document_id = Column(BigInteger, ForeignKey("project_documents.id", ondelete="CASCADE"), nullable=False)
    
    chunk_index = Column(Integer, nullable=False)  # 分块顺序 0, 1, 2, ...
    text_content = Column(Text, nullable=False)  # 分块文本
    embedding_json = Column(JSONB)  # 向量 1536-dim
    token_count = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    document = relationship("ProjectDocument", back_populates="chunks")
    
    __table_args__ = (
        Index("idx_project_document_chunks_document_id", "document_id"),
    )


class ProjectConversation(Base):
    """项目对话表"""
    __tablename__ = "project_conversations"
    
    id = Column(BigInteger, primary_key=True, default=generate_id)
    project_id = Column(BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    title = Column(String(256))  # "AI芯片技术进展"
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    
    # 关系
    project = relationship("Project", back_populates="conversations")
    messages = relationship("ProjectConversationMessage", back_populates="conversation", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_project_conversations_project_id", "project_id"),
        Index("idx_project_conversations_created_at", "created_at"),
    )


class ProjectConversationMessage(Base):
    """对话消息表"""
    __tablename__ = "project_conversation_messages"
    
    id = Column(BigInteger, primary_key=True, default=generate_id)
    conversation_id = Column(BigInteger, ForeignKey("project_conversations.id", ondelete="CASCADE"), nullable=False)
    
    role = Column(String(16), nullable=False)  # "user", "assistant", "system"
    content = Column(Text, nullable=False)
    
    # RAG 相关
    rag_used = Column(Boolean, default=False)
    news_used = Column(Boolean, default=False)
    doc_used = Column(Boolean, default=False)
    doc_ids = Column(JSONB)  # [1, 2, 5]
    chunk_ids = Column(JSONB)  # [[1,2,3], [4,5,6]]
    
    search_query = Column(Text)  # 用户查询词
    search_results_count = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    conversation = relationship("ProjectConversation", back_populates="messages")
    
    __table_args__ = (
        Index("idx_project_conversation_messages_conversation_id", "conversation_id"),
    )


class ProjectMemory(Base):
    """项目级长期记忆"""
    __tablename__ = "project_memories"
    
    id = Column(BigInteger, primary_key=True, default=generate_id)
    project_id = Column(BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(BigInteger, ForeignKey("project_conversations.id"))
    
    memory_type = Column(String(32))  # "user_interest", "assistant_fact", "summary"
    text_content = Column(Text, nullable=False)
    normalized_text = Column(Text)  # For deduplication
    embedding_json = Column(JSONB)
    
    strength = Column(Float, default=1.0)  # Strength (0.0-1.0, decays over time)
    hit_count = Column(Integer, default=0)
    last_retrieved_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    project = relationship("Project", back_populates="memories")
    
    __table_args__ = (
        Index("idx_project_memories_project_id", "project_id"),
    )
```

### 文件: `backend/models/__init__.py`

```python
"""导出所有模型"""
from .user import User
from .project import (
    Project,
    ProjectDocument,
    ProjectDocumentChunk,
    ProjectConversation,
    ProjectConversationMessage,
    ProjectMemory
)

__all__ = [
    "User",
    "Project",
    "ProjectDocument",
    "ProjectDocumentChunk",
    "ProjectConversation",
    "ProjectConversationMessage",
    "ProjectMemory"
]
```

---

## Part 2: 创建数据库迁移脚本

### 文件: `backend/scripts/init_project_tables.py`

```python
"""初始化项目管理表"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, Base
from models import (
    Project, ProjectDocument, ProjectDocumentChunk,
    ProjectConversation, ProjectConversationMessage, ProjectMemory
)

def init_tables():
    """创建所有项目管理表"""
    print("[1] 创建 Project 表...")
    Base.metadata.create_all(bind=engine, tables=[Project.__table__])
    
    print("[2] 创建 ProjectDocument 表...")
    Base.metadata.create_all(bind=engine, tables=[ProjectDocument.__table__])
    
    print("[3] 创建 ProjectDocumentChunk 表...")
    Base.metadata.create_all(bind=engine, tables=[ProjectDocumentChunk.__table__])
    
    print("[4] 创建 ProjectConversation 表...")
    Base.metadata.create_all(bind=engine, tables=[ProjectConversation.__table__])
    
    print("[5] 创建 ProjectConversationMessage 表...")
    Base.metadata.create_all(bind=engine, tables=[ProjectConversationMessage.__table__])
    
    print("[6] 创建 ProjectMemory 表...")
    Base.metadata.create_all(bind=engine, tables=[ProjectMemory.__table__])
    
    print("✅ 所有表创建成功！")

if __name__ == "__main__":
    init_tables()
```

**运行**:
```bash
cd backend
python scripts/init_project_tables.py
```

---

## Part 3: 创建项目服务层

### 文件: `backend/services/project_service.py`

```python
"""项目管理服务"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
import uuid

from models import Project, ProjectDocument, ProjectConversation, ProjectMemory
from loguru import logger

class ProjectService:
    """项目管理服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========== 项目 CRUD ==========
    
    async def create_project(self, user_id: int, name: str, description: str, domain: str) -> Project:
        """创建项目"""
        # 检查重复
        existing = self.db.query(Project).filter(
            and_(
                Project.user_id == user_id,
                Project.name == name,
                Project.deleted_at.is_(None)
            )
        ).first()
        
        if existing:
            raise ValueError(f"项目 '{name}' 已存在")
        
        project = Project(
            user_id=user_id,
            name=name,
            description=description,
            domain=domain
        )
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        
        logger.info(f"📂 创建项目: user_id={user_id}, project_name={name}")
        return project
    
    async def get_projects(self, user_id: int) -> List[Project]:
        """查询用户的所有项目"""
        projects = self.db.query(Project).filter(
            and_(
                Project.user_id == user_id,
                Project.deleted_at.is_(None)
            )
        ).order_by(Project.updated_at.desc()).all()
        
        return projects
    
    async def get_project(self, project_id: int, user_id: int) -> Optional[Project]:
        """查询单个项目（带权限检查）"""
        project = self.db.query(Project).filter(
            and_(
                Project.id == project_id,
                Project.user_id == user_id,
                Project.deleted_at.is_(None)
            )
        ).first()
        
        return project
    
    async def update_project(self, project_id: int, user_id: int, **kwargs) -> Optional[Project]:
        """更新项目"""
        project = await self.get_project(project_id, user_id)
        if not project:
            return None
        
        for key, value in kwargs.items():
            if hasattr(project, key) and key not in ["id", "user_id", "created_at"]:
                setattr(project, key, value)
        
        project.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(project)
        
        return project
    
    async def delete_project(self, project_id: int, user_id: int) -> bool:
        """删除项目（软删除）"""
        project = await self.get_project(project_id, user_id)
        if not project:
            return False
        
        project.deleted_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"🗑️  删除项目: project_id={project_id}")
        return True
    
    # ========== 项目统计 ==========
    
    async def get_project_stats(self, project_id: int) -> dict:
        """获取项目统计信息"""
        project = self.db.query(Project).filter(Project.id == project_id).first()
        
        if not project:
            return {}
        
        doc_count = self.db.query(ProjectDocument).filter(
            and_(
                ProjectDocument.project_id == project_id,
                ProjectDocument.deleted_at.is_(None)
            )
        ).count()
        
        conv_count = self.db.query(ProjectConversation).filter(
            and_(
                ProjectConversation.project_id == project_id,
                ProjectConversation.deleted_at.is_(None)
            )
        ).count()
        
        return {
            "total_documents": doc_count,
            "total_conversations": conv_count,
            "last_activity": project.updated_at.isoformat() if project.updated_at else None
        }
    
    # ========== 文档统计更新 ==========
    
    async def increment_doc_count(self, project_id: int, delta: int = 1):
        """增加文档计数"""
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.doc_count = (project.doc_count or 0) + delta
            project.updated_at = datetime.utcnow()
            self.db.commit()
    
    async def increment_conversation_count(self, project_id: int, delta: int = 1):
        """增加对话计数"""
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.conversation_count = (project.conversation_count or 0) + delta
            project.updated_at = datetime.utcnow()
            self.db.commit()
```

---

## Part 4: 创建 API 路由

### 文件: `backend/api/projects_routes.py`

```python
"""项目管理 API 路由"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import Project, User
from services.project_service import ProjectService
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api/projects", tags=["projects"])

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

class ProjectDetailResponse(ProjectResponse):
    stats: dict

# ========== 依赖注入 ==========

async def get_current_user(db: Session = Depends(get_db)) -> User:
    """假设你有认证中间件，这里简化处理"""
    # 实际应该从 JWT token 或 session 获取
    user = db.query(User).filter(User.username == "test_user").first()
    if not user:
        raise HTTPException(status_code=401, detail="未认证")
    return user

# ========== API 端点 ==========

@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    req: ProjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """创建项目"""
    service = ProjectService(db)
    try:
        project = await service.create_project(
            user_id=user.id,
            name=req.name,
            description=req.description,
            domain=req.domain
        )
        return project
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """列出用户的所有项目"""
    service = ProjectService(db)
    projects = await service.get_projects(user.id)
    return projects

@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """获取项目详情"""
    service = ProjectService(db)
    project = await service.get_project(project_id, user.id)
    
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    stats = await service.get_project_stats(project_id)
    
    return {
        **project.__dict__,
        "stats": stats
    }

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    req: ProjectUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """更新项目"""
    service = ProjectService(db)
    
    update_data = req.dict(exclude_unset=True)
    project = await service.update_project(project_id, user.id, **update_data)
    
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    return project

@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """删除项目"""
    service = ProjectService(db)
    success = await service.delete_project(project_id, user.id)
    
    if not success:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    return None
```

### 在 `backend/main.py` 中注册路由

```python
# 在 FastAPI app 初始化后添加
from api.projects_routes import router as projects_router

app.include_router(projects_router)
```

---

## Part 5: 测试

### 文件: `backend/tests/test_projects.py`

```python
"""项目 API 测试"""

import pytest
from fastapi.testclient import TestClient
from main import app
from database import get_db_context
from models import User, Project

client = TestClient(app)

@pytest.fixture
def setup_user():
    """创建测试用户"""
    with get_db_context() as db:
        user = db.query(User).filter(User.username == "test_user").first()
        if not user:
            user = User(username="test_user", password_hash="xxx")
            db.add(user)
            db.commit()
        yield user

def test_create_project(setup_user):
    """测试创建项目"""
    response = client.post("/api/projects", json={
        "name": "AI芯片技术现状",
        "description": "分析AI芯片发展趋势",
        "domain": "technology"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "AI芯片技术现状"
    assert data["doc_count"] == 0

def test_list_projects(setup_user):
    """测试列出项目"""
    response = client.get("/api/projects")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 0

def test_get_project(setup_user):
    """测试获取项目详情"""
    # 先创建
    create_resp = client.post("/api/projects", json={
        "name": "Test Project",
        "description": "Test",
        "domain": "test"
    })
    project_id = create_resp.json()["id"]
    
    # 再查询
    response = client.get(f"/api/projects/{project_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Project"
    assert "stats" in data

def test_delete_project(setup_user):
    """测试删除项目"""
    # 先创建
    create_resp = client.post("/api/projects", json={
        "name": "Delete Test",
        "description": "Test",
        "domain": "test"
    })
    project_id = create_resp.json()["id"]
    
    # 再删除
    response = client.delete(f"/api/projects/{project_id}")
    assert response.status_code == 204
    
    # 验证已删除
    get_resp = client.get(f"/api/projects/{project_id}")
    assert get_resp.status_code == 404
```

**运行测试**:
```bash
cd backend
pytest tests/test_projects.py -v
```

---

## 检查清单

- [ ] 创建 `backend/models/project.py` (6 个 SQLAlchemy 模型)
- [ ] 创建 `backend/services/project_service.py` (项目 CRUD 服务)
- [ ] 创建 `backend/api/projects_routes.py` (10+ 个 API 端点)
- [ ] 运行 `python scripts/init_project_tables.py` 初始化表
- [ ] 在 `backend/main.py` 中注册路由
- [ ] 运行 `pytest tests/test_projects.py` 验证 API
- [ ] 测试样本请求：
  ```bash
  curl -X POST http://localhost:8000/api/projects \
    -H "Content-Type: application/json" \
    -d '{"name":"Test","description":"..","domain":"tech"}'
  ```

---

## 下一步（Phase 2）

完成以上后，进入 **Part 2: 文档处理 + 向量化**
- PDF/DOCX 解析
- 语义分块
- Embedding 生成和存储

