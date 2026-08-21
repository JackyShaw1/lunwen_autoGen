import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowRight, BookOpen, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { StatsCards } from '@/features/dashboard/StatsCards'
import { SubjectChart, TrendChart } from '@/features/dashboard/Charts'
import { CaseList } from '@/features/cases/CaseList'
import { fetchCases, fetchDashboardStats } from '@/features/cases/api'
import type { StatsRange } from '@/types/case'
import { authStore } from '@/stores/authStore'

export default function Dashboard() {
  const navigate = useNavigate()
  const [range, setRange] = useState<StatsRange>('month')
  const user = authStore.getState().user

  const { data: stats } = useQuery({
    queryKey: ['dashboard-stats', range],
    queryFn: () => fetchDashboardStats(range),
  })
  const { data: cases = [] } = useQuery({
    queryKey: ['cases'],
    queryFn: fetchCases,
  })

  if (!stats) return <div className="text-gray-500">加载中…</div>

  return (
    <div>
      <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-primary">教学工作台</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-950">你好，{user?.name || '老师'}</h1>
          <p className="mt-2 text-sm text-slate-500">继续完善课程资产，或从一个新的教学目标开始。</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex gap-1 rounded-full border border-gray-200 bg-white p-1">
            {(['month', 'semester', 'all'] as StatsRange[]).map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => setRange(r)}
                className={`rounded-full px-3 py-1 text-xs ${range === r ? 'bg-primary text-white' : 'text-gray-600'}`}
              >
                {r === 'month' ? '本月' : r === 'semester' ? '本学期' : '全部'}
              </button>
            ))}
          </div>
          <Button onClick={() => navigate('/case/new')}><Sparkles size={16} />创建新案例</Button>
        </div>
      </div>

      <StatsCards stats={stats} />

      <div className="mt-6 grid gap-4 lg:grid-cols-[.8fr_1.2fr]">
        <SubjectChart data={stats.subject_distribution} />
        <TrendChart data={stats.monthly_trend} />
      </div>

      <div className="mt-9 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-200/70 text-slate-600"><BookOpen size={18} /></span>
          <div><h2 className="font-bold text-slate-900">最近案例</h2><p className="text-xs text-slate-500">按最近更新时间排列</p></div>
        </div>
        {cases.length > 0 && <button type="button" className="flex items-center gap-1 text-sm font-semibold text-primary">查看全部 <ArrowRight size={15} /></button>}
      </div>
      <div className="mt-4">
        <CaseList cases={cases} />
      </div>
    </div>
  )
}
