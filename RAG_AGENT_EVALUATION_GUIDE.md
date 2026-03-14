# RAG And Agent Evaluation Guide

本文说明如何在 TechEyes 项目中对 RAG 整链路和各个 Agent 分别进行测评。

## 1. 测评对象

- RAG 整链路测评：使用 RAGAS，对检索与生成效果做端到端评估。
- Agent 分模块测评：分别评估 Router、Retriever、Reranker、Critic。

## 2. 进入目录与环境

```bash
cd /Users/cairongqing/Documents/techeyes/backend
conda activate techeyes
```

## 3. RAG 整链路测评（RAGAS）

脚本：`backend/scripts/evaluate_project_rag_ragas.py`

### 3.1 仅检索指标（建议先跑）

```bash
python scripts/evaluate_project_rag_ragas.py \
  --dataset scripts/rag_eval_dataset.sample.jsonl \
  --output logs/rag_eval_ragas_report.json \
  --metric-set retrieval \
  --invalidate-before-each
```

### 3.2 全量指标（检索 + 生成）

```bash
python scripts/evaluate_project_rag_ragas.py \
  --dataset scripts/rag_eval_dataset.sample.jsonl \
  --output logs/rag_eval_ragas_report_full.json \
  --metric-set full \
  --invalidate-before-each
```

### 3.3 指标说明

- `non_llm_context_precision_with_reference`：检索上下文精度（越高越好）
- `context_recall`：检索上下文召回（越高越好）
- `faithfulness`：回答是否忠于证据（越高越好）
- `answer_relevancy`：回答与问题相关性（越高越好）
- `factual_correctness`：回答与参考答案事实一致性（越高越好）

报告输出在 `backend/logs/`。

## 4. Agent 分模块测评

脚本：`backend/scripts/evaluate_rag_agents.py`

### 4.1 Router

```bash
python scripts/evaluate_rag_agents.py \
  --agent router \
  --dataset scripts/router_eval_dataset.sample.jsonl \
  --output logs/router_eval_report.json
```

关键指标：`intent/complexity/need_web/need_doc` 准确率、`fallback_rate`。

### 4.2 Retriever

```bash
python scripts/evaluate_rag_agents.py \
  --agent retriever \
  --dataset scripts/retriever_eval_dataset.sample.jsonl \
  --output logs/retriever_eval_report.json
```

关键指标：`hit_rate_at_k`、`recall_at_k`、`mrr_at_k`、`ndcg_at_k`。

### 4.3 Reranker

```bash
python scripts/evaluate_rag_agents.py \
  --agent reranker \
  --dataset scripts/reranker_eval_dataset.sample.jsonl \
  --output logs/reranker_eval_report.json
```

关键指标：排序指标 + `doc_diversity_ratio`。

### 4.4 Critic

```bash
python scripts/evaluate_rag_agents.py \
  --agent critic \
  --dataset scripts/critic_eval_dataset.sample.jsonl \
  --output logs/critic_eval_report.json
```

关键指标：`hallucination`、`citation_invalid`、`sufficient`、`valid` 的 precision/recall/f1。

### 4.5 一次跑完全部 Agent

```bash
python scripts/evaluate_rag_agents.py \
  --agent all \
  --router-dataset scripts/router_eval_dataset.sample.jsonl \
  --retriever-dataset scripts/retriever_eval_dataset.sample.jsonl \
  --reranker-dataset scripts/reranker_eval_dataset.sample.jsonl \
  --critic-dataset scripts/critic_eval_dataset.sample.jsonl \
  --output logs/rag_agents_eval_all_report.json
```

## 5. 数据集建议

- RAGAS 数据集至少包含：`project_id`、`question`、`expected_chunk_ids`、`reference_answer`。
- Router 数据集包含：`question` + `expected` 路由字段。
- Retriever/Reranker 数据集包含：`project_id`、`question`、`expected_chunk_ids`。
- Critic 数据集包含：`query`、`answer`、`evidence_chunks`、`label`。

## 6. 快速排错

- 如果模型初始化很慢：先用 `--metric-set retrieval` 跑通流程。
- 如果指标全是 0：优先检查 `expected_chunk_ids` 是否和当前项目真实 chunk 对齐。
- 如果路由经常 fallback：检查 Router 提示词和 JSON 输出稳定性。

## 7. 结果解读建议

- 先看整链路：RAGAS 是否达到可用阈值。
- 再看单 Agent：定位瓶颈在 Router、检索、重排还是 Critic。
- 最后回归整链路：验证优化后是否整体提升。
