#!/usr/bin/env python3
"""使用 RAGAS 评估项目知识工作台 RAG。

用法示例：
python scripts/evaluate_project_rag_ragas.py \
  --dataset scripts/rag_eval_dataset.sample.jsonl \
  --output logs/rag_eval_ragas_report.json \
  --metric-set full
"""

import argparse
import asyncio
import json
import math
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Sequence

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from loguru import logger
from openai import OpenAI
from ragas import evaluate
from ragas.dataset_schema import EvaluationDataset
from ragas.embeddings.base import embedding_factory
from ragas.llms import llm_factory
from ragas.metrics._answer_relevance import ResponseRelevancy
from ragas.metrics._context_precision import NonLLMContextPrecisionWithReference
from ragas.metrics._context_recall import LLMContextRecall
from ragas.metrics._factual_correctness import FactualCorrectness
from ragas.metrics._faithfulness import Faithfulness
from sqlalchemy import bindparam, text


def load_dataset(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"dataset not found: {path}")

    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            text_line = line.strip()
            if not text_line or text_line.startswith("#"):
                continue
            obj = json.loads(text_line)
            if "project_id" not in obj or "question" not in obj:
                raise ValueError(f"line {idx}: missing required fields project_id/question")
            rows.append(obj)
    return rows


def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(sorted_vals[int(k)])
    d0 = sorted_vals[f] * (c - k)
    d1 = sorted_vals[c] * (k - f)
    return float(d0 + d1)


def safe_int_list(values: Any) -> List[int]:
    if not isinstance(values, list):
        return []
    out: List[int] = []
    for value in values:
        try:
            out.append(int(value))
        except Exception:
            continue
    return out


def fetch_chunk_texts(project_id: int, chunk_ids: Sequence[int]) -> List[str]:
    if not chunk_ids:
        return []

    from database import engine

    query = text(
        """
        SELECT c.id, c.text_content
        FROM project_document_chunks c
        JOIN project_documents d ON d.id = c.document_id
        WHERE d.project_id = :project_id
          AND c.id IN :chunk_ids
        """
    ).bindparams(bindparam("chunk_ids", expanding=True))

    with engine.connect() as conn:
        rows = conn.execute(
            query,
            {
                "project_id": project_id,
                "chunk_ids": list(chunk_ids),
            },
        ).mappings().all()

    text_map = {int(row["id"]): str(row["text_content"] or "") for row in rows}
    return [text_map[cid] for cid in chunk_ids if cid in text_map and text_map[cid]]


def build_metrics(metric_set: str) -> List[Any]:
    if metric_set == "retrieval":
        return [
            NonLLMContextPrecisionWithReference(),
            LLMContextRecall(),
        ]
    if metric_set == "generation":
        return [
            Faithfulness(),
            ResponseRelevancy(),
            FactualCorrectness(mode="f1"),
        ]
    return [
        NonLLMContextPrecisionWithReference(),
        LLMContextRecall(),
        Faithfulness(),
        ResponseRelevancy(),
        FactualCorrectness(mode="f1"),
    ]


def summarize(details: List[Dict[str, Any]], ragas_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    latencies = [float(item.get("latency_ms", 0.0)) for item in details]
    cache_hits = [1.0 if item.get("cache_hit") else 0.0 for item in details]

    metric_names = [
        "non_llm_context_precision_with_reference",
        "context_recall",
        "faithfulness",
        "answer_relevancy",
        "factual_correctness",
    ]
    metric_summary: Dict[str, float] = {}
    for name in metric_names:
        values = [row.get(name) for row in ragas_rows if isinstance(row.get(name), (int, float))]
        if values:
            metric_summary[name] = round(statistics.mean(values), 4)

    return {
        "sample_count": len(details),
        "ragas": metric_summary,
        "latency_ms_avg": round(statistics.mean(latencies), 2) if latencies else 0.0,
        "latency_ms_p50": round(percentile(latencies, 0.50), 2) if latencies else 0.0,
        "latency_ms_p95": round(percentile(latencies, 0.95), 2) if latencies else 0.0,
        "cache_hit_rate": round(statistics.mean(cache_hits), 4) if cache_hits else 0.0,
    }


async def build_ragas_rows(
    service: Any,
    samples: List[Dict[str, Any]],
    invalidate_before_each: bool,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    ragas_rows: List[Dict[str, Any]] = []
    details: List[Dict[str, Any]] = []

    for idx, sample in enumerate(samples, start=1):
        sample_id = sample.get("id") or f"sample-{idx}"
        project_id = int(sample["project_id"])
        question = str(sample["question"])
        conversation_history = sample.get("conversation_history") or []
        enable_news = bool(sample.get("enable_news", False))
        expected_chunk_ids = safe_int_list(sample.get("expected_chunk_ids") or [])

        if invalidate_before_each:
            await service.invalidate_project_cache(project_id)

        t0 = time.perf_counter()
        rag_result = await service.answer_with_rag(
            project_id=project_id,
            question=question,
            conversation_history=conversation_history,
            enable_news=enable_news,
        )
        latency_ms = (time.perf_counter() - t0) * 1000

        doc_chunks = rag_result.get("doc_chunks") or []
        retrieved_contexts = [str(chunk.get("text") or "") for chunk in doc_chunks if chunk.get("text")]
        retrieved_context_ids = [str(int(chunk.get("chunk_id"))) for chunk in doc_chunks if chunk.get("chunk_id")]
        reference_contexts = fetch_chunk_texts(project_id, expected_chunk_ids)

        ragas_rows.append(
            {
                "user_input": question,
                "retrieved_contexts": retrieved_contexts,
                "reference_contexts": reference_contexts,
                "retrieved_context_ids": retrieved_context_ids,
                "reference_context_ids": [str(cid) for cid in expected_chunk_ids],
                "response": str(rag_result.get("answer") or ""),
                "reference": str(sample.get("reference_answer") or ""),
            }
        )

        rag_info = rag_result.get("rag_info") or {}
        details.append(
            {
                "id": sample_id,
                "project_id": project_id,
                "question": question,
                "latency_ms": round(latency_ms, 2),
                "cache_hit": bool(rag_info.get("cache_hit", False)),
                "cache_source": rag_info.get("cache_source"),
                "doc_count": len(doc_chunks),
                "news_count": len(rag_result.get("news_sources") or []),
                "expected_chunk_ids": expected_chunk_ids,
                "retrieved_chunk_ids": [int(cid) for cid in retrieved_context_ids],
                "validation": rag_info.get("validation"),
                "routing": rag_info.get("routing"),
                "answer_preview": str(rag_result.get("answer") or "")[:300],
            }
        )

        logger.info(
            f"[{idx}/{len(samples)}] prepared sample_id={sample_id}, "
            f"retrieved={len(retrieved_contexts)}, references={len(reference_contexts)}"
        )

    return ragas_rows, details


async def run(args: argparse.Namespace) -> Dict[str, Any]:
    from config import get_config
    from services.project_rag_service import project_rag_service

    dataset_path = Path(args.dataset)
    output_path = Path(args.output)

    samples = load_dataset(dataset_path)
    if not samples:
        raise ValueError("dataset is empty")

    config = get_config()
    service = project_rag_service
    ragas_data, details = await build_ragas_rows(
        service=service,
        samples=samples,
        invalidate_before_each=args.invalidate_before_each,
    )

    dataset = EvaluationDataset.from_list(ragas_data)
    metrics = build_metrics(args.metric_set)

    need_llm = any(metric.name in {"context_recall", "faithfulness", "answer_relevancy", "factual_correctness"} for metric in metrics)
    need_embeddings = any(metric.name in {"answer_relevancy"} for metric in metrics)

    llm = None
    embeddings = None
    if need_llm or need_embeddings:
        client = OpenAI(api_key=config.llm.api_key, base_url=config.llm.base_url)
        if need_llm:
            llm = llm_factory(config.llm.model_id, provider="openai", client=client)
        if need_embeddings:
            embeddings = embedding_factory(
                provider="openai",
                model=args.embedding_model,
                client=client,
                base_url=config.llm.base_url,
            )

    logger.info(
        f"RAGAS 评测启动: samples={len(samples)}, metric_set={args.metric_set}, "
        f"llm={config.llm.provider}:{config.llm.model_id}, embedding_model={args.embedding_model}"
    )

    result = evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=llm,
        embeddings=embeddings,
        raise_exceptions=False,
        show_progress=True,
        batch_size=args.batch_size,
    )
    ragas_rows = result.to_pandas().to_dict(orient="records")

    report = {
        "summary": summarize(details, ragas_rows),
        "details": [
            {
                **detail,
                "ragas": {
                    key: row.get(key)
                    for key in [
                        "non_llm_context_precision_with_reference",
                        "context_recall",
                        "faithfulness",
                        "answer_relevancy",
                        "factual_correctness",
                    ]
                    if key in row
                },
            }
            for detail, row in zip(details, ragas_rows)
        ],
        "config": {
            "dataset": str(dataset_path),
            "output": str(output_path),
            "metric_set": args.metric_set,
            "embedding_model": args.embedding_model,
            "batch_size": args.batch_size,
            "invalidate_before_each": args.invalidate_before_each,
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate Project RAG with RAGAS")
    parser.add_argument("--dataset", required=True, help="JSONL dataset path")
    parser.add_argument("--output", default="logs/rag_eval_ragas_report.json", help="Output report path")
    parser.add_argument(
        "--metric-set",
        choices=["full", "retrieval", "generation"],
        default="full",
        help="Metric bundle to run",
    )
    parser.add_argument("--embedding-model", default="text-embedding-v4", help="Embedding model for RAGAS")
    parser.add_argument("--batch-size", type=int, default=None, help="RAGAS batch size")
    parser.add_argument(
        "--invalidate-before-each",
        action="store_true",
        help="Invalidate project cache before each sample to reduce cache impact",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    report = asyncio.run(run(args))

    print("\n=== RAGAS Evaluation Summary ===")
    print(json.dumps(report.get("summary", {}), ensure_ascii=False, indent=2))
    print(f"\nReport written to: {args.output}")


if __name__ == "__main__":
    main()