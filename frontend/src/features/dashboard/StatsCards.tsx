import { BookOpenCheck, Clock3, FileCheck2, Sparkles } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import type { DashboardStats } from '@/types/case'

export function StatsCards({ stats }: { stats: DashboardStats }) {
  const items = [
    {
      label: '全部案例',
      value: stats.total_cases,
      sub: stats.total_cases_delta > 0 ? `本月新增 ${stats.total_cases_delta} 个` : '持续沉淀课程资产',
      icon: BookOpenCheck,
      color: 'bg-indigo-50 text-indigo-600',
    },
    {
      label: '可直接授课',
      value: stats.finalized_count,
      sub: `整体完成率 ${stats.completion_rate}%`,
      icon: FileCheck2,
      color: 'bg-emerald-50 text-emerald-600',
    },
    {
      label: '预计节省时间',
      value: `${stats.estimated_hours_saved}h`,
      sub: '按每个案例 8 小时估算',
      icon: Clock3,
      color: 'bg-amber-50 text-amber-600',
    },
    {
      label: '剩余生成额度',
      value: stats.quota_remaining,
      sub: stats.quota_remaining > 1 ? '额度充足，可继续创建' : '额度即将用完',
      icon: Sparkles,
      color: 'bg-violet-50 text-violet-600',
      highlight: true,
    },
  ]

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {items.map(({ label, value, sub, icon: Icon, color, highlight }) => (
        <Card key={label} className={highlight ? 'border-indigo-200 bg-gradient-to-br from-white to-indigo-50/70' : ''}>
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-slate-500">{label}</p>
              <p className="mt-2 text-3xl font-bold tracking-tight text-slate-950">{value}</p>
            </div>
            <span className={`flex h-10 w-10 items-center justify-center rounded-xl ${color}`}><Icon size={20} /></span>
          </div>
          <p className="mt-3 text-xs text-slate-500">{sub}</p>
        </Card>
      ))}
    </div>
  )
}
