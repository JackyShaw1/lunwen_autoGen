import { Navigate, Outlet } from 'react-router-dom'
import { authStore } from '@/stores/authStore'

export function AuthGuard() {
  if (!authStore.getState().isAuthenticated()) {
    return <Navigate to="/auth" replace />
  }
  return <Outlet />
}

export function AdminGuard() {
  if (!authStore.getState().isAuthenticated()) {
    return <Navigate to="/auth" replace />
  }
  // MVP: allow all authenticated users to view admin for demo
  return <Outlet />
}
