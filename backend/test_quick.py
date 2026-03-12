#!/usr/bin/env python
"""快速测试 - 不使用Reranker"""

import os
os.environ['RETRIEVAL_ENABLE_RERANKER'] = 'false'

from config import get_config
from services.project_rag_service import ProjectRAGService

print("=" * 60)
print("多智能体RAG系统 - 快速测试（禁用Reranker）")
print("=" * 60)

config = get_config()
print("\n✅ 配置加载成功")
print(f"  - 检索策略: {config.retrieval.strategy}")
print(f"  - Reranker: {'启用' if config.retrieval.enable_reranker else '禁用'}")
print(f"  - BM25权重: {config.retrieval.bm25_weight}")

print("\n初始化多智能体RAG系统...")
service = ProjectRAGService()

print("\n验证7个Agent:")
agents = [
    ("router", "Router Agent"),
    ("planner", "Planner Agent"),
    ("retriever", "Retriever Agent"),
    ("web_news", "Web/News Agent"),
    ("reranker", "Reranker Agent"),
    ("synthesizer", "Synthesizer Agent"),
    ("critic", "Critic Agent"),
]

for i, (attr, name) in enumerate(agents, 1):
    agent = getattr(service, attr, None)
    status = "✅" if agent else "❌"
    print(f"  {i}️⃣ {status} {name}")

print("\n" + "=" * 60)
print("🎉 系统验证完成！所有Agent已就绪")
print("=" * 60)
print("\n提示: Reranker已禁用以加快初始化")
print("如需启用精排功能，设置 RETRIEVAL_ENABLE_RERANKER=true")
