import { NavLink } from 'react-router-dom'
import { BookOpen, Bot, LayoutDashboard, PlusCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { authStore } from '@/stores/authStore'
import { LogoutButton } from './LogoutButton'

const links = [
  { to: '/dashboard', label: '工作台', icon: LayoutDashboard },
  { to: '/case/new', label: '创建案例', icon: PlusCircle },
  { to: '/admin/agents', label: 'AI 团队配置', icon: Bot, adminOnly: true },
]

export function Sidebar() {
  const user = authStore.getState().user
  const visibleLinks = links.filter((link) => !link.adminOnly || user?.role === 'admin')

  return (
    <aside className="hidden min-h-screen w-64 shrink-0 flex-col border-r border-slate-200 bg-white p-4 lg:flex">
      <NavLink to="/dashboard" className="mb-7 flex items-center gap-3 px-2 py-1 text-slate-950 no-underline">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-white shadow-sm"><BookOpen size={21} /></span>
        <span><strong className="block text-base leading-5">知案</strong><small className="text-xs text-slate-500">AI 教学案例工作台</small></span>
      </NavLink>

      <nav className="flex-1 space-y-1">
        <p className="mb-2 px-3 text-[11px] font-bold uppercase tracking-widest text-slate-400">工作空间</p>
        {visibleLinks.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => cn(
              'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-600 no-underline transition-colors',
              isActive ? 'bg-primary-light text-primary-dark' : 'hover:bg-slate-100 hover:text-slate-950',
            )}
          >
            <Icon size={18} />{label}
          </NavLink>
        ))}
      </nav>

      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
        <div className="flex items-center gap-3 px-1 pb-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-100 text-sm font-bold text-primary">{user?.name?.slice(0, 1) || '教'}</span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-slate-800">{user?.name || '教师用户'}</p>
            <p className="truncate text-xs text-slate-500">剩余 {user?.quota_remaining ?? 0} 次生成</p>
          </div>
        </div>
        <LogoutButton />
      </div>
    </aside>
  )
}
