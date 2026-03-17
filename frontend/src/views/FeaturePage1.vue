<template>
  <div class="feature-shell min-h-screen">
    <Header />
    <main class="container mx-auto px-4 md:px-8 pt-28 md:pt-32 pb-16">
      <div class="max-w-5xl mx-auto">
        <p class="badge">功能页1</p>
        <h1 class="title">启动页：定标与意图捕捉</h1>
        <p class="subtitle">
          用户输入分析需求后，系统先进行语义缓存命中，再通过上下文工程补全行业背景和时效信息。
        </p>

        <section class="grid md:grid-cols-2 gap-5 mt-8">
          <article class="card">
            <h2>语义缓存 (Semantic Cache)</h2>
            <p>在 Redis 中检索相似问题，如果命中则快速返回分析框架，减少模型调用成本并提升首屏响应速度。</p>
            <ul>
              <li>相似查询秒级返回</li>
              <li>节省推理调用成本</li>
              <li>保证热门主题一致性</li>
            </ul>
          </article>

          <article class="card">
            <h2>上下文工程 (Context Engineering)</h2>
            <p>将用户自然语言转为结构化分析指令，自动补全日期、行业基准、关注公司等上下文字段。</p>
            <ul>
              <li>System Prompt 模板化注入</li>
              <li>结构化请求构建</li>
              <li>分析边界与目标约束</li>
            </ul>
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
  background: linear-gradient(140deg, #08162f 0%, #0f2347 52%, #0d1a3d 100%);
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
  background: rgba(15, 23, 42, 0.5);
  padding: 1.1rem;
}

.card h2 {
  font-size: 1.2rem;
  font-weight: 700;
  margin-bottom: 0.6rem;
  color: #7dd3fc;
}

.card p {
  color: rgba(226, 232, 240, 0.9);
}

.card ul {
  margin-top: 0.7rem;
  font-size: 0.9rem;
  color: #cbd5e1;
  padding-left: 1rem;
}

.card li + li {
  margin-top: 0.35rem;
}
</style>
