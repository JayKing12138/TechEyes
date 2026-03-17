#!/usr/bin/env python3
"""自动化评测脚本：项目知识工作台 RAG（检索/生成/端到端）。

用法示例：
python scripts/evaluate_project_rag.py \
  --dataset scripts/rag_eval_dataset.sample.jsonl \
  --output logs/rag_eval_report.json
"""

import argparse
import asyncio
import json
import math
import re
import sys
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from loguru import logger


def normalize_text(text: str) -> str:
    value = (text or "").strip().lower()
    value = re.sub(r"\s+", " ", value)
    return value


def tokenize(text: str) -> List[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []
    return re.findall(r"[\w\u4e00-\u9fff]+", normalized)


def split_sentences(text: str) -> List[str]:
    content = (text or "").strip()
    if not content:
        return []
    parts = re.split(r"[。！？!?\n]+", content)
    return [p.strip() for p in parts if p.strip()]


def parse_json_maybe(raw: str) -> Optional[dict]:
    text = (raw or "").strip()
    if not text:
        return None
    if "```json" in text:
        try:
            text = text.split("```json", 1)[1].split("```", 1)[0].strip()
        except Exception:
            pass
    elif "```" in text:
        try:
            text = text.split("```", 1)[1].split("```", 1)[0].strip()
        except Exception:
            pass

    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass

    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


@dataclass
class RetrievalMetrics:
    hit_rate_at_k: float
    recall_at_k: float
    mrr_at_k: float
    ndcg_at_k: float


@dataclass
class GenerationMetrics:
    accuracy: float
    completeness: float
    faithfulness: float
    judge_source: str


class RAGEvaluator:
    def __init__(
        self,
        service: Any,
        top_k: int,
        rerank_top_k: int,
        use_llm_judge: bool,
        success_threshold: float,
        invalidate_before_each: bool,
    ):
        self.service = service
        self.top_k = top_k
        self.rerank_top_k = rerank_top_k
        self.use_llm_judge = use_llm_judge
        self.success_threshold = success_threshold
        self.invalidate_before_each = invalidate_before_each

    @staticmethod
    def _safe_int_list(values: Any) -> List[int]:
        if not isinstance(values, list):
            return []
        out: List[int] = []
        for v in values:
            try:
                out.append(int(v))
            except Exception:
                continue
        return out

    def _compute_retrieval_metrics(self, ranked_chunk_ids: List[int], relevant_chunk_ids: List[int], k: int) -> RetrievalMetrics:
        ranked = ranked_chunk_ids[:k]
        rel_set = set(relevant_chunk_ids)

        if not rel_set:
            return RetrievalMetrics(0.0, 0.0, 0.0, 0.0)

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

        return RetrievalMetrics(hit_rate, recall, mrr, ndcg)

    async def _retrieve_ranked_chunks(self, project_id: int, question: str) -> Tuple[List[Dict[str, Any]], float]:
        t0 = time.perf_counter()

        routing = await self.service.router.route(question)
        queries = [question]
        if routing.get("complexity") == "high":
            queries = await self.service.planner.decompose(question, max_sub_queries=3)

        all_doc_chunks: List[Dict[str, Any]] = []
        seen = set()
        for query in queries:
            chunks = await self.service.retriever.retrieve(project_id=project_id, query=query, top_k=self.top_k)
            for chunk in chunks:
                cid = chunk.get("chunk_id")
                if cid in seen:
                    continue
                seen.add(cid)
                all_doc_chunks.append(chunk)

        reranked = await self.service.reranker.rerank(
            query=question,
            candidates=all_doc_chunks,
            top_k=self.rerank_top_k,
            enable_diversity=True,
            max_per_doc=2,
        )

        latency_ms = (time.perf_counter() - t0) * 1000
        return reranked, latency_ms

    def _heuristic_generation_metrics(
        self,
        answer: str,
        reference_answer: str,
        required_facts: Sequence[str],
        evidence_texts: Sequence[str],
    ) -> GenerationMetrics:
        ans_tokens = tokenize(answer)
        ref_tokens = tokenize(reference_answer)

        if ans_tokens and ref_tokens:
            ans_set = set(ans_tokens)
            ref_set = set(ref_tokens)
            precision = len(ans_set & ref_set) / max(1, len(ans_set))
            recall = len(ans_set & ref_set) / max(1, len(ref_set))
            accuracy = (2 * precision * recall / max(1e-9, precision + recall))
        else:
            accuracy = 0.0

        norm_answer = normalize_text(answer)
        fact_hits = 0
        total_facts = len(required_facts)
        if total_facts > 0:
            for fact in required_facts:
                if normalize_text(str(fact)) and normalize_text(str(fact)) in norm_answer:
                    fact_hits += 1
            completeness = fact_hits / total_facts
        else:
            completeness = accuracy

        sentence_list = split_sentences(answer)
        evidence_tokens = [set(tokenize(text)) for text in evidence_texts if text]
        supported = 0
        for sent in sentence_list:
            sent_set = set(tokenize(sent))
            if not sent_set:
                continue
            is_supported = False
            for ev in evidence_tokens:
                overlap = len(sent_set & ev)
                ratio = overlap / max(1, len(sent_set))
                if ratio >= 0.35:
                    is_supported = True
                    break
            if is_supported:
                supported += 1
        faithfulness = supported / max(1, len(sentence_list)) if sentence_list else 0.0

        return GenerationMetrics(
            accuracy=max(0.0, min(1.0, accuracy)),
            completeness=max(0.0, min(1.0, completeness)),
            faithfulness=max(0.0, min(1.0, faithfulness)),
            judge_source="heuristic",
        )

    async def _llm_judge_generation_metrics(
        self,
        question: str,
        answer: str,
        reference_answer: str,
        required_facts: Sequence[str],
        evidence_texts: Sequence[str],
    ) -> Optional[GenerationMetrics]:
        if not self.use_llm_judge:
            return None

        evidence_preview = "\n\n".join(
            f"[证据{i+1}] {txt[:500]}" for i, txt in enumerate(evidence_texts[:5])
        )
        facts_preview = "\n".join(f"- {f}" for f in required_facts[:20]) if required_facts else "- 无"

        prompt = f"""你是RAG评测专家。请根据问题、标准答案、模型答案和证据，给出0~1分的评估。

问题:
{question}

标准答案:
{reference_answer or '无'}

模型答案:
{answer}

关键事实清单:
{facts_preview}

证据片段:
{evidence_preview or '无'}

评分标准:
1) accuracy: 答案和标准答案语义一致程度
2) completeness: 是否覆盖关键事实
3) faithfulness: 是否被证据支持，不编造

只返回JSON:
{{"accuracy": 0.0, "completeness": 0.0, "faithfulness": 0.0}}
"""

        try:
            raw = self.service.critic.agent.run(prompt)
            obj = parse_json_maybe(raw)
            if not obj:
                return None
            return GenerationMetrics(
                accuracy=float(obj.get("accuracy", 0.0)),
                completeness=float(obj.get("completeness", 0.0)),
                faithfulness=float(obj.get("faithfulness", 0.0)),
                judge_source="llm-judge",
            )
        except Exception as exc:
            logger.warning(f"LLM judge failed, fallback heuristic: {exc}")
            return None

    async def evaluate_one(self, sample: Dict[str, Any]) -> Dict[str, Any]:
        sample_id = sample.get("id") or f"sample-{int(time.time() * 1000)}"
        project_id = int(sample["project_id"])
        question = str(sample["question"])
        conversation_history = sample.get("conversation_history") or []
        expected_chunk_ids = self._safe_int_list(sample.get("expected_chunk_ids") or [])
        reference_answer = str(sample.get("reference_answer") or "")
        required_facts = sample.get("required_facts") or []
        enable_news = bool(sample.get("enable_news", False))

        if self.invalidate_before_each:
            await self.service.invalidate_project_cache(project_id)

        retrieval_chunks, retrieval_latency_ms = await self._retrieve_ranked_chunks(project_id, question)
        ranked_chunk_ids = [int(c.get("chunk_id")) for c in retrieval_chunks if c.get("chunk_id")]
        retrieval_metrics = self._compute_retrieval_metrics(ranked_chunk_ids, expected_chunk_ids, self.rerank_top_k)

        t0 = time.perf_counter()
        rag_result = await self.service.answer_with_rag(
            project_id=project_id,
            question=question,
            conversation_history=conversation_history,
            enable_news=enable_news,
        )
        e2e_latency_ms = (time.perf_counter() - t0) * 1000

        answer = rag_result.get("answer", "")
        evidence_chunks = rag_result.get("doc_chunks", [])
        evidence_texts = [str(c.get("text", "")) for c in evidence_chunks if c.get("text")]

        gen_metrics = await self._llm_judge_generation_metrics(
            question=question,
            answer=answer,
            reference_answer=reference_answer,
            required_facts=required_facts,
            evidence_texts=evidence_texts,
        )
        if gen_metrics is None:
            gen_metrics = self._heuristic_generation_metrics(
                answer=answer,
                reference_answer=reference_answer,
                required_facts=required_facts,
                evidence_texts=evidence_texts,
            )

        task_success = (
            retrieval_metrics.hit_rate_at_k >= 1.0
            and gen_metrics.accuracy >= self.success_threshold
            and gen_metrics.completeness >= self.success_threshold
            and gen_metrics.faithfulness >= self.success_threshold
        )

        return {
            "id": sample_id,
            "project_id": project_id,
            "question": question,
            "retrieval": {
                "top_k": self.rerank_top_k,
                "latency_ms": round(retrieval_latency_ms, 2),
                "expected_chunk_ids": expected_chunk_ids,
                "ranked_chunk_ids": ranked_chunk_ids,
                "hit_rate_at_k": round(retrieval_metrics.hit_rate_at_k, 4),
                "recall_at_k": round(retrieval_metrics.recall_at_k, 4),
                "mrr_at_k": round(retrieval_metrics.mrr_at_k, 4),
                "ndcg_at_k": round(retrieval_metrics.ndcg_at_k, 4),
            },
            "generation": {
                "judge": gen_metrics.judge_source,
                "accuracy": round(gen_metrics.accuracy, 4),
                "completeness": round(gen_metrics.completeness, 4),
                "faithfulness": round(gen_metrics.faithfulness, 4),
            },
            "end_to_end": {
                "latency_ms": round(e2e_latency_ms, 2),
                "task_success": task_success,
                "cache_hit": bool((rag_result.get("rag_info") or {}).get("cache_hit", False)),
            },
            "answer_preview": answer[:300],
            "rag_info": rag_result.get("rag_info", {}),
        }


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


def summarize(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not results:
        return {}

    retrieval_hit = [r["retrieval"]["hit_rate_at_k"] for r in results]
    retrieval_recall = [r["retrieval"]["recall_at_k"] for r in results]
    retrieval_mrr = [r["retrieval"]["mrr_at_k"] for r in results]
    retrieval_ndcg = [r["retrieval"]["ndcg_at_k"] for r in results]

    gen_acc = [r["generation"]["accuracy"] for r in results]
    gen_comp = [r["generation"]["completeness"] for r in results]
    gen_faith = [r["generation"]["faithfulness"] for r in results]

    latencies = [r["end_to_end"]["latency_ms"] for r in results]
    retrieval_latencies = [r["retrieval"]["latency_ms"] for r in results]
    success_list = [1.0 if r["end_to_end"]["task_success"] else 0.0 for r in results]

    return {
        "sample_count": len(results),
        "retrieval": {
            "hit_rate_at_k": round(statistics.mean(retrieval_hit), 4),
            "recall_at_k": round(statistics.mean(retrieval_recall), 4),
            "mrr_at_k": round(statistics.mean(retrieval_mrr), 4),
            "ndcg_at_k": round(statistics.mean(retrieval_ndcg), 4),
            "latency_ms_avg": round(statistics.mean(retrieval_latencies), 2),
            "latency_ms_p50": round(percentile(retrieval_latencies, 0.50), 2),
            "latency_ms_p95": round(percentile(retrieval_latencies, 0.95), 2),
        },
        "generation": {
            "accuracy": round(statistics.mean(gen_acc), 4),
            "completeness": round(statistics.mean(gen_comp), 4),
            "faithfulness": round(statistics.mean(gen_faith), 4),
        },
        "end_to_end": {
            "task_success_rate": round(statistics.mean(success_list), 4),
            "latency_ms_avg": round(statistics.mean(latencies), 2),
            "latency_ms_p50": round(percentile(latencies, 0.50), 2),
            "latency_ms_p95": round(percentile(latencies, 0.95), 2),
            "cache_hit_rate": round(statistics.mean([1.0 if r["end_to_end"]["cache_hit"] else 0.0 for r in results]), 4),
        },
    }


def load_dataset(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"dataset not found: {path}")

    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            text = line.strip()
            if not text or text.startswith("#"):
                continue
            obj = json.loads(text)
            if "project_id" not in obj or "question" not in obj:
                raise ValueError(f"line {idx}: missing required fields project_id/question")
            rows.append(obj)
    return rows


async def run(args: argparse.Namespace) -> Dict[str, Any]:
    # 延迟导入，避免仅查看 --help 时强依赖业务运行环境。
    from config import get_config
    from services.project_rag_service import ProjectRAGService

    dataset_path = Path(args.dataset)
    output_path = Path(args.output)

    samples = load_dataset(dataset_path)
    if not samples:
        raise ValueError("dataset is empty")

    config = get_config()
    logger.info(
        f"RAG评测启动: samples={len(samples)}, model={config.llm.provider}:{config.llm.model_id}, "
        f"top_k={args.top_k}, rerank_top_k={args.rerank_top_k}"
    )

    evaluator = RAGEvaluator(
        service=ProjectRAGService(),
        top_k=args.top_k,
        rerank_top_k=args.rerank_top_k,
        use_llm_judge=args.use_llm_judge,
        success_threshold=args.success_threshold,
        invalidate_before_each=args.invalidate_before_each,
    )

    details: List[Dict[str, Any]] = []
    for idx, sample in enumerate(samples, start=1):
        logger.info(f"[{idx}/{len(samples)}] evaluating sample_id={sample.get('id', idx)}")
        result = await evaluator.evaluate_one(sample)
        details.append(result)

    summary = summarize(details)
    report = {
        "summary": summary,
        "details": details,
        "config": {
            "dataset": str(dataset_path),
            "top_k": args.top_k,
            "rerank_top_k": args.rerank_top_k,
            "use_llm_judge": args.use_llm_judge,
            "success_threshold": args.success_threshold,
            "invalidate_before_each": args.invalidate_before_each,
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate Project Workbench RAG")
    parser.add_argument("--dataset", required=True, help="JSONL dataset path")
    parser.add_argument("--output", default="logs/rag_eval_report.json", help="Output report path")
    parser.add_argument("--top-k", type=int, default=15, help="Retriever top_k")
    parser.add_argument("--rerank-top-k", type=int, default=5, help="Reranker output top_k")
    parser.add_argument("--use-llm-judge", action="store_true", help="Use LLM judge for generation metrics")
    parser.add_argument("--success-threshold", type=float, default=0.6, help="Threshold for task success")
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

    print("\n=== RAG Evaluation Summary ===")
    print(json.dumps(report.get("summary", {}), ensure_ascii=False, indent=2))
    print(f"\nReport written to: {args.output}")


if __name__ == "__main__":
    main()
