<template>
  <div class="feature-shell min-h-screen">
    <Header />
    <main class="container mx-auto px-4 md:px-8 pt-28 md:pt-32 pb-16">
      <div class="max-w-5xl mx-auto">
        <p class="badge">功能页4</p>
        <h1 class="title">结果页：结构化报告与未来推演</h1>
        <p class="subtitle">
          输出不是长文本堆砌，而是结构化数据驱动的报告页面；支持条件变更后的推演重算。
        </p>

        <section class="grid md:grid-cols-2 gap-5 mt-8">
          <article class="card">
            <h2>Structured Output</h2>
            <p>基于 Pydantic 约束模型输出字段，生成时间轴、对比表、来源列表等模块化内容。</p>
          </article>
          <article class="card">
            <h2>未来展望推演</h2>
            <p>用户变更关键条件后，系统按推理链重算结论，得到可解释的“如果...那么...”路径。</p>
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
  background: linear-gradient(150deg, #0b1732 0%, #1a2b59 55%, #13234a 100%);
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
