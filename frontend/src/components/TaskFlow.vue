<template>
  <div class="space-y-4">
    <!-- Summary Stats -->
    <div class="grid grid-cols-3 gap-3 mb-6">
      <div class="text-center bg-dark-surface p-3 rounded-lg">
        <div class="text-xl font-bold text-green-400">{{ completedCount }}</div>
        <div class="text-xs text-gray-400">已完成</div>
      </div>
      <div class="text-center bg-dark-surface p-3 rounded-lg">
        <div class="text-xl font-bold text-yellow-400">{{ runningCount }}</div>
        <div class="text-xs text-gray-400">进行中</div>
      </div>
      <div class="text-center bg-dark-surface p-3 rounded-lg">
        <div class="text-xl font-bold text-gray-400">{{ pendingCount }}</div>
        <div class="text-xs text-ray-400">待处理</div>
      </div>
    </div>

    <!-- Task List -->
    <div class="space-y-3">
      <div
        v-for="task in tasks"
        :key="task.id"
        :class="[
          'p-4 rounded-xl border-2 transition-all duration-300',
          getTaskClass(task.status)
        ]"
      >
        <!-- Task Header -->
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center gap-2">
            <span class="text-lg">{{ getStatusIcon(task.status) }}</span>
            <span class="font-medium">{{ task.name }}</span>
          </div>
          <span class="text-xs text-gray-500">{{ task.agent }}</span>
        </div>

        <!-- Task Description -->
        <p class="text-sm text-gray-400 mb-3">{{ task.description }}</p>

        <!-- Progress Bar for Running -->
        <div v-if="task.status === 'running'" class="mb-2">
          <div class="w-full bg-dark-bg rounded-full h-1.5">
            <div 
              class="h-full bg-yellow-400 rounded-full animate-pulse"
              :style="{ width: '60%' }"
            />
          </div>
        </div>

        <!-- Output for Completed -->
        <div 
          v-if="task.status === 'completed' && task.output"
          class="mt-2 bg-dark-bg p-3 rounded-lg"
        >
          <p class="text-xs text-gray-300 line-clamp-2">
            {{ task.output }}
          </p>
        </div>

        <!-- Execution Time -->
        <div v-if="task.execution_time" class="text-xs text-gray-500 mt-2">
          耗时: {{ task.execution_time }}s
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TaskNode } from '@/types'

interface Props {
  tasks: TaskNode[]
}

const props = defineProps<Props>()

const completedCount = computed(() => 
  props.tasks.filter(t => t.status === 'completed').length
)
const runningCount = computed(() => 
  props.tasks.filter(t => t.status === 'running').length
)
const pendingCount = computed(() => 
  props.tasks.filter(t => t.status === 'pending').length
)

const getStatusIcon = (status: string) => {
  const icons: Record<string, string> = {
    pending: '⏸️',
    running: '▶️',
    completed: '✅',
    error: '❌',
  }
  return icons[status] || '❓'
}

const getTaskClass = (status: string) => {
  const classes: Record<string, string> = {
    pending: 'border-gray-600 bg-dark-surface/50',
    running: 'border-yellow-500 bg-yellow-500/5',
    completed: 'border-green-500 bg-green-500/5',
    error: 'border-red-500 bg-red-500/5',
  }
  return classes[status] || ''
}
</script>
