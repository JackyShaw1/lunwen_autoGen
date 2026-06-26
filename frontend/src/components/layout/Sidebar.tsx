import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'

const links = [
  { to: '/dashboard', label: '📊 案例工作台', end: false },
  { to: '/case/new', label: '📝 创建案例', end: true },
  { to: '/admin/agents', label: '🤖 Agent 配置', end: false, adminOnly: true },
]

export function Sidebar() {
  return (
    <aside className="w-60 shrink-0 border-r border-gray-200 bg-white p-5">
      <div className="mb-5 px-3 text-lg font-bold text-primary">CaseAutoGenSystem</div>
      <nav className="space-y-1">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.end}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-2 rounded-lg px-3 py-2.5 text-sm text-gray-700 no-underline',
                isActive ? 'bg-primary-light font-medium text-primary-dark' : 'hover:bg-gray-100',
              )
            }
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
