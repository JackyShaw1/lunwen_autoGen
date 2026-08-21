import { Card } from '@/components/ui/Card'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts'

const COLORS = ['#4f46e5', '#10b981', '#f59e0b', '#cbd5e1']

export function SubjectChart({ data }: { data: Record<string, number> }) {
  const chartData = Object.entries(data).map(([name, value]) => ({ name, value }))
  const max = Math.max(...chartData.map((d) => d.value), 1)

  return (
    <Card>
      <h3 className="text-sm font-semibold">学科分布</h3>
      <p className="mb-4 text-xs text-gray-500">各学科案例数量</p>
      {chartData.length === 0 ? (
        <div className="flex h-28 items-center justify-center rounded-xl bg-slate-50 text-sm text-slate-400">创建案例后显示学科分布</div>
      ) : <div className="space-y-2">
        {chartData.map((row) => (
          <div key={row.name} className="flex items-center gap-3 text-sm">
            <span className="w-16 shrink-0 text-gray-600">{row.name}</span>
            <div className="h-2 flex-1 overflow-hidden rounded bg-gray-100">
              <div
                className="h-full rounded bg-primary"
                style={{ width: `${(row.value / max) * 100}%` }}
              />
            </div>
            <span className="w-6 text-right font-semibold">{row.value}</span>
          </div>
        ))}
      </div>}
    </Card>
  )
}

export function StatusChart({ data }: { data: Record<string, number> }) {
  const labels: Record<string, string> = {
    finalized: '已定稿',
    running: '生成中',
    editing: '待编辑',
    draft: '草稿',
  }
  const chartData = Object.entries(data).map(([key, value]) => ({
    name: labels[key] || key,
    value,
  }))

  return (
    <Card>
      <h3 className="text-sm font-semibold">案例状态</h3>
      <p className="mb-4 text-xs text-gray-500">当前全部案例状态占比</p>
      <div className="flex items-center gap-6">
        <ResponsiveContainer width={100} height={100}>
          <PieChart>
            <Pie data={chartData} dataKey="value" innerRadius={28} outerRadius={44} paddingAngle={2}>
              {chartData.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="space-y-1 text-xs text-gray-600">
          {chartData.map((d, i) => (
            <div key={d.name} className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-sm" style={{ background: COLORS[i] }} />
              {d.name} {d.value}
            </div>
          ))}
        </div>
      </div>
    </Card>
  )
}

export function TrendChart({ data }: { data: Array<{ month: string; count: number }> }) {
  return (
    <Card>
      <h3 className="text-sm font-semibold">近 6 月生成趋势</h3>
      <p className="mb-4 text-xs text-gray-500">每月新建案例数</p>
      {data.length === 0 ? (
        <div className="flex h-[120px] items-center justify-center rounded-xl bg-slate-50 text-sm text-slate-400">暂无趋势数据</div>
      ) : <ResponsiveContainer width="100%" height={120}>
        <BarChart data={data}>
          <XAxis dataKey="month" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
          <YAxis hide />
          <Tooltip />
          <Bar dataKey="count" fill="#4f46e5" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>}
    </Card>
  )
}
