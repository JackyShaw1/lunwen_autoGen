import { Outlet, NavLink } from 'react-router-dom'
import { LogoutButton } from './LogoutButton'

const adminLinks = [
  { to: '/admin/agents', label: '🤖 Agent 配置' },
  { to: '/admin/model', label: '✨ 大模型配置' },
]

export function AdminLayout() {
  return (
    <div className="flex min-h-screen bg-gray-50">
      <aside className="flex w-52 shrink-0 flex-col border-r border-gray-200 bg-slate-50 p-4">
        <div className="mb-4 px-2 text-sm font-bold text-primary">⚙️ Agent 配置中心</div>
        <nav className="flex-1 space-y-0.5">
          {adminLinks.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                `block rounded-lg px-3 py-2 text-sm ${
                  isActive ? 'bg-indigo-100 font-semibold text-primary' : 'text-gray-700 hover:bg-gray-100'
                }`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
        <NavLink to="/dashboard" className="mt-4 block px-3 py-2 text-sm text-gray-500 hover:text-primary">
          ← 返回工作台
        </NavLink>
        <LogoutButton className="mt-1" />
      </aside>
      <main className="flex-1 overflow-y-auto p-6 md:p-8">
        <Outlet />
      </main>
    </div>
  )
}

export function AdminSubSection({
  id,
  title,
  description,
  children,
}: {
  id: string
  title: string
  description?: string
  children: React.ReactNode
}) {
  return (
    <section id={id} className="mb-12 scroll-mt-6">
      <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
      {description && <p className="mt-1 text-sm text-gray-500">{description}</p>}
      <div className="mt-6">{children}</div>
    </section>
  )
}
