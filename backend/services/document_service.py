"""文档处理服务 - 文件解析、分块、向量化"""

import os
import json
import re
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
from loguru import logger
import httpx

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb
from chromadb.config import Settings

from config import get_config
from database import engine
from sqlalchemy import text, bindparam

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None


class DocumentService:
    """文档处理服务 - 负责文档解析、分块、向量化"""
    
    def __init__(self):
        self.config = get_config()
        self.upload_dir = Path(self.config.app.upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_dir = Path(self.config.app.chroma_path)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        self.chunk_size = 800  # 每个 chunk 大约 800 字符
        self.chunk_overlap = 200  # chunk 之间重叠 200 字符
        self.embedding_model = "text-embedding-v4"
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.chroma_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        self.chroma_collection = self.chroma_client.get_or_create_collection(
            name="project_document_chunks",
            metadata={"hnsw:space": "cosine"},
        )
        
    async def process_uploaded_file(
        self, 
        project_id: int, 
        doc_id: int,
        file_content: bytes,
        filename: str
    ) -> Dict:
        """处理上传的文件：保存、解析、分块、向量化"""
        try:
            # 1. 保存文件并更新文档路径
            file_path = await self._save_file(project_id, doc_id, file_content, filename)
            logger.info(f"[DocService] 文件已保存: {file_path}")
            
            # 更新数据库中的 file_path
            await self._update_file_path(doc_id, str(file_path))
            
            # 2. 解析文本
            text_content = await self._extract_text(file_path, filename)
            if not text_content or len(text_content.strip()) < 10:
                logger.warning(f"[DocService] 文件解析失败或内容为空: {filename}")
                return {"success": False, "error": "文件内容为空或解析失败"}
            
            logger.info(f"[DocService] 文本已解析，长度: {len(text_content)} 字符")
            
            # 3. 分块
            chunks = self._split_into_chunks(text_content)
            logger.info(f"[DocService] 分块完成: {len(chunks)} 个 chunks")
            
            # 4. 向量化并保存
            success_count = 0
            for idx, chunk_text in enumerate(chunks):
                embedding = await self._embed_text(chunk_text)
                success = await self._save_chunk(
                    project_id=project_id,
                    doc_id=doc_id,
                    chunk_index=idx,
                    filename=filename,
                    text_content=chunk_text,
                    embedding=embedding,
                    token_count=len(chunk_text) // 4  # 粗略估算
                )
                if success:
                    success_count += 1
            
            # 5. 更新文档状态
            await self._mark_document_processed(doc_id, len(chunks), project_id)
            
            logger.info(f"[DocService] 文档处理完成: doc_id={doc_id}, chunks={success_count}/{len(chunks)}")
            
            return {
                "success": True,
                "chunk_count": success_count,
                "total_chars": len(text_content)
            }
            
        except Exception as e:
            logger.error(f"[DocService] 文档处理失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def _save_file(
        self, 
        project_id: int, 
        doc_id: int, 
        content: bytes,
        filename: str
    ) -> Path:
        """保存文件到本地存储"""
        project_dir = self.upload_dir / f"project_{project_id}"
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # 使用 doc_id 确保文件名唯一
        ext = Path(filename).suffix
        safe_filename = f"doc_{doc_id}{ext}"
        file_path = project_dir / safe_filename
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        return file_path
    
    async def _extract_text(self, file_path: Path, filename: str) -> str:
        """从文件中提取文本"""
        ext = file_path.suffix.lower()
        
        try:
            if ext == '.txt':
                return self._extract_text_from_txt(file_path)
            elif ext == '.pdf':
                return self._extract_text_from_pdf(file_path)
            elif ext in ['.docx', '.doc']:
                return self._extract_text_from_docx(file_path)
            else:
                logger.warning(f"[DocService] 不支持的文件类型: {ext}")
                return ""
        except Exception as e:
            logger.error(f"[DocService] 文本提取失败 {filename}: {e}")
            return ""
    
    def _extract_text_from_txt(self, file_path: Path) -> str:
        """从 TXT 文件提取文本"""
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin1']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        return ""
    
    def _extract_text_from_pdf(self, file_path: Path) -> str:
        """从 PDF 文件提取文本"""
        if not PyPDF2:
            logger.warning("[DocService] PyPDF2 未安装，无法解析 PDF")
            return ""
        
        try:
            text_parts = []
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error(f"[DocService] PDF 解析失败: {e}")
            return ""
    
    def _extract_text_from_docx(self, file_path: Path) -> str:
        """从 DOCX 文件提取文本"""
        if not DocxDocument:
            logger.warning("[DocService] python-docx 未安装，无法解析 DOCX")
            return ""
        
        try:
            doc = DocxDocument(file_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n\n".join(paragraphs)
        except Exception as e:
            logger.error(f"[DocService] DOCX 解析失败: {e}")
            return ""
    
    def _split_into_chunks(self, text: str) -> List[str]:
        """将文本分块"""
        # 清理文本
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # 如果不是最后一块，尝试在句子边界处分割
            if end < len(text):
                # 寻找句号、问号、感叹号等
                for sep in ['。', '！', '？', '.', '!', '?', '\n\n', '\n']:
                    pos = text.rfind(sep, start, end)
                    if pos > start + self.chunk_size // 2:  # 至少要有一半长度
                        end = pos + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # 下一个块从重叠位置开始
            start = end - self.chunk_overlap if end < len(text) else end
        
        return chunks
    
    async def _embed_text(self, text: str) -> Optional[List[float]]:
        """生成文本向量"""
        if not text or len(text.strip()) < 3:
            return None
        
        api_key = self.config.llm.api_key
        base_url = (self.config.llm.base_url or "").rstrip("/")
        
        if not api_key or not base_url:
            logger.warning("[DocService] LLM_API_KEY 或 BASE_URL 未配置")
            return None
        
        url = f"{base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.embedding_model,
            "input": text[:2000],  # 限制长度
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                emb = data.get("data", [{}])[0].get("embedding")
                if isinstance(emb, list) and emb:
                    return [float(x) for x in emb]
                return None
        except Exception as e:
            logger.warning(f"[DocService] 向量化失败: {e}")
            return None
    
    async def _save_chunk(
        self,
        project_id: int,
        doc_id: int,
        chunk_index: int,
        filename: str,
        text_content: str,
        embedding: Optional[List[float]],
        token_count: int
    ) -> bool:
        """保存文档块到数据库，并写入 Chroma 向量库"""
        try:
            with engine.begin() as conn:
                result = conn.execute(
                    text("""
                        INSERT INTO project_document_chunks 
                        (document_id, chunk_index, text_content, embedding_json, token_count, created_at)
                        VALUES (:document_id, :chunk_index, :text_content, :embedding_json, :token_count, NOW())
                        RETURNING id
                    """),
                    {
                        "document_id": doc_id,
                        "chunk_index": chunk_index,
                        "text_content": text_content[:5000],  # 限制长度
                        "embedding_json": json.dumps(embedding) if embedding else None,
                        "token_count": token_count,
                    }
                )
                row = result.first()

            if row and embedding:
                chunk_id = int(row[0])
                self.chroma_collection.upsert(
                    ids=[str(chunk_id)],
                    embeddings=[embedding],
                    documents=[text_content[:5000]],
                    metadatas=[
                        {
                            "project_id": int(project_id),
                            "document_id": int(doc_id),
                            "chunk_id": chunk_id,
                            "chunk_index": int(chunk_index),
                            "filename": str(filename or ""),
                        }
                    ],
                )

            return True
        except Exception as e:
            logger.error(f"[DocService] 保存 chunk 失败: {e}")
            return False
    
    async def _update_file_path(self, doc_id: int, file_path: str) -> None:
        """更新文档的文件路径"""
        try:
            with engine.begin() as conn:
                conn.execute(
                    text("""
                        UPDATE project_documents 
                        SET file_path = :file_path
                        WHERE id = :doc_id
                    """),
                    {"doc_id": doc_id, "file_path": file_path}
                )
        except Exception as e:
            logger.error(f"[DocService] 更新文件路径失败: {e}")
    
    async def _mark_document_processed(self, doc_id: int, chunk_count: int, project_id: int = None) -> None:
        """标记文档处理完成并更新项目文档计数"""
        try:
            with engine.begin() as conn:
                # 更新文档状态
                conn.execute(
                    text("""
                        UPDATE project_documents 
                        SET processed_at = NOW(), chunk_count = :chunk_count
                        WHERE id = :doc_id
                    """),
                    {"doc_id": doc_id, "chunk_count": chunk_count}
                )
                
                # 重新计算项目的实际文档数（只计数已完成的）
                if project_id:
                    actual_count = conn.execute(
                        text("""
                            SELECT COUNT(*) FROM project_documents
                            WHERE project_id = :project_id
                              AND deleted_at IS NULL
                              AND processed_at IS NOT NULL
                              AND chunk_count > 0
                        """),
                        {"project_id": project_id}
                    ).scalar()
                    
                    # 更新项目的文档计数
                    conn.execute(
                        text("""
                            UPDATE projects 
                            SET doc_count = :doc_count, updated_at = NOW()
                            WHERE id = :project_id
                        """),
                        {"project_id": project_id, "doc_count": actual_count}
                    )
                    
        except Exception as e:
            logger.error(f"[DocService] 更新文档状态失败: {e}")
    
    async def search_similar_chunks(
        self,
        project_id: int,
        query: str,
        top_k: int = 5
    ) -> List[Dict]:
        """检索与查询相似的文档片段"""
        # 生成查询向量
        query_emb = await self._embed_text(query)
        
        try:
            # 优先使用 Chroma 向量检索（持久化向量数据库）
            if query_emb:
                chroma_rows = self._search_with_chroma(project_id=project_id, query_emb=query_emb, top_k=top_k)
                if chroma_rows:
                    return chroma_rows

                logger.info("[DocService] Chroma 检索无命中，回退到 JSON/关键词检索")

            with engine.begin() as conn:
                # 获取该项目的所有文档块
                rows = conn.execute(
                    text("""
                        SELECT 
                            c.id, c.document_id, c.chunk_index, c.text_content, 
                            c.embedding_json, d.filename, d.authority_score
                        FROM project_document_chunks c
                        JOIN project_documents d ON c.document_id = d.id
                        WHERE d.project_id = :project_id 
                          AND d.deleted_at IS NULL
                          AND d.processed_at IS NOT NULL
                        ORDER BY d.authority_score DESC, c.chunk_index ASC
                        LIMIT 200
                    """),
                    {"project_id": project_id}
                ).mappings().all()
            
            if not rows:
                return []
            
            # 计算相似度
            scored = []
            for row in rows:
                score = 0.0
                if query_emb and row.get("embedding_json"):
                    try:
                        chunk_emb = json.loads(row["embedding_json"])
                        score = self._cosine_similarity(query_emb, chunk_emb)
                    except Exception:
                        score = 0.0
                else:
                    # 关键词匹配作为备选
                    if query.lower() in row["text_content"].lower():
                        score = 0.7
                
                # 加入权威度加权
                authority_bonus = float(row.get("authority_score", 0.7)) * 0.15
                final_score = score + authority_bonus
                
                if final_score > 0.5:  # 阈值过滤
                    scored.append((
                        final_score,
                        {
                            "chunk_id": row["id"],
                            "document_id": row["document_id"],
                            "filename": row["filename"],
                            "text": row["text_content"],
                            "score": round(final_score, 4)
                        }
                    ))
            
            # 排序并返回 top_k
            scored.sort(key=lambda x: x[0], reverse=True)
            return [item[1] for item in scored[:top_k]]
            
        except Exception as e:
            logger.error(f"[DocService] 检索失败: {e}")
            return []

    def _search_with_chroma(self, project_id: int, query_emb: List[float], top_k: int) -> List[Dict]:
        """通过 Chroma 检索候选，再到 SQL 过滤有效文档并做权威度加权。"""
        try:
            n_results = max(top_k * 6, 40)
            result = self.chroma_collection.query(
                query_embeddings=[query_emb],
                where={"project_id": int(project_id)},
                n_results=n_results,
                include=["metadatas", "distances"],
            )

            metadatas = (result.get("metadatas") or [[]])[0]
            distances = (result.get("distances") or [[]])[0]
            if not metadatas:
                return []

            similarity_map: Dict[int, float] = {}
            candidate_ids: List[int] = []
            for meta, distance in zip(metadatas, distances):
                chunk_id = int(meta.get("chunk_id") or 0)
                if chunk_id <= 0:
                    continue
                dist = float(distance or 1.0)
                similarity_map[chunk_id] = max(0.0, 1.0 - dist)
                candidate_ids.append(chunk_id)

            if not candidate_ids:
                return []

            sql = text(
                """
                SELECT
                    c.id,
                    c.document_id,
                    c.chunk_index,
                    c.text_content,
                    d.filename,
                    d.authority_score
                FROM project_document_chunks c
                JOIN project_documents d ON c.document_id = d.id
                WHERE d.project_id = :project_id
                  AND d.deleted_at IS NULL
                  AND d.processed_at IS NOT NULL
                  AND c.id IN :chunk_ids
                """
            ).bindparams(bindparam("chunk_ids", expanding=True))

            with engine.begin() as conn:
                rows = conn.execute(
                    sql,
                    {"project_id": project_id, "chunk_ids": candidate_ids},
                ).mappings().all()

            scored = []
            for row in rows:
                similarity = float(similarity_map.get(int(row["id"]), 0.0))
                authority_bonus = float(row.get("authority_score", 0.7)) * 0.15
                final_score = similarity + authority_bonus
                if final_score > 0.5:
                    scored.append(
                        {
                            "chunk_id": row["id"],
                            "document_id": row["document_id"],
                            "filename": row["filename"],
                            "text": row["text_content"],
                            "score": round(final_score, 4),
                        }
                    )

            scored.sort(key=lambda x: x["score"], reverse=True)
            return scored[:top_k]
        except Exception as e:
            logger.warning(f"[DocService] Chroma 检索失败，回退 SQL 检索: {e}")
            return []

    def delete_document_vectors(self, doc_id: int) -> None:
        """删除 Chroma 中指定文档的向量索引。"""
        try:
            self.chroma_collection.delete(where={"document_id": int(doc_id)})
        except Exception as e:
            logger.warning(f"[DocService] 删除 Chroma 文档向量失败 doc_id={doc_id}: {e}")
    
    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot / (norm1 * norm2)
