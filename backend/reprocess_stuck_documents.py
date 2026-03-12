"""重新处理卡住的文档"""
import asyncio
from database import SessionLocal
from models.project import ProjectDocument
from services.document_service import DocumentService

async def reprocess_stuck_documents(project_id: int):
    """重新处理所有处理中但未完成的文档"""
    db = SessionLocal()
    doc_service = DocumentService()
    
    try:
        # 查找所有 processed_at 为 None 的文档
        stuck_docs = db.query(ProjectDocument).filter(
            ProjectDocument.project_id == project_id,
            ProjectDocument.processed_at.is_(None)
        ).all()
        
        print(f"找到 {len(stuck_docs)} 个待处理文档")
        
        for doc in stuck_docs:
            print(f"\n开始处理文档 #{doc.id}: {doc.filename}")
            try:
                await doc_service.process_uploaded_file(
                    doc_id=doc.id,
                    project_id=doc.project_id,
                    filename=doc.filename,
                    file_content=open(doc.file_path, 'rb').read()
                )
                print(f"✅ 文档 #{doc.id} 处理成功")
            except Exception as e:
                print(f"❌ 文档 #{doc.id} 处理失败: {str(e)}")
                import traceback
                traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    # 处理项目 1 的卡住文档
    asyncio.run(reprocess_stuck_documents(project_id=1))
