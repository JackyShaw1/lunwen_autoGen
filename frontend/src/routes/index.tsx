import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AppLayout } from '@/components/layout/AppLayout'
import { AdminLayout } from '@/components/layout/AdminLayout'
import { AuthGuard } from '@/routes/guards'
import Landing from '@/pages/Landing'
import Auth from '@/pages/Auth'
import Dashboard from '@/pages/Dashboard'
import CreateCase from '@/pages/CreateCase'
import GenerationMonitor from '@/pages/GenerationMonitor'
import CaseDetail from '@/pages/CaseDetail'
import Export from '@/pages/Export'
import AgentConfig from '@/pages/admin/AgentConfig'

export function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/auth" element={<Auth />} />
        <Route element={<AuthGuard />}>
          <Route element={<AppLayout />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/case/new" element={<CreateCase />} />
            <Route path="/case/:id/generate" element={<GenerationMonitor />} />
            <Route path="/case/:id/export" element={<Export />} />
            <Route path="/case/:id" element={<CaseDetail />} />
          </Route>
          <Route element={<AdminLayout />}>
            <Route path="/admin/agents" element={<AgentConfig />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
