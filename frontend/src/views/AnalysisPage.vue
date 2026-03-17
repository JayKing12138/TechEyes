<template>
  <div class="min-h-screen techeyes-page-shell analysis-shell">
    <Header />
    
    <main class="container mx-auto px-4 pt-24 pb-12">
      <!-- Header -->
      <div class="mb-8">
        <p class="analysis-eyebrow">Analysis Runtime</p>
        <h1 class="text-3xl font-bold mb-2 analysis-title">实时分析进度</h1>
      </div>

      <!-- Progress Bar -->
      <div class="glass-dark p-6 rounded-2xl mb-8 techeyes-panel-soft">
        <div class="flex justify-between items-center mb-2">
          <span class="text-sm font-medium">总体进度</span>
          <span class="text-sm text-neon-cyan">{{ progress }}%</span>
        </div>
        <div class="w-full bg-dark-surface rounded-full h-3 overflow-hidden">
          <div 
            class="h-full bg-gradient-to-r from-neon-cyan to-neon-purple transition-all duration-500"
            :style="{ width: `${progress}%` }"
          />
        </div>
        <p class="text-sm text-gray-400 mt-2">{{ currentStep }}</p>
      </div>

      <!-- Split Layout -->
      <div class="grid md:grid-cols-2 gap-6">
        <!-- Left: Task Flow -->
        <div class="glass-dark p-6 rounded-2xl techeyes-panel-soft">
          <h2 class="text-xl font-bold mb-4">🔄 任务流程</h2>
          <TaskFlow :tasks="tasks" />
        </div>

        <!-- Right: Real-time Output -->
        <div class="glass-dark p-6 rounded-2xl techeyes-panel-soft">
          <h2 class="text-xl font-bold mb-4">📡 实时输出</h2>
          <div 
            ref="outputRef"
            class="analysis-output rounded-lg p-4 h-[500px] overflow-y-auto font-mono text-sm"
          >
            <div 
              v-for="(log, index) in logs"
              :key="index"
              class="mb-2 text-gray-300"
            >
              <span class="text-gray-500">[{{ log.time }}]</span>
              {{ log.message }}
            </div>
          </div>
        </div>
      </div>

      <!-- Cancel Button -->
      <div class="mt-8 text-center">
        <button
          v-if="status === 'running'"
          @click="handleCancel"
          class="px-6 py-3 bg-red-500 hover:bg-red-600 rounded-lg font-medium transition-colors"
        >
          ❌ 取消分析
        </button>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAnalysisStore } from '@/stores/analysis'
import Header from '@/components/Header.vue'
import TaskFlow from '@/components/TaskFlow.vue'
import { subscribeToAnalysis, cancelAnalysis } from '@/services/api'

interface Props {
  sessionId: string
}

const props = defineProps<Props>()
const router = useRouter()
const store = useAnalysisStore()

const logs = ref<Array<{ time: string; message: string }>>([])
const outputRef = ref<HTMLElement | null>(null)
let eventSource: EventSource | null = null

const progress = computed(() => store.analysisState.progress)
const status = computed(() => store.analysisState.status)
const currentStep = computed(() => store.analysisState.current_step)
const tasks = computed(() => store.analysisState.tasks)

const addLog = (message: string) => {
  const time = new Date().toLocaleTimeString()
  logs.value.push({ time, message })
  
  nextTick(() => {
    if (outputRef.value) {
      outputRef.value.scrollTop = outputRef.value.scrollHeight
    }
  })
}

const handleCancel = async () => {
  try {
    await cancelAnalysis(props.sessionId)
    addLog('❌ 用户取消了分析')
    if (eventSource) {
      eventSource.close()
    }
    router.push('/')
  } catch (error) {
    console.error('取消失败:', error)
  }
}

onMounted(() => {
  store.setAnalysisState({ session_id: props.sessionId })
  addLog('🚀 开始分析任务')
  
  // 订阅实时更新
  eventSource = subscribeToAnalysis(props.sessionId, (data) => {
    if (data.type === 'progress') {
      store.updateProgress(data.progress)
      addLog(`📊 进度更新: ${data.progress}%`)
    } else if (data.type === 'step_update') {
      // 处理步骤更新
      store.setAnalysisState({ current_step: data.message })
      addLog(`📝 ${data.message}`)
    } else if (data.type === 'task_start') {
      store.updateTask(data.task_id, { status: 'running' })
      addLog(`▶️ 任务开始: ${data.task_name}`)
    } else if (data.type === 'task_complete') {
      store.updateTask(data.task_id, { 
        status: 'completed',
        output: data.output 
      })
      addLog(`✅ 任务完成: ${data.task_name}`)
    } else if (data.type === 'completed') {
      store.setAnalysisState({ status: 'completed', progress: 100 })
      addLog('🎉 分析完成！正在跳转...')
      
      setTimeout(() => {
        router.push(`/result/${props.sessionId}`)
      }, 1500)
    } else if (data.type === 'error') {
      store.setAnalysisState({ status: 'error' })
      addLog(`❌ 错误: ${data.errors || '未知错误'}`)
    }
  })
})

onUnmounted(() => {
  if (eventSource) {
    eventSource.close()
  }
})
</script>

<style scoped>
.analysis-shell {
  color: var(--te-text-main);
}

.analysis-eyebrow {
  display: inline-block;
  margin-bottom: 0.55rem;
  padding: 0.3rem 0.65rem;
  border: 1px solid rgba(103, 232, 249, 0.36);
  border-radius: 9999px;
  background: rgba(9, 29, 58, 0.7);
  color: #9fe7ff;
  font-size: 0.7rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.analysis-title {
  color: #dff8ff;
}

.analysis-output {
  background: rgba(5, 16, 38, 0.88);
  border: 1px solid rgba(125, 211, 252, 0.18);
}
</style>
