"""文档处理服务 - 文件解析、分块、向量化"""

import os
import json
import re
import logging
import shutil
import base64
import mimetypes
from statistics import median
from pathlib import Path
from typing import List, Optional, Dict, Tuple, Any
from datetime import datetime
from loguru import logger
import httpx

# 关闭 Chroma telemetry，并抑制 telemetry 组件的 ERROR 噪音日志。
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("CHROMA_TELEMETRY_DISABLED", "1")
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)
logging.getLogger("posthog").setLevel(logging.CRITICAL)

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
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

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
        self.chunk_size = 800  # 基础分块大小（会结合标题级别动态调整）
        self.chunk_overlap = 200  # chunk 之间重叠 200 字符
        self.embedding_model = (self.config.llm.embedding_model_id or "").strip()
        self.image_caption_model = (self.config.llm.image_caption_model_id or "").strip()
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.chroma_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        self.chroma_collection = self.chroma_client.get_or_create_collection(
            name="project_document_chunks",
            metadata={"hnsw:space": "cosine"},
        )

    @staticmethod
    def _sanitize_text(text: str) -> str:
        """移除数据库不接受的控制字符（重点是 NUL）。"""
        if not text:
            return ""
        return text.replace("\x00", "")
        
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

            # 1.5 提取并保存图片元数据（多模态）
            image_assets: List[Dict[str, Any]] = []
            if file_path.suffix.lower() == ".pdf":
                image_assets = await self._extract_and_save_pdf_images(project_id, doc_id, file_path)
                logger.info(f"[DocService] 图片提取完成: {len(image_assets)} 张")
            
            # 2. 解析文本
            text_content = await self._extract_text(file_path, filename, image_assets=image_assets)

            image_caption_count = 0
            image_table_count = 0
            if file_path.suffix.lower() == ".pdf" and image_assets:
                text_content, image_caption_count, image_table_count = await self._materialize_image_placeholders_in_text(
                    text_content,
                    image_assets,
                )

            text_content = self._sanitize_text(text_content)
            has_text = bool(text_content and len(text_content.strip()) >= 10)
            if has_text:
                logger.info(f"[DocService] 文本已解析，长度: {len(text_content)} 字符")
            else:
                logger.warning(f"[DocService] 文本较少或为空，将仅使用图片描述: {filename}")
            
            # 3. 分块
            chunks = self._split_into_chunks(text_content) if has_text else []
            logger.info(f"[DocService] 分块完成: {len(chunks)} 个 chunks")
            
            # 4. 向量化并保存文本 chunks
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

            if success_count == 0:
                return {"success": False, "error": "文档文本与图片描述均未成功入库"}
            
            # 5. 更新文档状态
            await self._mark_document_processed(doc_id, success_count, project_id)
            
            logger.info(
                f"[DocService] 文档处理完成: doc_id={doc_id}, text_chunks={len(chunks)}, "
                f"inline_image_captions={image_caption_count}, inline_image_tables={image_table_count}, saved={success_count}"
            )
            
            return {
                "success": True,
                "chunk_count": success_count,
                "total_chars": len(text_content),
                "image_count": len(image_assets),
                "inline_image_captions": image_caption_count,
                "inline_image_tables": image_table_count,
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
    
    async def _extract_text(self, file_path: Path, filename: str, image_assets: Optional[List[Dict[str, Any]]] = None) -> str:
        """从文件中提取文本"""
        ext = file_path.suffix.lower()
        
        try:
            if ext == '.txt':
                return self._extract_text_from_txt(file_path)
            elif ext == '.pdf':
                return self._extract_text_from_pdf(file_path, image_assets=image_assets)
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
    
    def _extract_text_from_pdf(self, file_path: Path, image_assets: Optional[List[Dict[str, Any]]] = None) -> str:
        """从 PDF 文件提取文本（优先布局/字体增强解析，失败则回退 PyPDF2）。"""
        if fitz is not None:
            try:
                return self._extract_text_from_pdf_with_layout(file_path, image_assets=image_assets)
            except Exception as exc:
                logger.warning(f"[DocService] PyMuPDF 布局解析失败，回退 PyPDF2: {exc}")

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

    def _extract_text_from_pdf_with_layout(self, file_path: Path, image_assets: Optional[List[Dict[str, Any]]] = None) -> str:
        """使用 PyMuPDF 提取文本并结合字体大小/居中布局识别标题层级。"""
        doc = fitz.open(file_path)
        collected_items: List[Dict[str, Any]] = []
        image_assets = image_assets or []
        images_by_page: Dict[int, List[Dict[str, Any]]] = {}
        for asset in image_assets:
            page_no = int(asset.get("page_number") or 0)
            if page_no <= 0:
                continue
            images_by_page.setdefault(page_no, []).append(asset)

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_number = page_idx + 1
            page_width = float(page.rect.width or 1.0)
            page_tables = self._extract_tables_from_pdf_page(page, page_number)
            text_dict = page.get_text("dict") or {}
            blocks = text_dict.get("blocks") or []

            for img_asset in images_by_page.get(page_number, []):
                placeholder = self._build_image_placeholder(img_asset)
                collected_items.append(
                    {
                        "kind": "image",
                        "text": placeholder,
                        "y0": float(img_asset.get("y0") or 0.0),
                        "font_size": 0.0,
                        "centered": False,
                        "page": page_number,
                    }
                )

            for table in page_tables:
                collected_items.append(
                    {
                        "kind": "table",
                        "text": table["text"],
                        "y0": table["y0"],
                        "font_size": 0.0,
                        "centered": False,
                        "page": page_number,
                    }
                )

            for block in blocks:
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    span_texts: List[str] = []
                    span_sizes: List[float] = []
                    x0_vals: List[float] = []
                    x1_vals: List[float] = []
                    y0_vals: List[float] = []
                    y1_vals: List[float] = []

                    for span in line.get("spans", []):
                        text = self._sanitize_text(str(span.get("text") or "")).strip()
                        if not text:
                            continue
                        span_texts.append(text)
                        span_sizes.append(float(span.get("size") or 0.0))
                        bbox = span.get("bbox") or [0.0, 0.0, 0.0, 0.0]
                        x0_vals.append(float(bbox[0]))
                        x1_vals.append(float(bbox[2]))
                        y0_vals.append(float(bbox[1]))
                        y1_vals.append(float(bbox[3]))

                    merged_text = " ".join(span_texts).strip()
                    if not merged_text:
                        continue

                    line_bbox = (
                        min(x0_vals) if x0_vals else 0.0,
                        min(y0_vals) if y0_vals else 0.0,
                        max(x1_vals) if x1_vals else 0.0,
                        max(y1_vals) if y1_vals else 0.0,
                    )
                    if self._bbox_overlaps_any_table(line_bbox, page_tables):
                        continue

                    left = min(x0_vals) if x0_vals else 0.0
                    right = max(x1_vals) if x1_vals else 0.0
                    line_width = max(0.0, right - left)
                    line_center = left + line_width / 2.0
                    centered = (
                        abs(line_center - page_width / 2.0) <= page_width * 0.08
                        and line_width <= page_width * 0.78
                    )

                    collected_items.append(
                        {
                            "kind": "line",
                            "text": merged_text,
                            "font_size": max(span_sizes) if span_sizes else 0.0,
                            "centered": centered,
                            "y0": line_bbox[1],
                            "page": page_number,
                        }
                    )

        doc.close()

        if not collected_items:
            return ""

        collected_items.sort(key=lambda x: (int(x.get("page") or 0), float(x.get("y0") or 0.0), str(x.get("kind") or "")))

        font_sizes = [x["font_size"] for x in collected_items if x.get("kind") == "line" and x["font_size"] > 0]
        body_size = float(median(font_sizes)) if font_sizes else 12.0

        output_lines: List[str] = []
        heading_count = 0
        table_count = 0
        for item in collected_items:
            text_line = str(item.get("text") or "").strip()
            if not text_line:
                continue
            if item.get("kind") == "table":
                table_count += 1
                output_lines.append(text_line)
                continue
            level = self._infer_pdf_heading_level(
                text=text_line,
                font_size=float(item.get("font_size") or 0.0),
                body_size=body_size,
                centered=bool(item.get("centered")),
            )
            if level > 0:
                heading_count += 1
                output_lines.append(f"{'#' * level} {text_line}")
            else:
                output_lines.append(text_line)

        logger.info(
            f"[DocService] PDF布局解析完成: lines={len(output_lines)}, tables={table_count}, inferred_headings={heading_count}, body_size={body_size:.2f}"
        )
        return "\n".join(output_lines)

    def _extract_tables_from_pdf_page(self, page: Any, page_number: int) -> List[Dict[str, Any]]:
        """从单页 PDF 中提取表格，并转成 Markdown 文本。"""
        if not hasattr(page, "find_tables"):
            return []

        try:
            finder = page.find_tables()
            tables = getattr(finder, "tables", None) or []
        except Exception as exc:
            logger.debug(f"[DocService] PDF表格检测失败 page={page_number}: {exc}")
            return []

        extracted: List[Dict[str, Any]] = []
        for idx, table in enumerate(tables, start=1):
            try:
                rows = table.extract() or []
                markdown = self._table_rows_to_markdown(rows, page_number, idx)
                if not markdown:
                    continue
                bbox = getattr(table, "bbox", None) or (0.0, 0.0, 0.0, 0.0)
                extracted.append(
                    {
                        "text": markdown,
                        "bbox": tuple(float(x) for x in bbox),
                        "y0": float(bbox[1]) if len(bbox) > 1 else 0.0,
                    }
                )
            except Exception as exc:
                logger.debug(f"[DocService] PDF表格抽取失败 page={page_number} idx={idx}: {exc}")
        return extracted

    def _table_rows_to_markdown(self, rows: List[List[Any]], page_number: int, table_index: int) -> str:
        """将表格行数据转成 Markdown，保留表头和单元格结构。"""
        normalized_rows: List[List[str]] = []
        max_cols = 0

        for row in rows:
            if not isinstance(row, list):
                continue
            cells = [self._sanitize_text(str(cell or "")).replace("\n", " ").strip() for cell in row]
            if not any(cells):
                continue
            max_cols = max(max_cols, len(cells))
            normalized_rows.append(cells)

        if not normalized_rows or max_cols == 0:
            return ""

        padded_rows: List[List[str]] = []
        for row in normalized_rows:
            padded = row + [""] * (max_cols - len(row))
            padded_rows.append([cell if cell else "-" for cell in padded])

        header = padded_rows[0]
        body = padded_rows[1:] if len(padded_rows) > 1 else []
        lines = [f"[TABLE] page={page_number} table={table_index}"]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join(["---"] * max_cols) + " |")
        for row in body:
            lines.append("| " + " | ".join(row) + " |")
        return "\n".join(lines)

    @staticmethod
    def _bbox_overlaps_any_table(line_bbox: Tuple[float, float, float, float], tables: List[Dict[str, Any]]) -> bool:
        """判断文本行是否落在已识别表格区域，避免文本/表格重复。"""
        lx0, ly0, lx1, ly1 = line_bbox
        for table in tables:
            tbbox = table.get("bbox") or (0.0, 0.0, 0.0, 0.0)
            tx0, ty0, tx1, ty1 = tbbox
            horizontal_overlap = min(lx1, tx1) - max(lx0, tx0)
            vertical_overlap = min(ly1, ty1) - max(ly0, ty0)
            if horizontal_overlap > 0 and vertical_overlap > 0:
                return True
        return False

    def _infer_pdf_heading_level(self, text: str, font_size: float, body_size: float, centered: bool) -> int:
        """基于字体大小与居中布局推断标题层级。"""
        text_line = (text or "").strip()
        if len(text_line) < 2 or len(text_line) > 100:
            return 0

        # 若本身匹配已有标题规则，优先使用已有规则。
        existing = self._detect_heading(text_line)
        if existing:
            return max(1, min(3, int(existing[0])))

        safe_body = max(body_size, 1.0)
        ratio = float(font_size or 0.0) / safe_body

        # 字体显著更大，直接视为高层标题。
        if ratio >= 1.45:
            return 1
        # 居中且明显放大，常见章节标题样式。
        if centered and ratio >= 1.20:
            return 1
        # 次级标题。
        if ratio >= 1.25:
            return 2
        if centered and ratio >= 1.08 and len(text_line) <= 40:
            return 2
        # 三级标题（略大于正文）。
        if ratio >= 1.12 and len(text_line) <= 55:
            return 3
        return 0
    
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
    
    def _normalize_text_for_chunking(self, text: str) -> str:
        """标准化文本，尽量保留结构信息（换行/段落）。"""
        if not text:
            return ""

        normalized = self._sanitize_text(text).replace("\r\n", "\n").replace("\r", "\n")
        lines = [re.sub(r"[\t\f\v ]+", " ", line).strip() for line in normalized.split("\n")]

        compact_lines = []
        blank_count = 0
        for line in lines:
            if not line:
                blank_count += 1
                if blank_count <= 1:
                    compact_lines.append("")
            else:
                blank_count = 0
                compact_lines.append(line)

        return "\n".join(compact_lines).strip()

    def _detect_heading(self, line: str) -> Optional[Tuple[int, str]]:
        """识别标题并返回 (level, heading_text)。"""
        if not line:
            return None

        text_line = line.strip()
        if len(text_line) < 2 or len(text_line) > 120:
            return None

        # Markdown 标题: # / ## / ###
        m = re.match(r"^(#{1,6})\s+(.+)$", text_line)
        if m:
            return len(m.group(1)), m.group(2).strip()

        # 中文章/节标题: 第1章 / 第一章 / 第三节
        m = re.match(r"^第[一二三四五六七八九十百千\d]+[章节部分篇]\s*(.+)?$", text_line)
        if m:
            return 1, text_line

        # 中文序号标题: 一、xx
        m = re.match(r"^[一二三四五六七八九十]+[、.．]\s+(.+)$", text_line)
        if m:
            return 1, text_line

        # 圆括号序号标题: (一) xx / （1）xx
        m = re.match(r"^[（(][一二三四五六七八九十\d]+[)）]\s+(.+)$", text_line)
        if m:
            return 2, text_line

        # 阿拉伯数字层级标题: 1. / 1.2 / 1.2.3
        m = re.match(r"^(\d+(?:\.\d+){0,3})[)）.、\-:\s]+(.+)$", text_line)
        if m:
            depth = m.group(1).count(".") + 1
            return min(depth, 4), text_line

        return None

    def _split_into_sections(self, text: str) -> List[Dict]:
        """按标题层级拆成 section。"""
        sections: List[Dict] = []
        current = {"heading": "", "level": 0, "lines": []}

        for raw_line in text.split("\n"):
            heading = self._detect_heading(raw_line)
            if heading:
                if current["heading"] or current["lines"]:
                    sections.append(
                        {
                            "heading": current["heading"],
                            "level": current["level"],
                            "content": "\n".join(current["lines"]).strip(),
                        }
                    )
                level, heading_text = heading
                current = {"heading": heading_text, "level": level, "lines": []}
            else:
                current["lines"].append(raw_line)

        if current["heading"] or current["lines"]:
            sections.append(
                {
                    "heading": current["heading"],
                    "level": current["level"],
                    "content": "\n".join(current["lines"]).strip(),
                }
            )

        return sections

    def _get_dynamic_chunk_size(self, heading_level: int, section_len: int) -> int:
        """根据标题级别和 section 长度动态调整 chunk 大小。"""
        base = self.chunk_size

        if heading_level <= 1:
            target = int(base * 0.9)  # 一级标题更细粒度
        elif heading_level == 2:
            target = base
        elif heading_level >= 3:
            target = int(base * 1.1)  # 深层小节可稍大，减少碎片化
        else:
            target = base

        if section_len > base * 4 and heading_level <= 2:
            target = int(target * 0.9)

        return max(400, min(1400, target))

    def _split_text_windowed(self, text: str, target_size: int, overlap: int) -> List[str]:
        """窗口切分：优先段落/句子边界，保留 overlap。"""
        text = text.strip()
        if not text:
            return []
        if len(text) <= target_size:
            return [text]

        chunks: List[str] = []
        start = 0
        n = len(text)

        while start < n:
            end = min(start + target_size, n)

            if end < n:
                best_cut = -1
                # 优先在更自然的边界切分
                for sep in ["\n\n", "\n", "。", "！", "？", ". ", "! ", "? ", "；", ";", "，", ","]:
                    pos = text.rfind(sep, start + target_size // 2, end)
                    if pos > best_cut:
                        best_cut = pos + len(sep)
                if best_cut > start + target_size // 2:
                    end = best_cut

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            if end >= n:
                break

            next_start = max(end - overlap, start + 1)
            start = next_start if next_start > start else end

        return chunks

    def _split_into_chunks(self, text: str) -> List[str]:
        """高级分块：标题感知 + 动态长度 + 重叠窗口。"""
        normalized = self._normalize_text_for_chunking(text)
        if not normalized:
            return []

        sections = self._split_into_sections(normalized)
        chunks: List[str] = []

        for section in sections:
            heading = section.get("heading", "").strip()
            level = int(section.get("level", 0) or 0)
            content = section.get("content", "").strip()

            # 纯标题也保留，避免目录信息丢失
            if heading and not content:
                chunks.append(f"[H{level}] {heading}")
                continue

            section_text = content if content else heading
            if not section_text:
                continue

            target_size = self._get_dynamic_chunk_size(level, len(section_text))
            split_parts = self._split_text_windowed(section_text, target_size, self.chunk_overlap)

            for idx, part in enumerate(split_parts):
                if heading:
                    title_prefix = f"[H{level}] {heading}"
                    chunk = f"{title_prefix}\n{part}" if idx == 0 else f"{title_prefix}（续）\n{part}"
                else:
                    chunk = part

                if len(chunk.strip()) >= 20:
                    chunks.append(chunk.strip())

        if not chunks:
            fallback = normalized[: self.chunk_size].strip()
            return [fallback] if fallback else []

        return chunks
    
    async def _embed_text(self, text: str) -> Optional[List[float]]:
        """生成文本向量"""
        text = self._sanitize_text(text)
        if not text or len(text.strip()) < 3:
            return None
        
        api_key = self.config.llm.effective_api_key
        base_url = (self.config.llm.base_url or "").rstrip("/")
        
        if not api_key or not base_url:
            logger.warning("[DocService] LLM_API_KEY 或 BASE_URL 未配置")
            return None

        if not self.embedding_model:
            logger.warning("[DocService] EMBEDDING_MODEL_ID 未配置")
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
            clean_text = self._sanitize_text(text_content)[:5000]
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
                        "text_content": clean_text,
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
                    documents=[clean_text],
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

    def _image_ext_from_bytes(self, image_data: bytes) -> str:
        """根据图片头判断扩展名。"""
        if not image_data or len(image_data) < 12:
            return "bin"
        if image_data.startswith(b"\xff\xd8\xff"):
            return "jpg"
        if image_data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "png"
        if image_data.startswith((b"GIF87a", b"GIF89a")):
            return "gif"
        if image_data.startswith(b"BM"):
            return "bmp"
        if image_data.startswith((b"II*\x00", b"MM\x00*")):
            return "tiff"
        if image_data[4:8] == b"jP  ":
            return "jp2"
        return "bin"

    async def _extract_and_save_pdf_images(self, project_id: int, doc_id: int, file_path: Path) -> List[Dict[str, Any]]:
        """从 PDF 提取图片并保存到文件系统 + 数据库（仅使用 PyMuPDF 主链路）。"""
        images_dir = self.upload_dir / f"project_{project_id}" / "images" / f"doc_{doc_id}"
        images_dir.mkdir(parents=True, exist_ok=True)

        image_assets: List[Dict[str, Any]] = []

        if fitz is None:
            logger.warning("[DocService] 未安装 PyMuPDF，无法执行图片抽取主链路")
            return image_assets

        try:
            doc = fitz.open(file_path)
        except Exception as exc:
            logger.warning(f"[DocService] 打开PDF失败，无法抽图: {exc}")
            return image_assets

        try:
            extracted_count = 0
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                img_list = page.get_images(full=True) or []
                page_image_index = 0

                for img_info in img_list:
                    try:
                        xref = img_info[0]
                        img = doc.extract_image(xref)
                        img_bytes = img.get("image")
                        if not img_bytes:
                            continue
                        ext = (img.get("ext") or self._image_ext_from_bytes(img_bytes)).lower()
                        rects = page.get_image_rects(xref) or []
                        y0 = float(rects[0].y0) if rects else float(page.rect.height + page_image_index)
                        page_image_index += 1
                        # 百炼对 image/jpx 兼容性较弱，统一转成 png 以提高多模态调用成功率。
                        if ext in {"jpx", "jp2"}:
                            pix = fitz.Pixmap(doc, xref)
                            if pix.n - pix.alpha > 3:
                                pix = fitz.Pixmap(fitz.csRGB, pix)
                            ext = "png"
                            filename = f"p{page_idx + 1}_img{page_image_index}.{ext}"
                            out_path = images_dir / filename
                            pix.save(str(out_path))
                        else:
                            filename = f"p{page_idx + 1}_img{page_image_index}.{ext}"
                            out_path = images_dir / filename
                            with open(out_path, "wb") as f:
                                f.write(img_bytes)

                        await self._save_document_image_meta(
                            doc_id=doc_id,
                            page_number=page_idx + 1,
                            image_index=page_image_index,
                            image_path=str(out_path),
                            image_format=ext,
                            width=int(img.get("width") or 0) or None,
                            height=int(img.get("height") or 0) or None,
                            color_space=str(img.get("colorspace") or "")[:32] or None,
                            extra_meta={"source": "pymupdf", "xref": xref, "y0": y0},
                        )
                        image_assets.append(
                            {
                                "page_number": page_idx + 1,
                                "image_index": page_image_index,
                                "image_path": str(out_path),
                                "image_format": ext,
                                "width": int(img.get("width") or 0) or None,
                                "height": int(img.get("height") or 0) or None,
                                "y0": y0,
                            }
                        )
                        extracted_count += 1
                    except Exception as img_exc:
                        logger.warning(f"[DocService] 嵌入图抽取失败 page={page_idx + 1}: {img_exc}")
                        continue

            # 若嵌入图抽取为空，回退到页面渲染（仍属图片处理链路，不退回纯文本方案）
            if extracted_count == 0:
                logger.info("[DocService] 未发现可提取嵌入图，启用页面渲染图片模式")
                image_assets.extend(await self._render_pdf_pages_as_images(doc, doc_id, images_dir))

            return image_assets
        finally:
            doc.close()

    async def _render_pdf_pages_as_images(self, doc: Any, doc_id: int, images_dir: Path) -> List[Dict[str, Any]]:
        """将 PDF 页面渲染成图片，保障图片链路可用。"""
        assets: List[Dict[str, Any]] = []
        max_pages = min(len(doc), 30)
        matrix = fitz.Matrix(1.6, 1.6)

        for page_idx in range(max_pages):
            try:
                page = doc[page_idx]
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                filename = f"p{page_idx + 1}_render1.png"
                out_path = images_dir / filename
                pix.save(str(out_path))

                await self._save_document_image_meta(
                    doc_id=doc_id,
                    page_number=page_idx + 1,
                    image_index=1,
                    image_path=str(out_path),
                    image_format="png",
                    width=int(pix.width),
                    height=int(pix.height),
                    color_space="rgb",
                    extra_meta={"source": "pymupdf_page_render"},
                )

                assets.append(
                    {
                        "page_number": page_idx + 1,
                        "image_index": 1,
                        "image_path": str(out_path),
                        "image_format": "png",
                        "width": int(pix.width),
                        "height": int(pix.height),
                        "y0": float(page.rect.height) * 0.5,
                    }
                )
            except Exception as exc:
                logger.warning(f"[DocService] 页面渲染失败 page={page_idx + 1}: {exc}")
        return assets

    async def _analyze_image_with_qwen_omni(self, image_path: Path) -> Dict[str, str]:
        """调用 env 配置的多模态模型生成图片描述，并提取图片表格。"""
        api_key = self.config.llm.effective_api_key
        base_url = (self.config.llm.base_url or "").rstrip("/")
        if not api_key or not base_url:
            logger.warning("[DocService] 图片描述跳过：LLM_API_KEY 或 BASE_URL 未配置")
            return {"caption": "", "table_markdown": ""}

        if not self.image_caption_model:
            logger.warning("[DocService] 图片描述跳过：IMAGE_CAPTION_MODEL_ID 未配置")
            return {"caption": "", "table_markdown": ""}

        if not image_path.exists():
            return {"caption": "", "table_markdown": ""}

        try:
            mime_type = mimetypes.guess_type(str(image_path))[0]
            if not mime_type:
                suffix = image_path.suffix.lower()
                mime_type = {
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".png": "image/png",
                    ".webp": "image/webp",
                    ".gif": "image/gif",
                    ".bmp": "image/bmp",
                }.get(suffix, "image/png")
            with open(image_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")

            payload = {
                "model": self.image_caption_model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "你是文档图像解析助手。"
                            "请输出JSON，字段包括caption和table_markdown。"
                            "caption用于概述图片；若图片包含表格，则table_markdown输出Markdown表格，否则为空字符串。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "请分析这张文档图片：\n"
                                    "1) caption: 用中文简洁描述图片要点（120字内）；\n"
                                    "2) table_markdown: 如果图中有表格，输出规范Markdown表格（含表头）；无表格则输出空字符串。\n"
                                    "只返回JSON，不要额外解释。"
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{b64}",
                                },
                            },
                        ],
                    },
                ],
                "temperature": 0.2,
                "max_tokens": 220,
            }

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            url = f"{base_url}/chat/completions"

            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                try:
                    resp.raise_for_status()
                except httpx.HTTPStatusError:
                    detail = (resp.text or "")[:1200]
                    logger.warning(
                        f"[DocService] 图片描述HTTP失败 image={image_path.name} status={resp.status_code} detail={detail}"
                    )
                    raise
                data = resp.json()

            content = (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "")
            if isinstance(content, list):
                text_parts = [str(x.get("text") or "") for x in content if isinstance(x, dict)]
                content = " ".join([t for t in text_parts if t]).strip()

            parsed = self._parse_image_analysis_json(str(content))
            caption = self._sanitize_text(parsed.get("caption") or "").strip()
            table_markdown = self._sanitize_text(parsed.get("table_markdown") or "").strip()
            return {"caption": caption, "table_markdown": table_markdown}
        except Exception as exc:
            logger.warning(f"[DocService] 图片描述失败 image={image_path.name}: {exc}")
            return {"caption": "", "table_markdown": ""}

    def _parse_image_analysis_json(self, raw: str) -> Dict[str, str]:
        """解析多模态返回，容忍代码块包装。"""
        if not raw:
            return {"caption": "", "table_markdown": ""}

        text_raw = raw.strip()
        match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text_raw, flags=re.IGNORECASE)
        candidate = match.group(1) if match else text_raw

        try:
            obj = json.loads(candidate)
            if not isinstance(obj, dict):
                return {"caption": text_raw[:200], "table_markdown": ""}
            return {
                "caption": str(obj.get("caption") or ""),
                "table_markdown": str(obj.get("table_markdown") or ""),
            }
        except Exception:
            # 回退：若不是JSON，整段作为caption
            return {"caption": text_raw[:200], "table_markdown": ""}

    def _build_image_caption_chunk(self, asset: Dict[str, Any], caption: str) -> str:
        """构建图片描述 chunk 文本，复用现有检索链路。"""
        page_number = asset.get("page_number")
        image_index = asset.get("image_index")
        image_format = asset.get("image_format") or "unknown"
        width = asset.get("width")
        height = asset.get("height")
        size_text = f"{width}x{height}" if width and height else "unknown"
        return (
            f"[IMAGE_CAPTION] page={page_number} image={image_index} format={image_format} size={size_text}\n"
            f"{caption}"
        ).strip()

    def _build_image_placeholder(self, asset: Dict[str, Any]) -> str:
        """构建图片占位符，后续在正文中替换成模型描述。"""
        page_number = int(asset.get("page_number") or 0)
        image_index = int(asset.get("image_index") or 0)
        return f"[[IMAGE_REF:p{page_number}_i{image_index}]]"

    async def _materialize_image_placeholders_in_text(
        self,
        text_content: str,
        image_assets: List[Dict[str, Any]],
    ) -> Tuple[str, int, int]:
        """将正文中的图片占位符替换为 qwen 生成的描述/表格。"""
        if not text_content:
            text_content = ""

        caption_count = 0
        table_count = 0
        output = text_content

        for asset in image_assets:
            placeholder = self._build_image_placeholder(asset)
            image_path = Path(str(asset.get("image_path") or ""))
            if not image_path.exists():
                output = output.replace(placeholder, "")
                continue

            analysis = await self._analyze_image_with_qwen_omni(image_path)
            caption = (analysis.get("caption") or "").strip() or "图片内容解析失败。"
            table_markdown = (analysis.get("table_markdown") or "").strip()

            inline_text = self._build_image_caption_chunk(asset, caption)
            caption_count += 1
            if table_markdown:
                inline_text = f"{inline_text}\n\n{self._build_image_table_chunk(asset, table_markdown)}"
                table_count += 1

            output = output.replace(placeholder, inline_text)

        return output, caption_count, table_count

    def _build_image_table_chunk(self, asset: Dict[str, Any], table_markdown: str) -> str:
        """构建图片表格 chunk 文本。"""
        page_number = asset.get("page_number")
        image_index = asset.get("image_index")
        table_markdown = self._sanitize_text(table_markdown)[:4500]
        return (
            f"[IMAGE_TABLE] page={page_number} image={image_index}\n"
            f"{table_markdown}"
        ).strip()

    async def _save_document_image_meta(
        self,
        doc_id: int,
        page_number: int,
        image_index: int,
        image_path: str,
        image_format: Optional[str],
        width: Optional[int],
        height: Optional[int],
        color_space: Optional[str],
        extra_meta: Optional[Dict],
    ) -> None:
        """写入文档图片元数据。"""
        try:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO project_document_images
                        (document_id, page_number, image_index, image_path, image_format, width, height, color_space, extra_meta, created_at)
                        VALUES
                        (:document_id, :page_number, :image_index, :image_path, :image_format, :width, :height, :color_space, :extra_meta, NOW())
                        """
                    ),
                    {
                        "document_id": doc_id,
                        "page_number": int(page_number),
                        "image_index": int(image_index),
                        "image_path": image_path,
                        "image_format": image_format,
                        "width": width,
                        "height": height,
                        "color_space": color_space,
                        "extra_meta": json.dumps(extra_meta or {}, ensure_ascii=False),
                    },
                )
        except Exception as exc:
            logger.warning(f"[DocService] 保存图片元数据失败: {exc}")
    
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

    def delete_document_assets(self, project_id: int, doc_id: int) -> None:
        """删除文档图片资产目录。"""
        images_dir = self.upload_dir / f"project_{project_id}" / "images" / f"doc_{doc_id}"
        if images_dir.exists():
            try:
                shutil.rmtree(images_dir)
            except Exception as e:
                logger.warning(f"[DocService] 删除图片资产失败 doc_id={doc_id}: {e}")
    
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
