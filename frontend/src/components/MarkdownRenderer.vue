<template>
  <div class="markdown-content" v-html="renderedHtml" @click="handleContentClick"></div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps<{
  content: string
  meta?: Record<string, any>
}>()

const emit = defineEmits<{
  (e: 'citation-click', refIndex: number): void
}>()

// 简单配置
marked.setOptions({
  breaks: true,
  gfm: true,
})

const escapeHtml = (value: string) =>
  value
    .split('&').join('&amp;')
    .split('<').join('&lt;')
    .split('>').join('&gt;')
    .split('"').join('&quot;')
    .split("'").join('&#39;')

const extractSourceMap = (content: string, meta?: Record<string, any>) => {
  const sourceMap = new Map<number, string>()

  const fromMeta = meta?.sources || meta?.references
  if (Array.isArray(fromMeta)) {
    fromMeta.forEach((item: any, idx: number) => {
      const title = item?.title || item?.source || `来源 ${idx + 1}`
      const url = item?.url ? ` (${item.url})` : ''
      sourceMap.set(idx + 1, `${title}${url}`)
    })
  }

  const docRefs = meta?.docRefs
  if (Array.isArray(docRefs)) {
    docRefs.forEach((item: any) => {
      const idx = Number(item?.refIndex)
      if (!idx) return
      const title = item?.filename || `文档 ${idx}`
      const hint = item?.chunkIndex !== undefined ? `（第 ${Number(item.chunkIndex) + 1} 段）` : ''
      sourceMap.set(idx, `${title}${hint}`)
    })
  }

  const lines = (content || '').split('\n')
  for (const line of lines) {
    const m1 = line.match(/^\s*\[(\d+)\]\s*[:：\-]?\s*(.+)$/)
    const m2 = line.match(/^\s*【\s*来源\s*(\d+)\s*】\s*[:：\-]?\s*(.+)$/i)
    const m3 = line.match(/^\s*来源\s*(\d+)\s*[:：\-]\s*(.+)$/i)
    const matched = m1 || m2 || m3
    if (matched) {
      const idx = Number(matched[1])
      const text = matched[2]?.trim()
      if (idx > 0 && text) {
        sourceMap.set(idx, text)
      }
    }
  }

  return sourceMap
}

const withCitationTooltip = (html: string, sourceMap: Map<number, string>) => {
  return html.replace(/(\[文档(\d+)\]|\[(\d+)\]|【\s*来源\s*(\d+)\s*】|来源\s*(\d+))/g, (full, _a, docNum, b, c, d) => {
    const idx = Number(docNum || b || c || d || 0)
    if (!idx) return full

    const source = sourceMap.get(idx) || `来源 ${idx}`
    const colorIndex = ((idx - 1) % 6) + 1
    const isDocRef = Boolean(docNum)
    const display = isDocRef ? String(idx) : full
    const shapeClass = isDocRef ? 'citation-circle' : ''
    return `<span class="citation-chip ${shapeClass} citation-color-${colorIndex}" data-source="${escapeHtml(source)}" data-ref-index="${idx}">${display}<span class="citation-tooltip">${escapeHtml(source)}</span></span>`
  })
}

const handleContentClick = (event: MouseEvent) => {
  const target = event.target as HTMLElement | null
  if (!target) return

  const chip = target.closest('.citation-chip') as HTMLElement | null
  if (!chip) return

  const refIndex = Number(chip.dataset.refIndex || 0)
  if (!refIndex) return

  event.preventDefault()
  emit('citation-click', refIndex)
}

const withKeyInfoHighlight = (html: string) => {
  return html.replace(
    /(^|[>\s（(])((?:\d+(?:\.\d+)?%|\d+(?:\.\d+)?(?:亿|万|元|美元|人|家|年|月|天)))(?=([\s<）),，。；;！？!]))/g,
    '$1<span class="key-info">$2</span>',
  )
}

const renderedHtml = computed(() => {
  try {
    const raw = String(marked.parse(props.content || ''))
    const sourceMap = extractSourceMap(props.content || '', props.meta)
    const withTooltip = withCitationTooltip(raw, sourceMap)
    return withKeyInfoHighlight(withTooltip)
  } catch (err) {
    console.error('Markdown parse error:', err)
    return props.content
  }
})
</script>

<style scoped>
.markdown-content {
  color: inherit;
  line-height: 1.6;
}

.markdown-content :deep(p) {
  margin: 0.5em 0;
}

.markdown-content :deep(code) {
  background: rgba(110, 118, 129, 0.2);
  padding: 0.2em 0.4em;
  border-radius: 3px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 0.9em;
}

.markdown-content :deep(pre) {
  background: #1e1e1e;
  padding: 1em;
  border-radius: 6px;
  overflow-x: auto;
  margin: 0.8em 0;
}

.markdown-content :deep(pre code) {
  background: transparent;
  padding: 0;
  color: #d4d4d4;
  font-size: 0.92em;
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3) {
  margin: 1em 0 0.5em 0;
  font-weight: 600;
}

.markdown-content :deep(h1) {
  font-size: 1.5em;
  border-bottom: 1px solid rgba(148, 163, 184, 0.3);
  padding-bottom: 0.3em;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin: 0.5em 0;
  padding-left: 2em;
}

.markdown-content :deep(blockquote) {
  border-left: 3px solid rgba(59, 130, 246, 0.5);
  padding-left: 1em;
  margin: 0.8em 0;
}

.markdown-content :deep(a) {
  color: #60a5fa;
}

.markdown-content :deep(.key-info) {
  color: #fbbf24;
  font-weight: 700;
  background: linear-gradient(90deg, rgba(245, 158, 11, 0.18), rgba(16, 185, 129, 0.16));
  border-radius: 0.35rem;
  padding: 0.02rem 0.24rem;
}

.markdown-content :deep(.citation-chip) {
  position: relative;
  display: inline-flex;
  align-items: center;
  margin: 0 0.15rem;
  padding: 0.05rem 0.4rem;
  border-radius: 999px;
  font-size: 0.78em;
  font-weight: 700;
  line-height: 1.25;
  cursor: help;
  border: 1px solid transparent;
}

.markdown-content :deep(.citation-circle) {
  width: 1.45rem;
  height: 1.45rem;
  min-width: 1.45rem;
  padding: 0;
  justify-content: center;
  border-radius: 999px;
  font-size: 0.82em;
  vertical-align: middle;
  cursor: pointer;
}

.markdown-content :deep(.citation-tooltip) {
  position: absolute;
  left: 50%;
  top: calc(100% + 8px);
  transform: translateX(-50%);
  min-width: 220px;
  max-width: 360px;
  background: rgba(5, 18, 33, 0.96);
  border: 1px solid rgba(148, 163, 184, 0.35);
  color: #e2e8f0;
  border-radius: 0.65rem;
  padding: 0.45rem 0.62rem;
  font-size: 0.78rem;
  font-weight: 500;
  line-height: 1.4;
  box-shadow: 0 12px 30px rgba(2, 6, 23, 0.45);
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transition: opacity 0.16s ease;
  z-index: 20;
  white-space: normal;
}

.markdown-content :deep(.citation-chip:hover .citation-tooltip) {
  opacity: 1;
  visibility: visible;
}

.markdown-content :deep(.citation-color-1) {
  color: #fb7185;
  background: rgba(251, 113, 133, 0.14);
  border-color: rgba(251, 113, 133, 0.45);
}

.markdown-content :deep(.citation-color-2) {
  color: #22d3ee;
  background: rgba(34, 211, 238, 0.14);
  border-color: rgba(34, 211, 238, 0.45);
}

.markdown-content :deep(.citation-color-3) {
  color: #34d399;
  background: rgba(52, 211, 153, 0.14);
  border-color: rgba(52, 211, 153, 0.45);
}

.markdown-content :deep(.citation-color-4) {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.14);
  border-color: rgba(245, 158, 11, 0.45);
}

.markdown-content :deep(.citation-color-5) {
  color: #a78bfa;
  background: rgba(167, 139, 250, 0.14);
  border-color: rgba(167, 139, 250, 0.45);
}

.markdown-content :deep(.citation-color-6) {
  color: #38bdf8;
  background: rgba(56, 189, 248, 0.14);
  border-color: rgba(56, 189, 248, 0.45);
}

.markdown-content :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 1em 0;
}

.markdown-content :deep(table th),
.markdown-content :deep(table td) {
  border: 1px solid rgba(148, 163, 184, 0.3);
  padding: 0.5em 0.8em;
}

.markdown-content :deep(table th) {
  background: rgba(59, 130, 246, 0.15);
  font-weight: 600;
}
</style>
