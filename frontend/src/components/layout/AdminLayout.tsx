import { Outlet, NavLink } from 'react-router-dom'

const adminLinks = [
  { id: 'agent-list', label: '🤖 Agent 角色' },
  { id: 'workflow', label: '🔗 编排模板' },
  { id: 'tools', label: '🔧 Tool 工具' },
  { id: 'subjects', label: '📚 学科插件' },
  { id: 'global', label: '🌐 全局设置' },
  { id: 'monitor', label: '📊 运行监控' },
]

export function AdminLayout() {
  return (
    <div className="flex min-h-screen bg-gray-50">
      <aside className="w-52 shrink-0 border-r border-gray-200 bg-slate-50 p-4">
        <div className="mb-4 px-2 text-sm font-bold text-primary">⚙️ Agent 配置中心</div>
        <nav className="space-y-0.5">
          {adminLinks.map((link) => (
            <a
              key={link.id}
              href={`#${link.id}`}
              className="block rounded-lg px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
            >
              {link.label}
            </a>
          ))}
        </nav>
        <NavLink to="/dashboard" className="mt-4 block px-3 py-2 text-sm text-gray-500 hover:text-primary">
          ← 返回工作台
        </NavLink>
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
