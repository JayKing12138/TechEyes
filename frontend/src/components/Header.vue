<template>
  <header class="fixed top-0 left-0 right-0 z-50 border-b border-slate-700/40 header-shell">
    <div class="container mx-auto px-4 md:px-8">
      <div class="flex items-center justify-between h-16 md:h-[4.6rem]">
        <!-- Logo -->
        <router-link 
          to="/"
          class="flex items-center gap-3 group"
        >
          <div class="brand-mark" aria-hidden="true">
            <span class="brand-core"></span>
          </div>
          <span class="text-lg md:text-xl font-bold tracking-tight group-hover:text-cyan-300 transition-colors">
            TechEyes
          </span>
        </router-link>

        <!-- Navigation -->
        <nav class="hidden md:flex items-center gap-2">
          <router-link
            v-for="link in navLinks"
            :key="link.label"
            :to="link.to"
            :class="[
              'px-3 py-1.5 rounded-lg text-sm tracking-wide transition-colors',
              isActive(link.to)
                ? 'bg-cyan-500/15 text-cyan-200 border border-cyan-300/40'
                : 'text-slate-300 hover:text-cyan-300'
            ]"
          >
            {{ link.label }}
          </router-link>
        </nav>

        <div class="flex items-center gap-2">
          <a
            href="https://github.com/yourusername/techeyes"
            target="_blank"
            class="hidden md:flex items-center gap-2 px-3 py-2 rounded-xl border border-cyan-200/20 bg-cyan-500/5 hover:bg-cyan-500/15 hover:border-cyan-200/40 transition-colors text-cyan-200"
          >
            GitHub
          </a>

          <router-link
            v-if="!authStore.isLoggedIn"
            to="/auth"
            class="px-3.5 md:px-4 py-2 rounded-xl border border-cyan-200/30 bg-cyan-500/10 hover:bg-cyan-500/20 hover:border-cyan-200/60 transition-colors text-cyan-200"
          >
            登录 / 注册
          </router-link>

          <div v-else class="flex items-center gap-2">
            <span class="user-pill">{{ authStore.username }}</span>
            <button class="logout-btn" @click="handleLogout">登出</button>
          </div>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const navLinks = [
  { label: '首页', to: '/' },
  { label: '智能决策问答', to: '/chat' },
  { label: '项目知识工作台', to: '/projects' },
  { label: '科技新闻雷达', to: '/radar' },
]

const isActive = (path: string) => {
  if (path === '/') {
    return route.path === '/'
  }
  return route.path === path || route.path.startsWith(`${path}/`)
}

const handleLogout = () => {
  authStore.logout()
  router.push('/')
}
</script>

<style scoped>
.header-shell {
  backdrop-filter: blur(14px);
  background: linear-gradient(to right, rgba(7, 18, 40, 0.96), rgba(6, 28, 50, 0.94));
}

.brand-mark {
  position: relative;
  width: 1.85rem;
  height: 1.85rem;
  border-radius: 9999px;
  border: 1px solid rgba(125, 211, 252, 0.55);
  background: radial-gradient(circle at 30% 30%, rgba(56, 189, 248, 0.85), rgba(14, 116, 144, 0.25));
  box-shadow: 0 0 18px rgba(56, 189, 248, 0.45);
}

.brand-core {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0.48rem;
  height: 0.48rem;
  border-radius: 9999px;
  background: #ecfeff;
  transform: translate(-50%, -50%);
}

.user-pill {
  border: 1px solid rgba(103, 232, 249, 0.35);
  border-radius: 9999px;
  padding: 0.36rem 0.62rem;
  color: #cffafe;
  font-size: 0.82rem;
  background: rgba(8, 33, 60, 0.7);
}

.logout-btn {
  border: 1px solid rgba(148, 163, 184, 0.34);
  border-radius: 0.62rem;
  padding: 0.36rem 0.62rem;
  color: #dbeafe;
  background: rgba(15, 23, 42, 0.7);
}

.logout-btn:hover {
  border-color: rgba(125, 211, 252, 0.5);
  color: #ecfeff;
}
</style>

