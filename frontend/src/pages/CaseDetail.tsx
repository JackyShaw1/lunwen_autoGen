import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Textarea } from '@/components/ui/Input'
import { fetchCasePackage, saveCasePackage } from '@/features/cases/api'
import type { CasePackage } from '@/types/case'
import { cn } from '@/lib/utils'
import { BookOpenText, Clock3, Presentation, Quote, Users } from 'lucide-react'

const TABS = [
  { id: 'body', label: '案例正文' },
  { id: 'questions', label: '讨论题' },
  { id: 'guide', label: '教师参考' },
  { id: 'alignment', label: '目标对齐' },
] as const

function splitReadingParagraphs(text?: string) {
  const normalized = (text || '').replace(/\r\n/g, '\n').trim()
  if (!normalized) return ['暂无内容']
  const blocks = normalized.split(/\n\s*\n+/).map((part) => part.trim()).filter(Boolean)
  return blocks.flatMap((block) => {
    if (block.length <= 430) return [block.replace(/\n/g, ' ')]
    const sentences = block.match(/[^。！？；]+[。！？；]?/g) || [block]
    const result: string[] = []
    let current = ''
    sentences.forEach((sentence) => {
      if (current && current.length + sentence.length > 320) {
        result.push(current)
        current = sentence.trim()
      } else {
        current += sentence.trim()
      }
    })
    if (current) result.push(current)
    return result
  })
}

function ReadingText({ text }: { text?: string }) {
  return (
    <div className="case-reading space-y-5 text-[15px] leading-8 text-slate-700">
      {splitReadingParagraphs(text).map((paragraph, index) => (
        <p key={`${index}-${paragraph.slice(0, 12)}`} className="text-justify indent-8">{paragraph}</p>
      ))}
    </div>
  )
}

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
  const actualWords = [view.body.background, view.body.narrative, view.body.decision_point]
    .join('')
    .replace(/\s/g, '').length
  const targetWords = view.meta.target_words
  const lengthAccepted = targetWords
    ? actualWords >= Math.ceil(targetWords * 0.95) && actualWords <= Math.floor(targetWords * 1.05)
    : true
  const readingMinutes = Math.max(1, Math.ceil(actualWords / 450))

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
              <Badge variant="teal" className="ml-2">质量评分 {view.quality.overall_score}</Badge>
            )}
            {targetWords != null && (
              <span title={view.meta.word_count_scope || '背景、案例叙述与决策点的可见字符（不计空白）'}>
                <Badge variant={lengthAccepted ? 'teal' : 'yellow'} className="ml-2">
                  正文 {actualWords.toLocaleString()} / {targetWords.toLocaleString()} 字
                </Badge>
              </span>
            )}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {!editing ? (
            <>
              <Button variant="outline" onClick={startEdit}>编辑</Button>
              <Button onClick={() => navigate(`/case/${id}/export`)}><Presentation size={17} />导出 Word / PDF / PPT</Button>
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
        <div className="mb-4 flex gap-1 overflow-x-auto border-b">
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
          <article className="mx-auto max-w-5xl space-y-7 pb-4">
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-500">
              <span>{view.meta.fictional_disclaimer || '本案例用于教学研讨。'}</span>
              <span className="flex items-center gap-1.5"><Clock3 size={14} />预计阅读 {readingMinutes} 分钟</span>
            </div>

            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-50/70">
              <div className="flex items-center gap-3 border-b border-slate-200 px-6 py-4">
                <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-white text-primary shadow-sm"><BookOpenText size={18} /></span>
                <div><p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Context</p><h2 className="font-bold text-slate-900">案例背景</h2></div>
              </div>
              <div className="px-6 py-6 md:px-10">
              {editing && draft ? (
                <Textarea
                  rows={6}
                  value={draft.body.background || ''}
                  onChange={(e) =>
                    setDraft({ ...draft, body: { ...draft.body, background: e.target.value } })
                  }
                />
              ) : (
                <ReadingText text={view.body.background} />
              )}
              </div>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white px-6 py-7 shadow-sm md:px-12 md:py-10">
              <div className="mb-7 flex flex-wrap items-end justify-between gap-3 border-b border-slate-100 pb-5">
                <div><p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Case Narrative</p><h2 className="mt-1 text-xl font-bold text-slate-950">案例正文</h2></div>
                <span className="text-xs text-slate-400">正文约 {actualWords.toLocaleString()} 字</span>
              </div>
              {editing && draft ? (
                <Textarea
                  rows={24}
                  className="case-reading leading-7"
                  value={draft.body.narrative}
                  onChange={(e) =>
                    setDraft({ ...draft, body: { ...draft.body, narrative: e.target.value } })
                  }
                />
              ) : (
                <ReadingText text={view.body.narrative} />
              )}
            </section>

            {!!view.body.characters?.length && !editing && (
              <section>
                <div className="mb-3 flex items-center gap-2 text-sm font-bold text-slate-900"><Users size={17} className="text-primary" />关键角色与立场</div>
                <div className="grid gap-3 md:grid-cols-3">
                  {view.body.characters.map((character) => (
                    <div key={character.name} className="rounded-xl border border-slate-200 bg-white p-4">
                      <p className="font-bold text-slate-900">{character.name}</p>
                      <p className="mt-0.5 text-xs font-medium text-primary">{character.role}</p>
                      <p className="mt-3 text-sm leading-6 text-slate-600">{character.stance}</p>
                    </div>
                  ))}
                </div>
              </section>
            )}

            <section className="relative overflow-hidden rounded-2xl border border-indigo-200 bg-gradient-to-br from-indigo-50 to-white px-6 py-7 md:px-10">
              <Quote className="absolute right-6 top-5 text-indigo-100" size={54} />
              <div className="relative">
                <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary">Decision Point</p>
                <h2 className="mt-1 text-lg font-bold text-slate-950">关键决策点</h2>
                <div className="mt-5 text-[15px] font-semibold leading-8 text-indigo-950">
              {editing && draft ? (
                <Textarea
                  rows={5}
                  value={draft.body.decision_point || ''}
                  onChange={(e) =>
                    setDraft({ ...draft, body: { ...draft.body, decision_point: e.target.value } })
                  }
                />
              ) : (
                <ReadingText text={view.body.decision_point} />
              )}
                </div>
              </div>
            </section>
          </article>
        )}

        {tab === 'questions' && (
          <div className="mx-auto max-w-4xl space-y-4">
            {view.discussion_questions.map((q, i) => (
              <div key={i} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex items-start gap-4">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-sm font-bold text-primary">{i + 1}</span>
                  <div className="min-w-0 flex-1">
                    <div className="mb-2 text-xs font-semibold text-primary">{q.level}层问题</div>
                {editing && draft ? (
                  <Textarea
                    rows={2}
                    value={draft.discussion_questions[i].question}
                    onChange={(e) => {
                      const next = [...draft.discussion_questions]
                      next[i] = { ...next[i], question: e.target.value }
                      setDraft({ ...draft, discussion_questions: next })
                    }}
                  />
                ) : (
                      <p className="text-[15px] font-semibold leading-7 text-slate-800">{q.question}</p>
                )}
                    {q.teaching_intent && <p className="mt-3 border-t border-slate-100 pt-3 text-xs leading-5 text-slate-500"><span className="font-semibold text-slate-600">教学意图：</span>{q.teaching_intent}</p>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === 'guide' && (
          <div className="mx-auto grid max-w-5xl gap-5 text-sm text-slate-700 lg:grid-cols-2">
            <section className="rounded-2xl border border-indigo-100 bg-indigo-50/60 p-5 lg:col-span-2">
              <p className="mb-2 text-xs font-bold uppercase tracking-wider text-primary">Teaching Flow</p>
              <h3 className="mb-3 font-bold text-slate-900">建议授课流程</h3>
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
                <p className="leading-7">{view.instructor_guide.teaching_flow}</p>
            )}
            </section>
            <section className="rounded-2xl border border-slate-200 bg-white p-5">
              <h3 className="font-bold text-slate-900">教学要点</h3>
              <ul className="mt-3 space-y-2.5">{view.instructor_guide.key_points?.map((point) => <li key={point} className="flex gap-2 leading-6"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />{point}</li>)}</ul>
            </section>
            <section className="rounded-2xl border border-amber-200 bg-amber-50/50 p-5">
              <h3 className="font-bold text-slate-900">常见误区</h3>
              <ul className="mt-3 space-y-2.5">{view.instructor_guide.common_misconceptions?.map((item) => <li key={item} className="flex gap-2 leading-6"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500" />{item}</li>)}</ul>
            </section>
          </div>
        )}

        {tab === 'alignment' && (
          <div className="mx-auto max-w-5xl overflow-hidden rounded-2xl border border-slate-200"><div className="overflow-x-auto"><table className="w-full min-w-[760px] text-sm">
            <thead>
              <tr className="bg-slate-900 text-left text-white">
                <th className="p-4">教学目标</th>
                <th className="p-4">案例环节</th>
                <th className="p-4">课堂活动</th>
                <th className="p-4">评价方式</th>
              </tr>
            </thead>
            <tbody>
              {view.alignment_matrix.map((row, i) => (
                <tr key={i} className="border-t border-slate-200 odd:bg-white even:bg-slate-50/70">
                  <td className="p-4 font-bold text-primary">{row.objective_id}</td>
                  <td className="p-4 leading-6 text-slate-700">{row.case_section}</td>
                  <td className="p-4 leading-6 text-slate-700">{row.activity}</td>
                  <td className="p-4 leading-6 text-slate-700">{row.assessment}</td>
                </tr>
              ))}
            </tbody>
          </table></div></div>
        )}
      </Card>
    </div>
  )
}
