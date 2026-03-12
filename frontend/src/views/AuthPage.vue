<template>
  <div class="min-h-screen techeyes-page-shell auth-shell">
    <Header />

    <main class="container mx-auto px-4 md:px-8 pt-28 md:pt-36 pb-16">
      <section class="auth-card mx-auto">
        <p class="auth-eyebrow">Account Center</p>
        <h1 class="text-3xl md:text-4xl font-black mt-2">欢迎使用 TechEyes</h1>
        <p class="text-slate-300/90 mt-2">注册或登录后可查看历史记录并管理个人会话。</p>

        <div class="auth-tabs mt-6">
          <button
            :class="['auth-tab', mode === 'login' ? 'auth-tab-active' : '']"
            @click="mode = 'login'"
          >
            登录
          </button>
          <button
            :class="['auth-tab', mode === 'register' ? 'auth-tab-active' : '']"
            @click="mode = 'register'"
          >
            注册
          </button>
        </div>

        <form class="mt-5 space-y-4" @submit.prevent="handleSubmit">
          <div>
            <label class="auth-label">用户名</label>
            <input v-model.trim="username" class="auth-input" type="text" placeholder="输入用户名" />
          </div>

          <div>
            <label class="auth-label">密码</label>
            <input v-model="password" class="auth-input" type="password" placeholder="输入密码（至少6位）" />
          </div>

          <p v-if="errorMsg" class="auth-error">{{ errorMsg }}</p>

          <button class="auth-submit" :disabled="submitting">
            {{ submitting ? '提交中...' : mode === 'login' ? '登录' : '注册并登录' }}
          </button>
        </form>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Header from '@/components/Header.vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const mode = ref<'login' | 'register'>('login')
const username = ref('')
const password = ref('')
const errorMsg = ref('')
const submitting = ref(false)

const parseError = (error: any) => {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  return '操作失败，请稍后重试'
}

const handleSubmit = async () => {
  if (!username.value) {
    errorMsg.value = '请输入用户名'
    return
  }
  if (password.value.length < 6) {
    errorMsg.value = '密码至少 6 位'
    return
  }

  submitting.value = true
  errorMsg.value = ''

  try {
    if (mode.value === 'register') {
      await authStore.register(username.value, password.value)
    } else {
      await authStore.login(username.value, password.value)
    }

    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    router.replace(redirect)
  } catch (error: any) {
    errorMsg.value = parseError(error)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.auth-shell {
  color: #dbeafe;
}

.auth-card {
  width: 100%;
  max-width: 34rem;
  border: 1px solid rgba(125, 211, 252, 0.24);
  border-radius: 1rem;
  background: rgba(8, 22, 45, 0.85);
  backdrop-filter: blur(12px);
  padding: 1.2rem 1.25rem;
}

.auth-eyebrow {
  display: inline-block;
  padding: 0.3rem 0.66rem;
  border: 1px solid rgba(103, 232, 249, 0.34);
  border-radius: 9999px;
  color: #9cecff;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.auth-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
}

.auth-tab {
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 0.7rem;
  padding: 0.5rem;
  color: #cbd5e1;
  background: rgba(15, 23, 42, 0.5);
}

.auth-tab-active {
  color: #e0f2fe;
  border-color: rgba(103, 232, 249, 0.5);
  background: rgba(8, 57, 94, 0.55);
}

.auth-label {
  display: block;
  font-size: 0.85rem;
  color: #cbd5e1;
  margin-bottom: 0.35rem;
}

.auth-input {
  width: 100%;
  border: 1px solid rgba(148, 163, 184, 0.34);
  border-radius: 0.7rem;
  background: rgba(7, 17, 36, 0.78);
  color: #e2e8f0;
  padding: 0.6rem 0.75rem;
}

.auth-error {
  color: #fda4af;
  font-size: 0.86rem;
}

.auth-submit {
  width: 100%;
  border: 1px solid rgba(103, 232, 249, 0.5);
  border-radius: 0.75rem;
  background: linear-gradient(135deg, rgba(34, 211, 238, 0.4), rgba(59, 130, 246, 0.5));
  color: #ecfeff;
  font-weight: 700;
  padding: 0.62rem 0.8rem;
}

.auth-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
