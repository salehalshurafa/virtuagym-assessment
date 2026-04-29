import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import axios from 'axios'

import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'

// Cookies travel with every request — this is what makes the HttpOnly
// session cookie work for /api/auth/me, /api/plans, etc.
axios.defaults.withCredentials = true

// Global 401 handler. If a request comes back unauthenticated (cookie
// expired, server restarted, session revoked), drop the local user state
// and bounce to /login. Public pages are exempt so we don't loop.
axios.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      const auth = useAuthStore()
      auth.me = null
      const current = router.currentRoute.value
      if (!current.meta.public) {
        router.replace({ path: '/login', query: { redirect: current.fullPath } })
      }
    }
    return Promise.reject(err)
  },
)

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
