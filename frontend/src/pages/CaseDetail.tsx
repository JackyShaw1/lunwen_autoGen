import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { fetchCasePackage } from '@/features/cases/api'
import { cn } from '@/lib/utils'

const TABS = [
  { id: 'body', label: '案例正文' },
  { id: 'questions', label: '讨论题' },
  { id: 'guide', label: '教师参考' },
  { id: 'alignment', label: '目标对齐' },
] as const

export default function CaseDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [tab, setTab] = useState<string>('body')

  const { data: pkg, isLoading } = useQuery({
    queryKey: ['case-package', id],
    queryFn: () => fetchCasePackage(id!),
    enabled: !!id,
  })

  if (isLoading || !pkg) return <div className="text-gray-500">加载案例…</div>

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{pkg.meta.title}</h1>
          <p className="mt-1 text-sm text-gray-500">
            {pkg.meta.subject} · {pkg.meta.course}
            {pkg.quality?.overall_score && (
              <Badge variant="teal" className="ml-2">Rubric {pkg.quality.overall_score}</Badge>
            )}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">重跑 Pedagogy Agent</Button>
          <Button onClick={() => navigate(`/case/${id}/export`)}>导出授课包</Button>
        </div>
      </div>

      <Card>
        <div className="mb-4 flex gap-1 border-b">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={cn(
                'px-4 py-2 text-sm border-b-2 -mb-px',
                tab === t.id ? 'border-primary font-semibold text-primary' : 'border-transparent text-gray-500',
              )}
            >
              {t.label}
            </button>
          ))}
        </div>

        {tab === 'body' && (
          <div className="prose prose-sm max-w-none text-gray-700">
            <p className="text-xs text-gray-500">⚠️ {pkg.meta.fictional_disclaimer}</p>
            <h3>背景</h3>
            <p>{pkg.body.background}</p>
            <h3>案例叙述</h3>
            <p>{pkg.body.narrative}</p>
            <h3>决策点</h3>
            <p><strong>{pkg.body.decision_point}</strong></p>
          </div>
        )}

        {tab === 'questions' && (
          <div className="space-y-3">
            {pkg.discussion_questions.map((q, i) => (
              <div key={i} className="rounded-r-lg border-l-4 border-primary bg-gray-50 p-4">
                <div className="text-xs font-semibold text-primary">{q.level}层</div>
                <p className="mt-1 text-sm">{q.question}</p>
              </div>
            ))}
          </div>
        )}

        {tab === 'guide' && (
          <div className="space-y-4 text-sm text-gray-700">
            <p><strong>授课流程：</strong>{pkg.instructor_guide.teaching_flow}</p>
            <p><strong>要点：</strong>{pkg.instructor_guide.key_points?.join('；')}</p>
            <p><strong>常见误区：</strong>{pkg.instructor_guide.common_misconceptions?.join('；')}</p>
          </div>
        )}

        {tab === 'alignment' && (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-left">
                <th className="p-2">教学目标</th>
                <th className="p-2">案例环节</th>
                <th className="p-2">课堂活动</th>
              </tr>
            </thead>
            <tbody>
              {pkg.alignment_matrix.map((row, i) => (
                <tr key={i} className="border-t">
                  <td className="p-2">{row.objective_id}</td>
                  <td className="p-2">{row.case_section}</td>
                  <td className="p-2">{row.activity}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  )
}
