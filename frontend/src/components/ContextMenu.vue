<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="context-menu"
      :style="{ left: `${x}px`, top: `${y}px` }"
      @click.stop
    >
      <div
        v-for="item in menuItems"
        :key="item.id"
        class="menu-item"
        :class="{ 'menu-item-disabled': item.disabled }"
        @click="handleItemClick(item)"
      >
        <component :is="item.icon" v-if="item.icon" class="menu-icon" />
        <span class="menu-label">{{ item.label }}</span>
        <span v-if="item.shortcut" class="menu-shortcut">{{ item.shortcut }}</span>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, watch, onUnmounted } from 'vue'

interface MenuItem {
  id: string
  label: string
  icon?: any
  shortcut?: string
  disabled?: boolean
  action?: () => void
}

interface Props {
  visible: boolean
  x: number
  y: number
  items: MenuItem[]
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'select', item: MenuItem): void
}>()

const menuItems = computed(() => props.items)

const handleItemClick = (item: MenuItem) => {
  if (item.disabled) return
  
  emit('select', item)
  emit('close')
}

const handleClickOutside = (event: MouseEvent) => {
  if (props.visible) {
    emit('close')
  }
}

watch(() => props.visible, (newVal) => {
  if (newVal) {
    setTimeout(() => {
      document.addEventListener('click', handleClickOutside)
    }, 0)
  } else {
    document.removeEventListener('click', handleClickOutside)
  }
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.context-menu {
  position: fixed;
  background: rgba(15, 23, 42, 0.95);
  border: 1px solid rgba(125, 211, 252, 0.3);
  border-radius: 0.5rem;
  padding: 0.5rem 0;
  min-width: 180px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(10px);
  z-index: 10000;
  animation: fadeIn 0.15s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 1rem;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}

.menu-item:hover:not(.menu-item-disabled) {
  background: rgba(125, 211, 252, 0.1);
}

.menu-item-disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.menu-icon {
  width: 1rem;
  height: 1rem;
  color: rgba(125, 211, 252, 0.8);
}

.menu-label {
  flex: 1;
  color: #e2e8f0;
  font-size: 0.875rem;
  font-weight: 500;
}

.menu-shortcut {
  color: rgba(226, 232, 240, 0.5);
  font-size: 0.75rem;
  font-weight: 500;
}
</style>
