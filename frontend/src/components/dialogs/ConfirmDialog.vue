<template>
  <div class="dialog-overlay" @click.self="handleCancel">
    <div class="dialog-box">
      <div class="dialog-header danger">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4v.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <h2>{{ title }}</h2>
      </div>

      <div class="dialog-content">
        <p>{{ message }}</p>
      </div>

      <div class="dialog-footer">
        <button class="btn-secondary" @click="handleCancel">
          取消
        </button>
        <button class="btn-danger" @click="handleConfirm" :disabled="confirming">
          {{ confirming ? '确认中...' : '确认删除' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  title: string
  message: string
}>()

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()

const confirming = ref(false)

const handleConfirm = async () => {
  confirming.value = true
  try {
    await new Promise(resolve => setTimeout(resolve, 300))
    emit('confirm')
  } finally {
    confirming.value = false
  }
}

const handleCancel = () => {
  emit('cancel')
}
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.dialog-box {
  background: white;
  border-radius: 0.75rem;
  box-shadow: 0 20px 25px rgba(0, 0, 0, 0.15);
  width: 90%;
  max-width: 400px;
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.dialog-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.5rem;
  border-bottom: 1px solid #e2e8f0;
}

.dialog-header.danger {
  color: #e53e3e;
}

.dialog-header h2 {
  font-size: 1.15rem;
  font-weight: 700;
  color: inherit;
  margin: 0;
}

.dialog-content {
  padding: 1.5rem;
}

.dialog-content p {
  margin: 0;
  color: #4a5568;
  line-height: 1.6;
  font-size: 0.95rem;
}

.dialog-footer {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  padding: 1.5rem;
  border-top: 1px solid #e2e8f0;
}

.btn-secondary,
.btn-danger {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-secondary {
  background: white;
  border: 1px solid #e2e8f0;
  color: #4a5568;
}

.btn-secondary:hover {
  background: #f7fafc;
  border-color: #cbd5e0;
}

.btn-danger {
  background: #e53e3e;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #c53030;
  transform: translateY(-2px);
}

.btn-danger:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
