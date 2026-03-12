<template>
  <div class="dialog-overlay" @click.self="handleCancel">
    <div class="dialog-box">
      <div class="dialog-header">
        <h2>新建分析项目</h2>
        <button class="close-btn" @click="handleCancel">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div class="dialog-content">
        <form @submit.prevent="handleSubmit">
          <!-- 项目名称 -->
          <div class="form-group">
            <label for="name" class="form-label">项目名称 *</label>
            <input
              id="name"
              v-model="form.name"
              type="text"
              placeholder="如: AI芯片技术现状与前景"
              class="form-input"
              required
            />
          </div>

          <!-- 项目描述 -->
          <div class="form-group">
            <label for="description" class="form-label">项目描述</label>
            <textarea
              id="description"
              v-model="form.description"
              placeholder="简要描述这个项目的目标和范围..."
              class="form-textarea"
              rows="4"
            />
          </div>

          <!-- 领域分类 -->
          <div class="form-group">
            <label for="domain" class="form-label">领域分类 *</label>
            <select v-model="form.domain" id="domain" class="form-select" required>
              <option value="">-- 选择领域 --</option>
              <option value="technology">科技与 IT</option>
              <option value="finance">金融与经济</option>
              <option value="healthcare">医疗与健康</option>
              <option value="energy">能源与环保</option>
              <option value="industry">产业发展</option>
              <option value="other">其他</option>
            </select>
          </div>

          <div class="dialog-footer">
            <button type="button" class="btn-cancel" @click="handleCancel">
              取消
            </button>
            <button type="submit" class="btn-primary" :disabled="!form.name || !form.domain || submitting">
              {{ submitting ? '创建中...' : '创建项目' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  create: [data: any]
  close: []
}>()

const form = ref({
  name: '',
  description: '',
  domain: ''
})

const submitting = ref(false)

const handleSubmit = async () => {
  const payload = {
    name: form.value.name.trim(),
    description: form.value.description.trim(),
    domain: form.value.domain
  }

  if (!payload.name || !payload.domain) {
    return
  }

  submitting.value = true
  try {
    await new Promise(resolve => setTimeout(resolve, 300)) // 模拟提交延迟
    emit('create', {
      name: payload.name,
      description: payload.description,
      domain: payload.domain,
      doc_count: 0,
      conversation_count: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    })
  } finally {
    submitting.value = false
  }
}

const handleCancel = () => {
  emit('close')
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
  max-width: 500px;
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
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e2e8f0;
}

.dialog-header h2 {
  font-size: 1.25rem;
  font-weight: 700;
  color: #1a202c;
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  color: #718096;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 0.375rem;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: #f7fafc;
  color: #2d3748;
}

.dialog-content {
  padding: 2rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-label {
  display: block;
  font-size: 0.95rem;
  font-weight: 600;
  color: #2d3748;
  margin-bottom: 0.5rem;
}

.form-input,
.form-textarea,
.form-select {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 0.5rem;
  font-family: inherit;
  font-size: 0.95rem;
  color: #1a202c;
  background: white;
  transition: all 0.2s ease;
}

.form-input::placeholder,
.form-textarea::placeholder {
  color: #a0aec0;
}

.form-input:focus,
.form-textarea:focus,
.form-select:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.form-textarea {
  resize: vertical;
}

.dialog-footer {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}

.btn-primary,
.btn-cancel {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-cancel {
  background: white;
  border: 1px solid #e2e8f0;
  color: #4a5568;
}

.btn-cancel:hover {
  background: #f7fafc;
  border-color: #cbd5e0;
}
</style>
