<template>
  <div class="relative">
    <div
      :class="[
        'search-shell flex items-center gap-4 px-4 md:px-5 py-3.5 md:py-4 rounded-2xl transition-all duration-300',
        isFocused ? 'ring-2 ring-cyan-300/70 shadow-lg shadow-cyan-500/20' : '',
        dragActive ? 'drag-active' : ''
      ]"
      @dragover.prevent="dragActive = true"
      @dragleave.prevent="dragActive = false"
      @drop.prevent="handleDrop"
    >
      <div
        :class="[
          'search-glyph transition-transform duration-500',
          loading ? 'animate-spin' : ''
        ]"
      ></div>

      <!-- Input -->
      <input
        v-model="query"
        type="text"
        placeholder="输入你想分析的科技话题，例如：OpenAI vs Anthropic"
        :disabled="loading"
        @focus="isFocused = true"
        @blur="isFocused = false"
        @keyup.enter="handleSubmit"
        class="flex-1 bg-transparent outline-none text-base md:text-lg placeholder-slate-400 disabled:opacity-50"
      />

      <!-- Submit Button -->
      <button
        @click="handleSubmit"
        :disabled="!query.trim() || loading"
        :class="[
          'px-5 md:px-6 py-2.5 md:py-3 rounded-xl font-semibold tracking-wide transition-all duration-300',
          'bg-gradient-to-r from-cyan-400 to-blue-500 text-slate-950',
          'hover:shadow-lg hover:shadow-cyan-400/30 hover:-translate-y-0.5',
          'disabled:opacity-50 disabled:cursor-not-allowed'
        ]"
      >
        {{ loading ? '分析中...' : '开始分析' }}
      </button>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface Props {
  loading?: boolean
}

interface Emits {
  (e: 'submit', query: string): void
  (e: 'attach', file: File): void
}

defineProps<Props>()
const emit = defineEmits<Emits>()

const query = ref('')
const isFocused = ref(false)
const dragActive = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)

const handleSubmit = () => {
  if (query.value.trim()) {
    emit('submit', query.value.trim())
  }
}

const emitFile = (file: File | null) => {
  if (!file) return
  emit('attach', file)
}

const openFilePicker = () => {
  fileInputRef.value?.click()
}

const handleFilePick = (event: Event) => {
  const target = event.target as HTMLInputElement
  emitFile(target.files?.[0] || null)
}

const handleDrop = (event: DragEvent) => {
  dragActive.value = false
  emitFile(event.dataTransfer?.files?.[0] || null)
}
</script>

<style scoped>
.search-shell {
  border: 1px solid rgba(125, 211, 252, 0.25);
  background: linear-gradient(155deg, rgba(15, 32, 64, 0.82), rgba(17, 36, 73, 0.62));
  backdrop-filter: blur(10px);
}

.drag-active {
  border-color: rgba(103, 232, 249, 0.78);
  box-shadow: 0 0 0 2px rgba(103, 232, 249, 0.35);
}

.search-glyph {
  width: 1.2rem;
  height: 1.2rem;
  border-radius: 9999px;
  border: 2px solid rgba(103, 232, 249, 0.85);
  position: relative;
}

.search-glyph::after {
  content: '';
  position: absolute;
  right: -0.35rem;
  bottom: -0.32rem;
  width: 0.44rem;
  height: 2px;
  transform: rotate(40deg);
  transform-origin: left center;
  background: rgba(103, 232, 249, 0.9);
  border-radius: 9999px;
}

.attach-btn {
  position: relative;
  border: 1px solid rgba(125, 211, 252, 0.36);
  border-radius: 0.7rem;
  width: 2.35rem;
  height: 2.35rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(10, 26, 48, 0.86);
  background-image: url('../images/上传文件.png');
  background-position: center;
  background-repeat: no-repeat;
  background-size: 72%;
}

.attach-btn:hover {
  border-color: rgba(125, 211, 252, 0.72);
  background-color: rgba(14, 42, 73, 0.95);
}
</style>
