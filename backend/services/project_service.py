"""项目管理服务"""

from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, text
from loguru import logger

from models.project import (
    Project,
    ProjectDocument,
    ProjectConversation,
    ProjectConversationMessage,
    ProjectMemory,
)


class ProjectService:
    """项目管理服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========== 项目 CRUD ==========
    
    def create_project(self, user_id: int, name: str, description: str = None, domain: str = None) -> Project:
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
    
    def get_projects(self, user_id: int) -> List[Project]:
        """查询用户的所有项目"""
        projects = self.db.query(Project).filter(
            and_(
                Project.user_id == user_id,
                Project.deleted_at.is_(None)
            )
        ).order_by(desc(Project.updated_at)).all()
        
        return projects
    
    def get_project(self, project_id: int, user_id: int = None) -> Optional[Project]:
        """查询单个项目（带权限检查）"""
        query = self.db.query(Project).filter(
            and_(
                Project.id == project_id,
                Project.deleted_at.is_(None)
            )
        )
        
        if user_id is not None:
            query = query.filter(Project.user_id == user_id)
        
        project = query.first()
        return project
    
    def update_project(self, project_id: int, user_id: int, **kwargs) -> Optional[Project]:
        """更新项目"""
        project = self.get_project(project_id, user_id)
        if not project:
            return None
        
        for key, value in kwargs.items():
            if hasattr(project, key) and key not in ["id", "user_id", "created_at"]:
                setattr(project, key, value)
        
        project.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(project)
        
        logger.info(f"✏️  更新项目: project_id={project_id}")
        return project
    
    def delete_project(self, project_id: int, user_id: int) -> bool:
        """删除项目（软删除）"""
        project = self.get_project(project_id, user_id)
        if not project:
            return False
        
        project.deleted_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"🗑️  删除项目: project_id={project_id}")
        return True
    
    # ========== 项目统计 ==========
    
    def get_project_stats(self, project_id: int) -> Dict:
        """获取项目统计信息"""
        project = self.db.query(Project).filter(Project.id == project_id).first()
        
        if not project:
            return {}
        
        doc_count = self.db.query(ProjectDocument).filter(
            and_(
                ProjectDocument.project_id == project_id,
                ProjectDocument.deleted_at.is_(None),
                ProjectDocument.processed_at.isnot(None),  # 只计数已处理完成的文档
                ProjectDocument.chunk_count > 0  # 确保有内容
            )
        ).count()
        
        conv_count = self.db.query(ProjectConversation).filter(
            and_(
                ProjectConversation.project_id == project_id,
                ProjectConversation.deleted_at.is_(None)
            )
        ).count()
        
        # 计算总chunk数
        total_chunks = self.db.execute(
            text(
                """
            SELECT COALESCE(SUM(chunk_count), 0) 
            FROM project_documents 
            WHERE project_id = :project_id AND deleted_at IS NULL
            """
            ),
            {"project_id": project_id}
        ).scalar()
        
        return {
            "total_documents": doc_count,
            "total_conversations": conv_count,
            "total_chunks": total_chunks or 0,
            "last_activity": project.updated_at.isoformat() if project.updated_at else None
        }
    
    # ========== 文档管理 ==========
    
    def get_documents(self, project_id: int) -> List[ProjectDocument]:
        """获取项目文档列表（只返回处理成功的文档）"""
        documents = self.db.query(ProjectDocument).filter(
            and_(
                ProjectDocument.project_id == project_id,
                ProjectDocument.deleted_at.is_(None),
                ProjectDocument.processed_at.isnot(None),  # 只返回已处理完成的文档
                ProjectDocument.chunk_count > 0  # 确保有分块内容
            )
        ).order_by(desc(ProjectDocument.uploaded_at)).all()
        
        return documents
    
    def create_document(self, project_id: int, filename: str, source_type: str, 
                       file_path: str = None, file_size_kb: int = None, 
                       upload_user_id: int = None) -> ProjectDocument:
        """创建文档记录"""
        document = ProjectDocument(
            project_id=project_id,
            filename=filename,
            source_type=source_type,
            file_path=file_path,
            file_size_kb=file_size_kb,
            upload_user_id=upload_user_id
        )
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        
        # 注意：doc_count 会在文档处理完成时自动更新（见 DocumentService._mark_document_processed）
        
        logger.info(f"📄 创建文档: project_id={project_id}, filename={filename}")
        return document
    
    def delete_document(self, project_id: int, doc_id: int) -> bool:
        """删除文档（软删除）"""
        document = self.db.query(ProjectDocument).filter(
            and_(
                ProjectDocument.id == doc_id,
                ProjectDocument.project_id == project_id,
                ProjectDocument.deleted_at.is_(None)
            )
        ).first()
        
        if not document:
            return False
        
        document.deleted_at = datetime.utcnow()
        self.db.commit()
        
        # 更新项目文档计数
        self._increment_doc_count(project_id, -1)
        
        logger.info(f"🗑️  删除文档: doc_id={doc_id}")
        return True
    
    # ========== 对话管理 ==========
    
    def get_conversations(self, project_id: int) -> List[ProjectConversation]:
        """获取项目对话列表"""
        conversations = self.db.query(ProjectConversation).filter(
            and_(
                ProjectConversation.project_id == project_id,
                ProjectConversation.deleted_at.is_(None)
            )
        ).order_by(desc(ProjectConversation.updated_at)).all()
        
        return conversations
    
    def get_conversation(self, project_id: int, conversation_id: int) -> Optional[ProjectConversation]:
        """获取对话详情"""
        conversation = self.db.query(ProjectConversation).filter(
            and_(
                ProjectConversation.id == conversation_id,
                ProjectConversation.project_id == project_id,
                ProjectConversation.deleted_at.is_(None)
            )
        ).first()
        
        return conversation
    
    def create_conversation(self, project_id: int, user_id: int, title: str = None) -> ProjectConversation:
        """创建新对话"""
        conversation = ProjectConversation(
            project_id=project_id,
            user_id=user_id,
            title=title or "新对话"
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        
        # 更新项目对话计数
        self._increment_conversation_count(project_id, 1)
        
        logger.info(f"💬 创建对话: project_id={project_id}, conversation_id={conversation.id}")
        return conversation
    
    def add_message(self, conversation_id: int, role: str, content: str, 
                   rag_info: Dict = None) -> ProjectConversationMessage:
        """添加消息"""
        message = ProjectConversationMessage(
            conversation_id=conversation_id,
            role=role,
            content=content
        )
        
        if rag_info:
            message.rag_used = rag_info.get('used', False)
            message.news_used = rag_info.get('news_used', False)
            message.doc_used = rag_info.get('doc_used', False)
            message.doc_ids = rag_info.get('doc_ids')
            message.chunk_ids = rag_info.get('chunk_ids')
            message.search_results_count = rag_info.get('search_results_count', rag_info.get('news_count', 0))
        
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        
        # 更新对话时间
        conversation = self.db.query(ProjectConversation).filter(
            ProjectConversation.id == conversation_id
        ).first()
        if conversation:
            conversation.updated_at = datetime.utcnow()
            
            # 同时更新项目时间
            project = self.db.query(Project).filter(
                Project.id == conversation.project_id
            ).first()
            if project:
                project.updated_at = datetime.utcnow()
            
            self.db.commit()
        
        return message
    
    def get_messages(self, conversation_id: int) -> List[ProjectConversationMessage]:
        """获取对话的所有消息"""
        messages = self.db.query(ProjectConversationMessage).filter(
            ProjectConversationMessage.conversation_id == conversation_id
        ).order_by(ProjectConversationMessage.created_at).all()

        return messages

    def delete_conversation(self, project_id: int, conversation_id: int) -> bool:
        """删除对话及其消息"""
        conversation = self.db.query(ProjectConversation).filter(
            and_(
                ProjectConversation.id == conversation_id,
                ProjectConversation.project_id == project_id,
                ProjectConversation.deleted_at.is_(None),
            )
        ).first()

        if not conversation:
            return False

        # 物理删除该对话下的所有消息
        self.db.query(ProjectConversationMessage).filter(
            ProjectConversationMessage.conversation_id == conversation_id
        ).delete()

        # 删除对话本身
        self.db.delete(conversation)
        self.db.commit()

        # 更新项目对话计数
        self._increment_conversation_count(project_id, -1)

        logger.info(f"🗑️  删除对话: project_id={project_id}, conversation_id={conversation_id}")
        return True

    def get_chunk_detail(self, project_id: int, chunk_id: int) -> Optional[Dict]:
        """获取项目内指定 chunk 的详细信息"""
        row = self.db.execute(
            text(
                """
                SELECT
                    c.id AS chunk_id,
                    c.document_id,
                    c.chunk_index,
                    c.text_content,
                    d.filename,
                    d.project_id
                FROM project_document_chunks c
                JOIN project_documents d ON d.id = c.document_id
                WHERE c.id = :chunk_id
                  AND d.project_id = :project_id
                  AND d.deleted_at IS NULL
                LIMIT 1
                """
            ),
            {"chunk_id": chunk_id, "project_id": project_id},
        ).mappings().first()

        if not row:
            return None

        return {
            "chunk_id": int(row["chunk_id"]),
            "document_id": int(row["document_id"]),
            "chunk_index": int(row["chunk_index"]),
            "filename": row["filename"],
            "text": row["text_content"],
        }
    
    # ========== 项目长期记忆 ==========
    
    def get_recent_memories(
        self,
        project_id: int,
        limit: int = 20,
        memory_types: Optional[List[str]] = None,
    ) -> List[ProjectMemory]:
        """获取项目的近期长期记忆，用于作为高层结论/摘要的辅助证据。"""
        query = self.db.query(ProjectMemory).filter(ProjectMemory.project_id == project_id)
        
        if memory_types:
            query = query.filter(ProjectMemory.memory_type.in_(memory_types))
        
        memories = (
            query.order_by(desc(ProjectMemory.updated_at)).limit(limit).all()
        )
        return memories
    
    # ========== 内部辅助方法 ==========
    
    def _increment_doc_count(self, project_id: int, delta: int = 1):
        """更新文档计数（重新计算以确保准确性）"""
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if project:
            # 重新计算实际完成的文档数，而不是简单增量
            actual_count = self.db.query(ProjectDocument).filter(
                and_(
                    ProjectDocument.project_id == project_id,
                    ProjectDocument.deleted_at.is_(None),
                    ProjectDocument.processed_at.isnot(None),
                    ProjectDocument.chunk_count > 0
                )
            ).count()
            
            project.doc_count = actual_count
            project.updated_at = datetime.utcnow()
            self.db.commit()
    
    def _increment_conversation_count(self, project_id: int, delta: int = 1):
        """增加对话计数"""
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.conversation_count = max(0, (project.conversation_count or 0) + delta)
            project.updated_at = datetime.utcnow()
            self.db.commit()
