import axios from 'axios'
import { authStore } from '@/stores/authStore'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  const token = authStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      authStore.getState().logout()
      if (window.location.pathname !== '/auth') {
        window.location.href = '/auth'
      }
    }
    return Promise.reject(err)
  },
)

export function getWsBaseUrl() {
  const env = import.meta.env.VITE_WS_BASE_URL
  if (env) return env.replace(/\/$/, '')
  // 开发环境直连后端，避开 Vite WebSocket 代理丢包
  if (import.meta.env.DEV) {
    return 'ws://127.0.0.1:8000'
  }
  const { protocol, host } = window.location
  return `${protocol === 'https:' ? 'wss' : 'ws'}://${host}`
}
