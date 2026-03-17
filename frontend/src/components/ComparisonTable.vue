<template>
  <div class="space-y-6">
    <div 
      v-for="(comparison, index) in comparisons"
      :key="index"
      class="glass-dark p-6 rounded-xl"
    >
      <!-- Dimension Header -->
      <div class="mb-4">
        <h4 class="text-lg font-semibold mb-1">{{ comparison.dimension }}</h4>
        <p class="text-sm text-gray-400">{{ comparison.description }}</p>
      </div>

      <!-- Company Comparisons -->
      <div class="space-y-4">
        <div 
          v-for="(comp, idx) in comparison.company_comparisons"
          :key="idx"
          class="bg-dark-surface p-4 rounded-lg"
        >
          <div class="flex items-center justify-between mb-3">
            <span class="font-medium">{{ comp.company }}</span>
            <span class="text-neon-cyan font-bold">{{ comp.score }}%</span>
          </div>
          
          <!-- Progress Bar -->
          <div class="w-full bg-dark-bg rounded-full h-2 mb-3 overflow-hidden">
            <div 
              class="h-full bg-gradient-to-r from-neon-cyan to-neon-purple transition-all duration-1000 ease-out"
              :style="{ 
                width: `${comp.score}%`,
                transitionDelay: `${idx * 100}ms`
              }"
            />
          </div>

          <!-- Value & Analysis -->
          <div class="space-y-2 text-sm">
            <p class="text-gray-400">
              <strong class="text-white">数据:</strong> {{ comp.value }}
            </p>
            <p class="text-gray-400">
              <strong class="text-white">分析:</strong> {{ comp.analysis }}
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ComparisonData } from '@/types'

interface Props {
  comparisons: ComparisonData[]
}

defineProps<Props>()
</script>
