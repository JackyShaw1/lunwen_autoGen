import { useNavigate } from 'react-router-dom'
import { LogOut } from 'lucide-react'
import { api } from '@/lib/api-client'
import { authStore } from '@/stores/authStore'
import { cn } from '@/lib/utils'

export function LogoutButton({ className }: { className?: string }) {
  const navigate = useNavigate()

  const logout = async () => {
    try {
      await api.post('/auth/logout')
    } finally {
      authStore.getState().logout()
      navigate('/auth', { replace: true })
    }
  }

  return (
    <button
      type="button"
      onClick={logout}
      className={cn('flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-xs font-medium text-slate-500 hover:bg-white hover:text-slate-800', className)}
    >
      <LogOut size={14} />退出登录
    </button>
  )
}
