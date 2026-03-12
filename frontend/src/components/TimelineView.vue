<template>
  <div class="space-y-6">
    <div 
      v-for="(event, index) in events"
      :key="index"
      class="flex gap-4 group"
    >
      <!-- Timeline Line -->
      <div class="flex flex-col items-center">
        <div 
          :class="[
            'w-3 h-3 rounded-full border-2 transition-all duration-300',
            'group-hover:scale-150',
            getSignificanceColor(event.significance)
          ]"
        />
        <div 
          v-if="index < events.length - 1"
          class="w-0.5 flex-1 bg-gradient-to-b from-neon-cyan/50 to-transparent"
          style="min-height: 60px"
        />
      </div>

      <!-- Event Content -->
      <div class="flex-1 pb-8">
        <div class="glass-dark p-4 rounded-xl hover:bg-dark-surface transition-colors">
          <!-- Date -->
          <div class="text-sm text-gray-500 mb-1">{{ event.date }}</div>
          
          <!-- Title -->
          <h4 class="text-lg font-semibold mb-2">{{ event.title }}</h4>
          
          <!-- Description -->
          <p class="text-gray-400 text-sm mb-3 line-clamp-3">
            {{ event.description }}
          </p>
          
          <!-- Companies & Significance -->
          <div class="flex items-center justify-between">
            <div class="flex gap-2">
              <span
                v-for="company in event.companies"
                :key="company"
                class="px-2 py-1 bg-neon-cyan/10 text-neon-cyan text-xs rounded"
              >
                {{ company }}
              </span>
            </div>
            <div class="flex gap-1">
              <span 
                v-for="i in event.significance"
                :key="i"
                class="text-yellow-400"
              >
                ⭐
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { TimelineEvent } from '@/types'

interface Props {
  events: TimelineEvent[]
}

defineProps<Props>()

const getSignificanceColor = (significance: number) => {
  if (significance >= 3) return 'border-red-500 bg-red-500'
  if (significance >= 2) return 'border-yellow-500 bg-yellow-500'
  return 'border-blue-500 bg-blue-500'
}
</script>
