import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/auth/LoginView.vue'),
      meta: { title: 'Login', requiresAuth: false },
    },
    {
      path: '/',
      component: () => import('@/components/layout/AppLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'home',
          component: () => import('@/views/HomeView.vue'),
          meta: { title: 'Home' },
        },
        {
          path: 'system/aimodel',
          name: 'aimodel',
          component: () => import('@/views/system/aimodel/AiModelView.vue'),
          meta: { title: 'AI Models', icon: 'robot', requiresAdmin: true },
        },
        {
          path: 'system/users',
          name: 'users',
          component: () => import('@/views/system/users/UserView.vue'),
          meta: { title: 'User Management', icon: 'people', requiresAdmin: true },
        },
        {
          path: 'system/workspace',
          name: 'workspace',
          component: () => import('@/views/system/workspace/WorkspaceView.vue'),
          meta: { title: 'Workspace', icon: 'folder', requiresAdmin: true },
        },
        {
          path: 'system/mcpserver',
          name: 'mcpserver',
          component: () => import('@/views/system/mcpserver/McpServerView.vue'),
          meta: { title: 'MCP Servers', icon: 'server', requiresAdmin: true },
        },
      ],
    },
  ],
})

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()
  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth !== false)
  const requiresAdmin = to.matched.some((record) => record.meta.requiresAdmin === true)

  if (requiresAuth && !authStore.isAuthenticated) {
    next({ path: '/login', query: { redirect: to.fullPath } })
  } else if (to.path === '/login' && authStore.isAuthenticated) {
    next('/')
  } else if (requiresAdmin && !authStore.isAdmin) {
    next('/')
  } else {
    next()
  }
})

router.afterEach((to) => {
  const title = to.meta.title as string | undefined
  document.title = title ? `${title} - Agent编排系统` : 'Agent编排系统'
})

export default router
