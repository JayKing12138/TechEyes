#!/usr/bin/env python3
"""评估 RAG 各 Agent（Router/Retriever/Reranker/Critic）。

支持两种模式：
1) 单 Agent: --agent router --dataset xxx.jsonl
2) 全量 Agent: --agent all --router-dataset ... --retriever-dataset ... --reranker-dataset ... --critic-dataset ...
"""

import argparse
import asyncio
import json
import math
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from loguru import logger


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"dataset not found: {path}")

    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            text = line.strip()
            if not text or text.startswith("#"):
                continue
            obj = json.loads(text)
            if not isinstance(obj, dict):
                raise ValueError(f"line {idx}: expected JSON object")
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


def compute_retrieval_metrics(ranked_ids: List[int], relevant_ids: List[int], k: int) -> Dict[str, float]:
    ranked = ranked_ids[:k]
    rel_set = set(relevant_ids)
    if not rel_set:
        return {"hit_rate_at_k": 0.0, "recall_at_k": 0.0, "mrr_at_k": 0.0, "ndcg_at_k": 0.0}

    hits = [1 if cid in rel_set else 0 for cid in ranked]
    hit_rate = 1.0 if any(hits) else 0.0
    recall = sum(hits) / len(rel_set)

    mrr = 0.0
    for idx, cid in enumerate(ranked, start=1):
        if cid in rel_set:
            mrr = 1.0 / idx
            break

    dcg = 0.0
    for idx, cid in enumerate(ranked, start=1):
        rel = 1.0 if cid in rel_set else 0.0
        if rel > 0:
            dcg += rel / math.log2(idx + 1)

    ideal_hits = min(len(rel_set), k)
    idcg = 0.0
    for idx in range(1, ideal_hits + 1):
        idcg += 1.0 / math.log2(idx + 1)
    ndcg = (dcg / idcg) if idcg > 0 else 0.0

    return {
        "hit_rate_at_k": hit_rate,
        "recall_at_k": recall,
        "mrr_at_k": mrr,
        "ndcg_at_k": ndcg,
    }


def binary_stats(y_true: List[int], y_pred: List[int]) -> Dict[str, float]:
    tp = sum(1 for a, b in zip(y_true, y_pred) if a == 1 and b == 1)
    tn = sum(1 for a, b in zip(y_true, y_pred) if a == 0 and b == 0)
    fp = sum(1 for a, b in zip(y_true, y_pred) if a == 0 and b == 1)
    fn = sum(1 for a, b in zip(y_true, y_pred) if a == 1 and b == 0)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    acc = (tp + tn) / max(1, len(y_true))

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": acc,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


class AgentEvaluator:
    def __init__(self):
        from agents.rag.router_agent import RouterAgent
        from agents.rag.retriever_agent import RetrieverAgent
        from agents.rag.reranker_agent import RerankerAgent
        from agents.rag.critic_agent import CriticAgent

        self.router = RouterAgent()
        self.retriever = RetrieverAgent()
        self.reranker = RerankerAgent()
        self.critic = CriticAgent()

    async def evaluate_router(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        details: List[Dict[str, Any]] = []
        field_hits = {
            "intent": [],
            "complexity": [],
            "need_web": [],
            "need_doc": [],
            "allow_model_knowledge": [],
        }
        latencies: List[float] = []
        fallback_flags: List[int] = []

        for idx, sample in enumerate(samples, start=1):
            sample_id = sample.get("id") or f"sample-{idx}"
            question = str(sample.get("question") or "")
            expected = sample.get("expected") or {}

            t0 = time.perf_counter()
            pred = await self.router.route(question)
            latency_ms = (time.perf_counter() - t0) * 1000
            latencies.append(latency_ms)

            fallback = 1 if str(pred.get("reasoning") or "") == "使用默认路由策略" else 0
            fallback_flags.append(fallback)

            row = {"id": sample_id, "question": question, "latency_ms": round(latency_ms, 2), "pred": pred, "expected": expected}
            for field in field_hits.keys():
                if field in expected:
                    hit = 1 if pred.get(field) == expected.get(field) else 0
                    field_hits[field].append(hit)
                    row[f"{field}_hit"] = bool(hit)
            details.append(row)

        summary = {
            "sample_count": len(details),
            "fallback_rate": round(statistics.mean(fallback_flags), 4) if fallback_flags else 0.0,
            "latency_ms_avg": round(statistics.mean(latencies), 2) if latencies else 0.0,
            "latency_ms_p50": round(percentile(latencies, 0.50), 2) if latencies else 0.0,
            "latency_ms_p95": round(percentile(latencies, 0.95), 2) if latencies else 0.0,
        }
        for field, values in field_hits.items():
            if values:
                summary[f"{field}_accuracy"] = round(statistics.mean(values), 4)

        return {"summary": summary, "details": details}

    async def evaluate_retriever(self, samples: List[Dict[str, Any]], top_k_default: int) -> Dict[str, Any]:
        details: List[Dict[str, Any]] = []
        latencies: List[float] = []
        hit_rates: List[float] = []
        recalls: List[float] = []
        mrrs: List[float] = []
        ndcgs: List[float] = []
        empty_rates: List[int] = []

        for idx, sample in enumerate(samples, start=1):
            sample_id = sample.get("id") or f"sample-{idx}"
            project_id = int(sample["project_id"])
            question = str(sample["question"])
            expected_ids = safe_int_list(sample.get("expected_chunk_ids") or [])
            top_k = int(sample.get("top_k") or top_k_default)

            t0 = time.perf_counter()
            candidates = await self.retriever.retrieve(project_id=project_id, query=question, top_k=top_k)
            latency_ms = (time.perf_counter() - t0) * 1000
            latencies.append(latency_ms)

            ranked_ids = [int(c.get("chunk_id")) for c in candidates if c.get("chunk_id")]
            metrics = compute_retrieval_metrics(ranked_ids, expected_ids, top_k)
            hit_rates.append(metrics["hit_rate_at_k"])
            recalls.append(metrics["recall_at_k"])
            mrrs.append(metrics["mrr_at_k"])
            ndcgs.append(metrics["ndcg_at_k"])
            empty_rates.append(1 if len(ranked_ids) == 0 else 0)

            details.append(
                {
                    "id": sample_id,
                    "project_id": project_id,
                    "question": question,
                    "top_k": top_k,
                    "latency_ms": round(latency_ms, 2),
                    "expected_chunk_ids": expected_ids,
                    "ranked_chunk_ids": ranked_ids,
                    "metrics": {k: round(v, 4) for k, v in metrics.items()},
                }
            )

        summary = {
            "sample_count": len(details),
            "hit_rate_at_k": round(statistics.mean(hit_rates), 4) if hit_rates else 0.0,
            "recall_at_k": round(statistics.mean(recalls), 4) if recalls else 0.0,
            "mrr_at_k": round(statistics.mean(mrrs), 4) if mrrs else 0.0,
            "ndcg_at_k": round(statistics.mean(ndcgs), 4) if ndcgs else 0.0,
            "empty_retrieval_rate": round(statistics.mean(empty_rates), 4) if empty_rates else 0.0,
            "latency_ms_avg": round(statistics.mean(latencies), 2) if latencies else 0.0,
            "latency_ms_p50": round(percentile(latencies, 0.50), 2) if latencies else 0.0,
            "latency_ms_p95": round(percentile(latencies, 0.95), 2) if latencies else 0.0,
        }
        return {"summary": summary, "details": details}

    async def evaluate_reranker(
        self,
        samples: List[Dict[str, Any]],
        retriever_top_k: int,
        rerank_top_k: int,
    ) -> Dict[str, Any]:
        details: List[Dict[str, Any]] = []
        latencies: List[float] = []
        hit_rates: List[float] = []
        recalls: List[float] = []
        mrrs: List[float] = []
        ndcgs: List[float] = []
        doc_diversities: List[float] = []

        for idx, sample in enumerate(samples, start=1):
            sample_id = sample.get("id") or f"sample-{idx}"
            question = str(sample["question"])
            expected_ids = safe_int_list(sample.get("expected_chunk_ids") or [])
            top_k = int(sample.get("rerank_top_k") or rerank_top_k)

            candidates = sample.get("candidates")
            if not isinstance(candidates, list):
                project_id = int(sample["project_id"])
                candidates = await self.retriever.retrieve(project_id=project_id, query=question, top_k=retriever_top_k)

            t0 = time.perf_counter()
            ranked = await self.reranker.rerank(
                query=question,
                candidates=candidates,
                top_k=top_k,
                enable_diversity=bool(sample.get("enable_diversity", True)),
                max_per_doc=int(sample.get("max_per_doc") or 2),
            )
            latency_ms = (time.perf_counter() - t0) * 1000
            latencies.append(latency_ms)

            ranked_ids = [int(c.get("chunk_id")) for c in ranked if c.get("chunk_id")]
            metrics = compute_retrieval_metrics(ranked_ids, expected_ids, top_k)
            hit_rates.append(metrics["hit_rate_at_k"])
            recalls.append(metrics["recall_at_k"])
            mrrs.append(metrics["mrr_at_k"])
            ndcgs.append(metrics["ndcg_at_k"])

            unique_docs = len({c.get("document_id") for c in ranked if c.get("document_id") is not None})
            doc_diversity = unique_docs / max(1, len(ranked))
            doc_diversities.append(doc_diversity)

            details.append(
                {
                    "id": sample_id,
                    "question": question,
                    "latency_ms": round(latency_ms, 2),
                    "expected_chunk_ids": expected_ids,
                    "ranked_chunk_ids": ranked_ids,
                    "unique_docs": unique_docs,
                    "doc_diversity_ratio": round(doc_diversity, 4),
                    "metrics": {k: round(v, 4) for k, v in metrics.items()},
                }
            )

        summary = {
            "sample_count": len(details),
            "hit_rate_at_k": round(statistics.mean(hit_rates), 4) if hit_rates else 0.0,
            "recall_at_k": round(statistics.mean(recalls), 4) if recalls else 0.0,
            "mrr_at_k": round(statistics.mean(mrrs), 4) if mrrs else 0.0,
            "ndcg_at_k": round(statistics.mean(ndcgs), 4) if ndcgs else 0.0,
            "doc_diversity_ratio": round(statistics.mean(doc_diversities), 4) if doc_diversities else 0.0,
            "latency_ms_avg": round(statistics.mean(latencies), 2) if latencies else 0.0,
            "latency_ms_p50": round(percentile(latencies, 0.50), 2) if latencies else 0.0,
            "latency_ms_p95": round(percentile(latencies, 0.95), 2) if latencies else 0.0,
        }
        return {"summary": summary, "details": details}

    async def evaluate_critic(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        details: List[Dict[str, Any]] = []
        latencies: List[float] = []

        y_true_h: List[int] = []
        y_pred_h: List[int] = []
        y_true_c: List[int] = []
        y_pred_c: List[int] = []
        y_true_s: List[int] = []
        y_pred_s: List[int] = []
        y_true_v: List[int] = []
        y_pred_v: List[int] = []

        for idx, sample in enumerate(samples, start=1):
            sample_id = sample.get("id") or f"sample-{idx}"
            query = str(sample.get("query") or "")
            answer = str(sample.get("answer") or "")
            evidence_chunks = sample.get("evidence_chunks") or []
            label = sample.get("label") or {}

            t0 = time.perf_counter()
            pred = await self.critic.validate(query=query, answer=answer, evidence_chunks=evidence_chunks)
            latency_ms = (time.perf_counter() - t0) * 1000
            latencies.append(latency_ms)

            if "hallucination" in label:
                y_true_h.append(1 if bool(label.get("hallucination")) else 0)
                y_pred_h.append(1 if bool(pred.get("hallucination")) else 0)
            if "citation_invalid" in label:
                y_true_c.append(1 if bool(label.get("citation_invalid")) else 0)
                y_pred_c.append(1 if bool(pred.get("citation_invalid")) else 0)
            if "sufficient" in label:
                y_true_s.append(1 if bool(label.get("sufficient")) else 0)
                y_pred_s.append(1 if bool(pred.get("sufficient")) else 0)
            if "valid" in label:
                y_true_v.append(1 if bool(label.get("valid")) else 0)
                y_pred_v.append(1 if bool(pred.get("valid")) else 0)

            details.append(
                {
                    "id": sample_id,
                    "query": query,
                    "latency_ms": round(latency_ms, 2),
                    "label": label,
                    "pred": pred,
                }
            )

        summary: Dict[str, Any] = {
            "sample_count": len(details),
            "latency_ms_avg": round(statistics.mean(latencies), 2) if latencies else 0.0,
            "latency_ms_p50": round(percentile(latencies, 0.50), 2) if latencies else 0.0,
            "latency_ms_p95": round(percentile(latencies, 0.95), 2) if latencies else 0.0,
        }

        if y_true_h:
            summary["hallucination"] = {k: round(v, 4) if isinstance(v, float) else v for k, v in binary_stats(y_true_h, y_pred_h).items()}
        if y_true_c:
            summary["citation_invalid"] = {k: round(v, 4) if isinstance(v, float) else v for k, v in binary_stats(y_true_c, y_pred_c).items()}
        if y_true_s:
            summary["sufficient"] = {k: round(v, 4) if isinstance(v, float) else v for k, v in binary_stats(y_true_s, y_pred_s).items()}
        if y_true_v:
            summary["valid"] = {k: round(v, 4) if isinstance(v, float) else v for k, v in binary_stats(y_true_v, y_pred_v).items()}

        return {"summary": summary, "details": details}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate RAG agents individually")
    parser.add_argument("--agent", choices=["router", "retriever", "reranker", "critic", "all"], required=True)

    parser.add_argument("--dataset", help="Dataset JSONL for single-agent mode")
    parser.add_argument("--router-dataset", help="Router dataset JSONL (for --agent all)")
    parser.add_argument("--retriever-dataset", help="Retriever dataset JSONL (for --agent all)")
    parser.add_argument("--reranker-dataset", help="Reranker dataset JSONL (for --agent all)")
    parser.add_argument("--critic-dataset", help="Critic dataset JSONL (for --agent all)")

    parser.add_argument("--retriever-top-k", type=int, default=15)
    parser.add_argument("--rerank-top-k", type=int, default=5)
    parser.add_argument("--output", default="logs/rag_agent_eval_report.json")
    return parser


def ensure_single_dataset(args: argparse.Namespace) -> Path:
    if not args.dataset:
        raise ValueError("--dataset is required for single-agent mode")
    return Path(args.dataset)


async def run(args: argparse.Namespace) -> Dict[str, Any]:
    evaluator = AgentEvaluator()
    report: Dict[str, Any] = {"mode": args.agent, "results": {}}

    if args.agent == "router":
        samples = load_jsonl(ensure_single_dataset(args))
        report["results"]["router"] = await evaluator.evaluate_router(samples)
    elif args.agent == "retriever":
        samples = load_jsonl(ensure_single_dataset(args))
        report["results"]["retriever"] = await evaluator.evaluate_retriever(samples, top_k_default=args.retriever_top_k)
    elif args.agent == "reranker":
        samples = load_jsonl(ensure_single_dataset(args))
        report["results"]["reranker"] = await evaluator.evaluate_reranker(
            samples,
            retriever_top_k=args.retriever_top_k,
            rerank_top_k=args.rerank_top_k,
        )
    elif args.agent == "critic":
        samples = load_jsonl(ensure_single_dataset(args))
        report["results"]["critic"] = await evaluator.evaluate_critic(samples)
    else:
        if not args.router_dataset:
            raise ValueError("--router-dataset is required for --agent all")
        if not args.retriever_dataset:
            raise ValueError("--retriever-dataset is required for --agent all")
        if not args.reranker_dataset:
            raise ValueError("--reranker-dataset is required for --agent all")
        if not args.critic_dataset:
            raise ValueError("--critic-dataset is required for --agent all")

        report["results"]["router"] = await evaluator.evaluate_router(load_jsonl(Path(args.router_dataset)))
        report["results"]["retriever"] = await evaluator.evaluate_retriever(
            load_jsonl(Path(args.retriever_dataset)),
            top_k_default=args.retriever_top_k,
        )
        report["results"]["reranker"] = await evaluator.evaluate_reranker(
            load_jsonl(Path(args.reranker_dataset)),
            retriever_top_k=args.retriever_top_k,
            rerank_top_k=args.rerank_top_k,
        )
        report["results"]["critic"] = await evaluator.evaluate_critic(load_jsonl(Path(args.critic_dataset)))

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    report = asyncio.run(run(args))

    print("\n=== Agent Evaluation Summary ===")
    for name, result in report.get("results", {}).items():
        print(f"[{name}]")
        print(json.dumps(result.get("summary", {}), ensure_ascii=False, indent=2))
    print(f"\nReport written to: {args.output}")


if __name__ == "__main__":
    main()
