import axios from 'axios'
import { authStore } from '@/stores/authStore'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
  withCredentials: true,
})

api.interceptors.request.use((config) => {
  const token = authStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let refreshPromise: Promise<string> | null = null

export async function refreshAuthSession(): Promise<string> {
  if (!refreshPromise) {
    refreshPromise = axios
      .post(`${api.defaults.baseURL}/auth/refresh`, null, { withCredentials: true })
      .then(({ data }) => {
        authStore.getState().login(data.user, data.access_token)
        return data.access_token as string
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const request = err.config as (typeof err.config & { _retried?: boolean }) | undefined
    const isAuthRequest = String(request?.url || '').includes('/auth/')
    if (err.response?.status === 401 && request && !request._retried && !isAuthRequest) {
      request._retried = true
      try {
        const token = await refreshAuthSession()
        request.headers.Authorization = `Bearer ${token}`
        return api(request)
      } catch {
        authStore.getState().logout()
        if (window.location.pathname !== '/auth') window.location.href = '/auth'
      }
    }
    return Promise.reject(err)
  },
)

export function getWsBaseUrl() {
  const env = import.meta.env.VITE_WS_BASE_URL
  if (env) return env.replace(/\/$/, '')
  const { protocol, host } = window.location
  return `${protocol === 'https:' ? 'wss' : 'ws'}://${host}`
}
