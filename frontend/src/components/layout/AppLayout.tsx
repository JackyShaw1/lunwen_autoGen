import { Outlet } from 'react-router-dom'
import { NavLink } from 'react-router-dom'
import { BookOpen, LayoutDashboard, PlusCircle } from 'lucide-react'
import { Sidebar } from './Sidebar'
import { LogoutButton } from './LogoutButton'

export function AppLayout() {
  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />
      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200 bg-white/95 px-4 backdrop-blur lg:hidden">
          <NavLink to="/dashboard" className="flex items-center gap-2 font-bold text-slate-950"><span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-white"><BookOpen size={17} /></span>知案</NavLink>
          <nav className="flex items-center gap-1">
            <NavLink to="/dashboard" aria-label="工作台" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100"><LayoutDashboard size={19} /></NavLink>
            <NavLink to="/case/new" aria-label="创建案例" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100"><PlusCircle size={19} /></NavLink>
            <LogoutButton className="w-auto px-2" />
          </nav>
        </header>
        <main className="mx-auto w-full max-w-[1500px] p-4 sm:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
