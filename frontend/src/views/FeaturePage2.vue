<template>
  <div class="feature-shell min-h-screen">
    <Header />
    <main class="container mx-auto px-4 md:px-8 pt-28 md:pt-32 pb-16">
      <div class="max-w-5xl mx-auto">
        <p class="badge">功能页2</p>
        <h1 class="title">过程页：多智能体协作执行</h1>
        <p class="subtitle">
          主控 Agent 拆解任务，研究 Agent 并行检索，分析 Agent 汇总推理，通过协议层调用工具并与其他 Agent 协作。
        </p>

        <section class="stack mt-8">
          <article class="card">
            <h2>Multi-Agent + CoT</h2>
            <p>任务分发给历史、现状、趋势三个子 Agent，各自输出思维链过程，最后由主控 Agent 聚合。</p>
          </article>

          <article class="card">
            <h2>MCP + Function Calling</h2>
            <p>通过 MCP 协议连接外部搜索、数据库和文档工具，动态调用接口完成事实采集与证据检索。</p>
          </article>

          <article class="card">
            <h2>A2A 协议协作</h2>
            <p>当分析过程中需要图表生成、补充核验时，Agent 间通过消息协议请求专用能力 Agent 继续处理。</p>
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
  background: linear-gradient(150deg, #0b142b 0%, #1a2554 55%, #111d44 100%);
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

.stack {
  display: grid;
  gap: 1rem;
}

.card {
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 1rem;
  background: rgba(15, 23, 42, 0.56);
  padding: 1.1rem;
}

.card h2 {
  font-size: 1.2rem;
  font-weight: 700;
  color: #7dd3fc;
  margin-bottom: 0.45rem;
}

.card p {
  color: rgba(226, 232, 240, 0.92);
}
</style>
