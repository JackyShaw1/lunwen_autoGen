import { Navigate, Outlet } from 'react-router-dom'
import { authStore } from '@/stores/authStore'

export function AuthGuard() {
  if (!authStore.getState().isAuthenticated()) {
    return <Navigate to="/auth" replace />
  }
  return <Outlet />
}

export function AdminGuard() {
  const { isAuthenticated, user } = authStore.getState()
  if (!isAuthenticated()) {
    return <Navigate to="/auth" replace />
  }
  if (user?.role !== 'admin') {
    return <Navigate to="/dashboard" replace />
  }
  return <Outlet />
}
