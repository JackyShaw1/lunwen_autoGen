import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Textarea } from '@/components/ui/Input'
import { fetchCasePackage, regenerateAgent, saveCasePackage } from '@/features/cases/api'
import type { CasePackage } from '@/types/case'
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
  const qc = useQueryClient()
  const [tab, setTab] = useState<string>('body')
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState<CasePackage | null>(null)

  const { data: pkg, isLoading, error } = useQuery({
    queryKey: ['case-package', id],
    queryFn: () => fetchCasePackage(id!),
    enabled: !!id,
  })

  const saveMut = useMutation({
    mutationFn: () => saveCasePackage(id!, draft!),
    onSuccess: () => {
      setEditing(false)
      qc.invalidateQueries({ queryKey: ['case-package', id] })
    },
  })

  const regenMut = useMutation({
    mutationFn: (agent: string) => regenerateAgent(id!, agent),
    onSuccess: () => navigate(`/case/${id}/generate?resume=1`),
  })

  if (isLoading) return <div className="text-gray-500">加载案例…</div>
  if (error || !pkg) {
    return (
      <div className="text-red-600">
        案例尚未生成或不存在。
        <Button className="ml-3" variant="outline" onClick={() => navigate(`/case/${id}/generate`)}>
          去生成
        </Button>
      </div>
    )
  }

  const view = editing && draft ? draft : pkg

  const startEdit = () => {
    setDraft(structuredClone(pkg))
    setEditing(true)
  }

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{view.meta.title}</h1>
          <p className="mt-1 text-sm text-gray-500">
            {view.meta.subject} · {view.meta.course}
            {view.quality?.overall_score != null && (
              <Badge variant="teal" className="ml-2">Rubric {view.quality.overall_score}</Badge>
            )}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {!editing ? (
            <>
              <Button variant="outline" onClick={startEdit}>编辑</Button>
              <Button
                variant="outline"
                disabled={regenMut.isPending}
                onClick={() => regenMut.mutate('PedagogyDesigner')}
              >
                重跑 Pedagogy Agent
              </Button>
              <Button onClick={() => navigate(`/case/${id}/export`)}>导出授课包</Button>
            </>
          ) : (
            <>
              <Button variant="outline" onClick={() => setEditing(false)}>取消</Button>
              <Button disabled={saveMut.isPending} onClick={() => saveMut.mutate()}>
                {saveMut.isPending ? '保存中…' : '保存版本'}
              </Button>
            </>
          )}
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
          <div className="space-y-4 text-sm text-gray-700">
            <p className="text-xs text-gray-500">⚠️ {view.meta.fictional_disclaimer}</p>
            <div>
              <h3 className="mb-1 font-semibold">背景</h3>
              {editing && draft ? (
                <Textarea
                  rows={4}
                  value={draft.body.background || ''}
                  onChange={(e) =>
                    setDraft({ ...draft, body: { ...draft.body, background: e.target.value } })
                  }
                />
              ) : (
                <p>{view.body.background}</p>
              )}
            </div>
            <div>
              <h3 className="mb-1 font-semibold">案例叙述</h3>
              {editing && draft ? (
                <Textarea
                  rows={8}
                  value={draft.body.narrative}
                  onChange={(e) =>
                    setDraft({ ...draft, body: { ...draft.body, narrative: e.target.value } })
                  }
                />
              ) : (
                <p className="whitespace-pre-wrap">{view.body.narrative}</p>
              )}
            </div>
            <div>
              <h3 className="mb-1 font-semibold">决策点</h3>
              {editing && draft ? (
                <Textarea
                  rows={3}
                  value={draft.body.decision_point || ''}
                  onChange={(e) =>
                    setDraft({ ...draft, body: { ...draft.body, decision_point: e.target.value } })
                  }
                />
              ) : (
                <p><strong>{view.body.decision_point}</strong></p>
              )}
            </div>
          </div>
        )}

        {tab === 'questions' && (
          <div className="space-y-3">
            {view.discussion_questions.map((q, i) => (
              <div key={i} className="rounded-r-lg border-l-4 border-primary bg-gray-50 p-4">
                <div className="text-xs font-semibold text-primary">{q.level}层</div>
                {editing && draft ? (
                  <Textarea
                    className="mt-2"
                    rows={2}
                    value={draft.discussion_questions[i].question}
                    onChange={(e) => {
                      const next = [...draft.discussion_questions]
                      next[i] = { ...next[i], question: e.target.value }
                      setDraft({ ...draft, discussion_questions: next })
                    }}
                  />
                ) : (
                  <p className="mt-1 text-sm">{q.question}</p>
                )}
              </div>
            ))}
          </div>
        )}

        {tab === 'guide' && (
          <div className="space-y-4 text-sm text-gray-700">
            {editing && draft ? (
              <Textarea
                rows={4}
                value={draft.instructor_guide.teaching_flow || ''}
                onChange={(e) =>
                  setDraft({
                    ...draft,
                    instructor_guide: { ...draft.instructor_guide, teaching_flow: e.target.value },
                  })
                }
              />
            ) : (
              <p><strong>授课流程：</strong>{view.instructor_guide.teaching_flow}</p>
            )}
            <p><strong>要点：</strong>{view.instructor_guide.key_points?.join('；')}</p>
            <p><strong>常见误区：</strong>{view.instructor_guide.common_misconceptions?.join('；')}</p>
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
              {view.alignment_matrix.map((row, i) => (
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
