"""项目管理模型"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, BigInteger, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from database import Base


class Project(Base):
    """项目表"""
    __tablename__ = "projects"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
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
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
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
    images = relationship("ProjectDocumentImage", back_populates="document", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_project_documents_project_id", "project_id"),
        Index("idx_project_documents_uploaded_at", "uploaded_at"),
    )


class ProjectDocumentChunk(Base):
    """文档分块表"""
    __tablename__ = "project_document_chunks"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    document_id = Column(BigInteger, ForeignKey("project_documents.id", ondelete="CASCADE"), nullable=False)
    
    chunk_index = Column(Integer, nullable=False)  # 分块顺序 0, 1, 2, ...
    text_content = Column(Text, nullable=False)  # 分块文本
    embedding_json = Column(JSONB)  # 向量嵌入 (1536维)
    token_count = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    document = relationship("ProjectDocument", back_populates="chunks")
    
    __table_args__ = (
        Index("idx_project_document_chunks_document_id", "document_id"),
    )


class ProjectDocumentImage(Base):
    """文档图片表（多模态元数据）"""
    __tablename__ = "project_document_images"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    document_id = Column(BigInteger, ForeignKey("project_documents.id", ondelete="CASCADE"), nullable=False)

    page_number = Column(Integer, nullable=False)  # PDF页码（从1开始）
    image_index = Column(Integer, nullable=False)  # 页内图片序号（从1开始）
    image_path = Column(String(512), nullable=False)  # 本地存储路径
    image_format = Column(String(16))  # png/jpeg/... 
    width = Column(Integer)
    height = Column(Integer)
    color_space = Column(String(32))
    extra_meta = Column(JSONB)

    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    document = relationship("ProjectDocument", back_populates="images")

    __table_args__ = (
        Index("idx_project_document_images_document_id", "document_id"),
        Index("idx_project_document_images_page_number", "page_number"),
    )


class ProjectConversation(Base):
    """项目对话表"""
    __tablename__ = "project_conversations"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
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
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
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
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
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
