import { Card } from '@/components/ui/Card'
import type { DashboardStats } from '@/types/case'

export function StatsCards({ stats }: { stats: DashboardStats }) {
  const items = [
    {
      label: '案例总数',
      value: stats.total_cases,
      sub: stats.total_cases_delta > 0 ? `↑ ${stats.total_cases_delta} 较上月` : undefined,
      trend: stats.total_cases_delta > 0 ? 'up' : undefined,
      highlight: true,
      icon: '📋',
    },
    {
      label: '已定稿',
      value: stats.finalized_count,
      sub: `完成率 ${stats.completion_rate}%`,
      icon: '✅',
    },
    {
      label: '生成中',
      value: stats.running_count,
      sub: 'Agent 协作进行中',
      icon: '⟳',
    },
    {
      label: '平均 Rubric',
      value: stats.avg_rubric.toFixed(1),
      sub: stats.avg_rubric_delta > 0 ? `↑ ${stats.avg_rubric_delta} 较上月` : undefined,
      trend: stats.avg_rubric_delta > 0 ? 'up' : undefined,
      icon: '⭐',
    },
    {
      label: '预估节省工时',
      value: stats.estimated_hours_saved,
      unit: '小时',
      sub: '按每案例 8h 估算',
      icon: '⏱',
    },
    {
      label: '导出次数',
      value: stats.export_count.total,
      sub: `Word ${stats.export_count.docx} · PDF ${stats.export_count.pdf}`,
      icon: '📤',
    },
  ]

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
      {items.map((item) => (
        <Card
          key={item.label}
          className={item.highlight ? 'border-primary bg-gradient-to-br from-teal-50 to-white' : 'p-4'}
        >
          <span className="absolute right-3 top-3 text-xl opacity-40">{item.icon}</span>
          <div className="text-xs text-gray-500">{item.label}</div>
          <div className="mt-1 text-2xl font-bold text-gray-900">
            {item.value}
            {item.unit && <span className="text-sm font-medium">{item.unit}</span>}
          </div>
          {item.sub && (
            <div className={`mt-1 text-xs ${item.trend === 'up' ? 'font-semibold text-green-600' : 'text-gray-500'}`}>
              {item.sub}
            </div>
          )}
        </Card>
      ))}
    </div>
  )
}
