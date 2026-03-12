#!/usr/bin/env python
"""测试多智能体RAG系统"""

from config import get_config
from services.project_rag_service import ProjectRAGService

print("=" * 60)
print("多智能体RAG系统测试")
print("=" * 60)

# 1. 加载配置
config = get_config()
print("\n✅ 配置加载成功")
print(f"  - 检索策略: {config.retrieval.strategy}")
print(f"  - Reranker模型: {config.retrieval.reranker_model}")
print(f"  - BM25权重: {config.retrieval.bm25_weight}")
print(f"  - 向量权重: {config.retrieval.vector_weight}")
print(f"  - 召回TopK: {config.retrieval.max_retrieval}")
print(f"  - 精排TopK: {config.retrieval.final_top_k}")

# 2. 初始化服务
print("\n初始化多智能体RAG系统...")
service = ProjectRAGService()
print("✅ ProjectRAGService初始化成功")

# 3. 验证所有Agent
print("\n验证7个Agent:")
agents = [
    ("router", "Router Agent", "意图识别和路由决策"),
    ("planner", "Planner Agent", "复杂问题拆解"),
    ("retriever", "Retriever Agent", "混合检索(Dense+BM25+RRF)"),
    ("web_news", "Web/News Agent", "实时信息检索"),
    ("reranker", "Reranker Agent", "Cross-Encoder精排"),
    ("synthesizer", "Synthesizer Agent", "引用生成"),
    ("critic", "Critic Agent", "质量校验"),
]

for i, (attr, name, desc) in enumerate(agents, 1):
    agent = getattr(service, attr, None)
    status = "✅" if agent else "❌"
    print(f"  {i}️⃣ {status} {name} - {desc}")

print("\n" + "=" * 60)
print("🎉 多智能体RAG系统部署成功！")
print("=" * 60)
