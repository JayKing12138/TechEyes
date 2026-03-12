<template>
  <div class="feature-shell min-h-screen">
    <Header />
    <main class="container mx-auto px-4 md:px-8 pt-28 md:pt-32 pb-16">
      <div class="max-w-5xl mx-auto">
        <p class="badge">功能页3</p>
        <h1 class="title">深度分析区：自纠错与记忆系统</h1>
        <p class="subtitle">
          面向“信息冲突”和“会话连续性”，系统会自动反思错误、交叉验证，并维持用户短期与长期偏好记忆。
        </p>

        <section class="grid md:grid-cols-3 gap-4 mt-8">
          <article class="card">
            <h2>Self-Correction</h2>
            <p>发现证据冲突后触发 Reflection 节点，重跑检索并优先采信权威来源。</p>
          </article>
          <article class="card">
            <h2>Memory</h2>
            <p>通过 Checkpointer 记录会话状态，并存储长期偏好实现跨会话连续体验。</p>
          </article>
          <article class="card">
            <h2>RAG</h2>
            <p>将抓取文档向量化入库（ChromaDB），支持后续问题的精准定位与引用。</p>
          </article>
        </section>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import Header from '@/components/Header.vue'
</script>

<style scoped>
.feature-shell {
  background: linear-gradient(140deg, #0a162f 0%, #162a4f 55%, #111f43 100%);
  color: #e2e8f0;
}

.badge {
  display: inline-block;
  border: 1px solid rgba(125, 211, 252, 0.45);
  border-radius: 9999px;
  padding: 0.35rem 0.7rem;
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  color: #a5f3fc;
}

.title {
  font-size: clamp(2rem, 4.5vw, 3.2rem);
  margin-top: 1rem;
  font-weight: 800;
}

.subtitle {
  margin-top: 0.8rem;
  max-width: 56rem;
  color: rgba(226, 232, 240, 0.88);
}

.card {
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 1rem;
  background: rgba(15, 23, 42, 0.56);
  padding: 1rem;
}

.card h2 {
  font-size: 1.1rem;
  font-weight: 700;
  color: #7dd3fc;
  margin-bottom: 0.45rem;
}

.card p {
  font-size: 0.93rem;
  color: rgba(226, 232, 240, 0.92);
}
</style>
