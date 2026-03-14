# 项目会话与多智能体架构总结

## 1. 会话概览
- 主要目标：实现RAG（检索增强生成）系统的端到端测评（RAGAS）与多智能体分模块测评。
- 用户需求演进：从测评工具开发、文档编写，到多智能体架构的技术解读。

## 2. 技术基础
- **RAGAS**：用于RAG端到端测评，集成于ProjectRAGService，支持多种评测指标。
- **自定义Agent测评**：支持Router、Retriever、Reranker、Critic等Agent的独立测评。
- **ProjectRAGService**：多智能体编排核心，负责缓存管理与Agent调度。
- **缓存体系**：L1（内存）、L2（Redis）、L3（语义）。
- **Python 3.10，conda环境techeyes**。

## 3. 代码与文件结构
- `evaluate_project_rag_ragas.py`：RAGAS测评脚本，已修正SQL参数传递问题。
- `evaluate_rag_agents.py`：多Agent测评脚本，支持四类Agent独立或联合测评。
- `router_eval_dataset.sample.jsonl`等：各Agent测评样例数据集。
- `rag_eval_dataset.sample.jsonl`：RAGAS测评样例数据集。
- `RAG_AGENT_EVALUATION_GUIDE.md`：测评操作文档。
- `project_rag_service.py`：多智能体编排与缓存管理核心。
- `*_agent.py`：各Agent实现，单一职责清晰。

## 4. 问题与解决
- SQLAlchemy参数遗漏导致报错，已修正。
- ProjectRAGService重复初始化，已改为单例。
- RouterAgent JSON解析不稳定，已记录fallback逻辑。

## 5. 进度追踪
- 已完成：RAGAS测评脚本、多Agent测评脚本、样例数据、文档、架构说明。
- 可选后续：如需可视化执行时序图、进一步优化测评脚本。

## 6. 多智能体架构简述
- **ProjectRAGService**负责整体流程编排，调用7个Agent（Router、Planner、Retriever、WebNews、Reranker、Synthesizer、Critic），并管理三层缓存。
- 各Agent职责单一，便于独立测评与调试。
- API入口由`/backend/api/projects_routes.py`暴露，统一调用ProjectRAGService。

## 7. 后续建议
- 如需团队文档或评审，可进一步绘制API→Service→7 Agents→Cache的执行时序图，并标注各阶段输入/输出字段。

---

*本文件由GitHub Copilot自动生成，内容基于2026年3月14日会话历史与代码分析。*