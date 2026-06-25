import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/login',          name: 'login',           component: () => import('../views/LoginView.vue'),          meta: { public: true } },
    { path: '/',               name: 'dashboard',       component: () => import('../views/DashboardView.vue') },
    { path: '/activities',     name: 'activities',      component: () => import('../views/ActivitiesView.vue') },
    { path: '/activities/:id', name: 'activity-detail', component: () => import('../views/ActivityDetailView.vue') },
    { path: '/health',         name: 'health',          component: () => import('../views/HealthView.vue') },
    { path: '/sleep',          name: 'sleep',           component: () => import('../views/SleepView.vue') },
    { path: '/profile',        name: 'profile',         component: () => import('../views/ProfileView.vue') },
    { path: '/d/:slug',        name: 'custom-dashboard', component: () => import('../views/CustomDashboardView.vue') },
  ],
})

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('access_token')
  if (!to.meta.public && !token) {
    next('/login')
  } else if (to.path === '/login' && token) {
    next('/')
  } else {
    next()
  }
})

export default router
