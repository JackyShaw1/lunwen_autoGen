import { useMemo, useState } from 'react'
import type { AgentProgressMessage, AgentStepResult } from '@/types/case'
import { AGENT_LABELS } from './AgentPipeline'
import { Badge } from '@/components/ui/Badge'
import { Card } from '@/components/ui/Card'
import { cn } from '@/lib/utils'

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mb-3">
      <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-400">{label}</div>
      <div className="text-sm text-gray-700">{children}</div>
    </div>
  )
}

/** 将各 Agent 的 focus 转为可读纯文本（回看已完成步骤用） */
export function focusToStreamText(agent: string, focus?: Record<string, unknown> | null): string {
  if (!focus) return ''

  if (agent === 'CasePlanner') {
    const objs = (focus.learning_objectives as Array<{ description?: string }> | undefined) || []
    const chars = (focus.characters as Array<{ name?: string; role?: string; stance?: string }> | undefined) || []
    return [
      '【决策点】',
      String(focus.decision_point || '—'),
      '',
      '【学习目标】',
      ...objs.map((o, i) => `${i + 1}. ${o.description || ''}`),
      '',
      '【角色立场】',
      ...chars.map((c) => `· ${c.name}（${c.role}）：${c.stance}`),
    ].join('\n')
  }

  if (agent === 'DomainExpert') {
    return [
      '【学科注释】',
      String(focus.domain_notes || '—'),
      '',
      '【背景片段】',
      String(focus.background || ''),
    ].join('\n')
  }

  if (agent === 'CaseWriter') {
    return [
      '【背景】',
      String(focus.background || ''),
      '',
      '【叙事】',
      String(focus.narrative || ''),
      '',
      '【决策点】',
      String(focus.decision_point || '—'),
    ].join('\n')
  }

  if (agent === 'PedagogyDesigner') {
    const qs = (focus.discussion_questions as Array<{ level?: string; question?: string }> | undefined) || []
    const guide = (focus.instructor_guide as { teaching_flow?: string } | undefined) || {}
    return [
      '【授课流程】',
      guide.teaching_flow || '—',
      '',
      '【讨论题】',
      ...qs.map((q, i) => `${i + 1}. [${q.level}] ${q.question}`),
    ].join('\n')
  }

  if (agent === 'Reviewer') {
    const quality =
      (focus.quality as {
        overall_score?: number
        reviewer_summary?: string
        rubric_scores?: Record<string, number>
      } | undefined) || {}
    const scores = quality.rubric_scores
      ? Object.entries(quality.rubric_scores)
          .map(([k, v]) => `· ${k}: ${v}`)
          .join('\n')
      : ''
    return [
      `【综合分】 ${quality.overall_score ?? '—'}`,
      '',
      '【评审摘要】',
      quality.reviewer_summary || '—',
      '',
      '【五维评分】',
      scores || '—',
    ].join('\n')
  }

  return JSON.stringify(focus, null, 2)
}

function ThinkingStream({ agent }: { agent: string }) {
  return (
    <div className="rounded-lg border border-amber-100 bg-amber-50/80 p-3">
      <p className="animate-pulse text-sm text-amber-900">{agent} 等待首个输出片段…</p>
      <p className="mt-1 text-xs text-amber-800/80">模型连接中，过程文本将在此实时显示</p>
      <div className="mt-3 h-1 overflow-hidden rounded bg-amber-100">
        <div className="h-full w-1/3 animate-pulse rounded bg-amber-400" />
      </div>
    </div>
  )
}

export function AgentStepPanel({
  selectedAgent,
  stepResults,
  taskMeta,
  stream,
}: {
  selectedAgent?: string
  stepResults: AgentStepResult[]
  taskMeta?: Record<string, unknown>
  stream?: AgentProgressMessage['stream']
}) {
  const [tab, setTab] = useState<'preview' | 'input' | 'json'>('preview')

  const step = useMemo(
    () => stepResults.find((s) => s.agent === selectedAgent) || stepResults[stepResults.length - 1],
    [stepResults, selectedAgent],
  )

  const agentName = step?.agent || selectedAgent || '—'
  const focusText = useMemo(() => focusToStreamText(agentName, step?.focus), [agentName, step?.focus])

  // 当前选中 Agent 正在被后端流式推送 → 用 stream.text（真打字）
  const isLiveStreaming = !!stream && stream.agent === agentName
  const previewText = isLiveStreaming ? stream!.text : focusText
  const showCursor = isLiveStreaming && !stream!.done

  if (!step && !taskMeta) {
    return (
      <Card className="sticky top-6 h-fit min-h-[320px] p-5">
        <h3 className="font-semibold text-gray-800">步骤过程数据</h3>
        <p className="mt-4 text-sm text-gray-500">等待 Agent 开始运行…</p>
      </Card>
    )
  }

  return (
    <Card className="sticky top-6 flex max-h-[calc(100vh-8rem)] flex-col overflow-hidden p-0">
      <div className="border-b bg-white p-4">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h3 className="font-semibold text-gray-900">
              {agentName}
              <span className="ml-2 text-sm font-normal text-gray-500">
                {AGENT_LABELS[agentName] || ''}
              </span>
            </h3>
            <p className="mt-1 text-xs text-gray-500 line-clamp-2">{step?.summary || '等待产出…'}</p>
          </div>
          {step?.status === 'completed' && <Badge variant="green">已完成</Badge>}
          {step?.status === 'running' && <Badge variant="yellow">生成中</Badge>}
        </div>
        <div className="mt-3 flex flex-wrap gap-3 text-xs text-gray-500">
          {step?.duration_ms != null && <span>耗时 {(step.duration_ms / 1000).toFixed(1)}s</span>}
          {step?.token_usage != null && <span>Token {step.token_usage}</span>}
          {showCursor && <span className="text-primary">流式输出中</span>}
          {!showCursor && previewText && step?.status === 'completed' && <span>全文已就绪</span>}
        </div>
        <div className="mt-3 flex gap-1">
          {(
            [
              ['preview', '过程预览'],
              ['input', '任务输入'],
              ['json', '原始 JSON'],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => setTab(id)}
              className={cn(
                'rounded-md px-3 py-1.5 text-xs',
                tab === id ? 'bg-primary text-white' : 'bg-gray-100 text-gray-600',
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {tab === 'preview' && (
          <div>
            {step?.status === 'running' && !previewText && <ThinkingStream agent={agentName} />}
            {previewText ? (
              <div className="mt-1 rounded-lg border border-gray-100 bg-white p-3 shadow-sm">
                <pre className="whitespace-pre-wrap break-words font-sans text-xs leading-relaxed text-gray-700">
                  {previewText}
                  {showCursor && (
                    <span className="ml-0.5 inline-block h-3.5 w-1.5 animate-pulse bg-primary align-middle" />
                  )}
                </pre>
              </div>
            ) : (
              step?.status !== 'running' && (
                <p className="text-sm text-gray-500">该步骤暂无预览数据</p>
              )
            )}
          </div>
        )}

        {tab === 'input' && (
          <div className="space-y-3 text-sm">
            {step?.input?.hint && <Field label="Agent 职责">{step.input.hint}</Field>}
            <Field label="教师任务参数">
              <pre className="overflow-x-auto rounded-lg bg-gray-50 p-3 text-[11px] leading-relaxed text-gray-700">
                {JSON.stringify(step?.input?.task || taskMeta || {}, null, 2)}
              </pre>
            </Field>
          </div>
        )}

        {tab === 'json' && (
          <pre className="overflow-x-auto rounded-lg bg-slate-900 p-3 text-[11px] leading-relaxed text-emerald-200">
            {JSON.stringify(
              {
                summary: step?.summary,
                focus: step?.focus,
                output: step?.output,
                stream: isLiveStreaming ? stream : undefined,
              },
              null,
              2,
            )}
          </pre>
        )}
      </div>
    </Card>
  )
}
