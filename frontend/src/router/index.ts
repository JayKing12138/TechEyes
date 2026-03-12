import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Landing',
    component: () => import('@/views/LandingPage.vue'),
  },
  {
    path: '/feature-1',
    name: 'Feature1',
    component: () => import('@/views/FeaturePage1.vue'),
  },
  {
    path: '/feature-2',
    name: 'Feature2',
    component: () => import('@/views/FeaturePage2.vue'),
  },
  {
    path: '/feature-3',
    name: 'Feature3',
    component: () => import('@/views/FeaturePage3.vue'),
  },
  {
    path: '/feature-4',
    name: 'Feature4',
    component: () => import('@/views/FeaturePage4.vue'),
  },
  {
    path: '/auth',
    name: 'Auth',
    component: () => import('@/views/AuthPage.vue'),
    meta: { requiresGuest: true },
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('@/views/HistoryPage.vue'),
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/views/ChatPage.vue'),
  },
  {
    path: '/projects',
    name: 'ProjectList',
    component: () => import('@/views/ProjectListPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/projects/:id',
    name: 'ProjectDetail',
    component: () => import('@/views/ProjectDetailPage.vue'),
    props: true,
    meta: { requiresAuth: true },
  },
  {
    path: '/analysis/:sessionId',
    name: 'Analysis',
    component: () => import('@/views/AnalysisPage.vue'),
    props: true,
  },
  {
    path: '/result/:sessionId',
    name: 'Result',
    component: () => import('@/views/ResultPage.vue'),
    props: true,
  },
  {
    path: '/radar',
    name: 'Radar',
    component: () => import('@/views/RadarPage.vue'),
  },
  {
    path: '/radar/news/:id',
    name: 'RadarNewsDetail',
    component: () => import('@/views/RadarNewsDetailPage.vue'),
    props: true,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const token = localStorage.getItem('techeyes_auth_token')
  const isLoggedIn = Boolean(token)

  if (to.meta.requiresAuth && !isLoggedIn) {
    return `/auth?redirect=${encodeURIComponent(to.fullPath)}`
  }

  if (to.meta.requiresGuest && isLoggedIn) {
    return '/'
  }

  return true
})

export default router
