import { useNavigate } from 'react-router-dom'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge, statusBadge } from '@/components/ui/Badge'
import type { CaseTask } from '@/types/case'
import { BookOpen, Plus } from 'lucide-react'

export function CaseList({ cases }: { cases: CaseTask[] }) {
  const navigate = useNavigate()

  if (cases.length === 0) {
    return (
      <Card className="border-dashed py-14 text-center">
        <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 text-primary"><BookOpen size={23} /></span>
        <h3 className="mt-4 font-bold text-slate-900">还没有教学案例</h3>
        <p className="mx-auto mt-2 max-w-sm text-sm text-slate-500">从一门正在教授的课程开始，几分钟内建立第一份可编辑的案例授课包。</p>
        <Button className="mt-5" onClick={() => navigate('/case/new')}><Plus size={16} />创建第一个案例</Button>
      </Card>
    )
  }

  return (
    <div className="space-y-3">
      {cases.map((c) => (
        <Card
          key={c.id}
          className="flex cursor-pointer flex-wrap items-center justify-between gap-4 p-5 transition-shadow hover:shadow-md"
          onClick={() => {
            if (c.status === 'running') navigate(`/case/${c.id}/generate`)
            else navigate(`/case/${c.id}`)
          }}
        >
          <div>
            <h3 className="font-semibold text-gray-900">{c.title}</h3>
            <p className="mt-1 text-sm text-gray-500">
              {c.subject} · {c.course_name} · {c.case_type} · {c.target_audience} · 更新于{' '}
              {c.updated_at.slice(0, 10)}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {statusBadge(c.status)}
            {c.rubric_overall && <Badge variant="teal">质量 {c.rubric_overall}</Badge>}
            {c.status === 'running' ? (
              <Button
                variant="outline"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation()
                  navigate(`/case/${c.id}/generate`)
                }}
              >
                查看协作
              </Button>
            ) : c.status === 'finalized' || c.status === 'completed' ? (
              <Button
                variant="outline"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation()
                  navigate(`/case/${c.id}/export`)
                }}
              >
                导出
              </Button>
            ) : (
              <Button variant="outline" size="sm">编辑</Button>
            )}
          </div>
        </Card>
      ))}
    </div>
  )
}
