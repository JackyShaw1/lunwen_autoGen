import { useNavigate } from 'react-router-dom'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge, statusBadge } from '@/components/ui/Badge'
import type { CaseTask } from '@/types/case'

export function CaseList({ cases }: { cases: CaseTask[] }) {
  const navigate = useNavigate()

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
            {c.rubric_overall && <Badge variant="teal">Rubric {c.rubric_overall}</Badge>}
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
