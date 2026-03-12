"""从 PostgreSQL 将历史 chunk 向量回填到 Chroma。"""

import json

from sqlalchemy import text

from config import get_config
from database import engine
from services.document_service import DocumentService


def main() -> None:
    config = get_config()
    svc = DocumentService()

    sql = text(
        """
        SELECT
            c.id AS chunk_id,
            c.document_id,
            c.chunk_index,
            c.text_content,
            c.embedding_json,
            d.project_id,
            d.filename
        FROM project_document_chunks c
        JOIN project_documents d ON d.id = c.document_id
        WHERE d.deleted_at IS NULL
          AND d.processed_at IS NOT NULL
          AND c.embedding_json IS NOT NULL
        ORDER BY c.id ASC
        """
    )

    with engine.begin() as conn:
        rows = conn.execute(sql).mappings().all()

    if not rows:
        print("没有可回填的数据。")
        return

    success = 0
    skipped = 0

    for row in rows:
        emb = row["embedding_json"]
        if isinstance(emb, str):
            try:
                emb = json.loads(emb)
            except Exception:
                emb = None

        if not isinstance(emb, list) or not emb:
            skipped += 1
            continue

        try:
            svc.chroma_collection.upsert(
                ids=[str(int(row["chunk_id"]))],
                embeddings=[[float(x) for x in emb]],
                documents=[str(row["text_content"] or "")[:5000]],
                metadatas=[
                    {
                        "project_id": int(row["project_id"]),
                        "document_id": int(row["document_id"]),
                        "chunk_id": int(row["chunk_id"]),
                        "chunk_index": int(row["chunk_index"] or 0),
                        "filename": str(row["filename"] or ""),
                    }
                ],
            )
            success += 1
        except Exception:
            skipped += 1

    print(
        f"Chroma 回填完成: total={len(rows)}, success={success}, skipped={skipped}, chroma_path={config.app.chroma_path}"
    )


if __name__ == "__main__":
    main()
