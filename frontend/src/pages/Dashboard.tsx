import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { StatsCards } from '@/features/dashboard/StatsCards'
import { SubjectChart, StatusChart, TrendChart } from '@/features/dashboard/Charts'
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
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold">你好，{user?.name || '老师'} 👋</h2>
          <p className="text-sm text-gray-500">本学期教学案例生成与使用数据一览</p>
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
          <Button onClick={() => navigate('/case/new')}>+ 创建案例</Button>
        </div>
      </div>

      <StatsCards stats={stats} />

      <div className="mt-5 grid gap-4 lg:grid-cols-3">
        <SubjectChart data={stats.subject_distribution} />
        <StatusChart data={stats.status_distribution} />
        <TrendChart data={stats.monthly_trend} />
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-4">
        {[
          { label: '平均生成耗时', value: `${stats.avg_generation_minutes} 分钟` },
          { label: '讨论题总数', value: `${stats.discussion_questions_total} 题` },
          { label: '局部 Agent 重跑', value: `${stats.agent_regenerate_count} 次` },
          { label: '剩余生成额度', value: `${stats.quota_remaining} 次`, highlight: true },
        ].map((item) => (
          <Card key={item.label} className={`p-4 ${item.highlight ? 'border-primary' : ''}`}>
            <div className="text-xs text-gray-500">{item.label}</div>
            <div className={`mt-1 text-xl font-bold ${item.highlight ? 'text-primary' : ''}`}>{item.value}</div>
          </Card>
        ))}
      </div>

      <div className="mt-8 flex items-center justify-between">
        <h3 className="font-semibold">最近案例</h3>
        <span className="text-sm text-gray-500">共 {cases.length} 个</span>
      </div>
      <div className="mt-3">
        <CaseList cases={cases} />
      </div>
    </div>
  )
}
