import { useEffect, useMemo, useRef, useState } from 'react'
import type { AgentProgressMessage, AgentStepResult } from '@/types/case'
import { AGENT_LABELS, readableAgentSummary } from './AgentPipeline'
import { Badge } from '@/components/ui/Badge'
import { Card } from '@/components/ui/Card'

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

  return '本步骤已完成，请查看节点结果摘要。'
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

/**
 * 服务端 WebSocket 和 HTTP 轮询都只负责更新目标文本；逐字动画由浏览器完成。
 * 因此即使代理网关合并了数据帧，教师仍能看到稳定、连续的打字效果。
 */
function useTypewriter(target: string, resetKey: string, enabled: boolean): string {
  const [displayed, setDisplayed] = useState(enabled ? '' : target)
  const displayedRef = useRef(displayed)
  const targetRef = useRef(target)

  useEffect(() => {
    targetRef.current = target
    if (!enabled) {
      displayedRef.current = target
      setDisplayed(target)
      return
    }
    if (!target.startsWith(displayedRef.current)) {
      displayedRef.current = ''
      setDisplayed('')
    }
  }, [target, enabled])

  useEffect(() => {
    if (!enabled) return
    displayedRef.current = ''
    setDisplayed('')
    const timer = window.setInterval(() => {
      const goal = targetRef.current
      let current = displayedRef.current
      if (!goal.startsWith(current)) current = ''
      if (current.length >= goal.length) return
      const remaining = goal.length - current.length
      const chars = remaining > 600 ? 10 : remaining > 240 ? 6 : remaining > 80 ? 3 : 1
      const next = goal.slice(0, current.length + chars)
      displayedRef.current = next
      setDisplayed(next)
    }, 20)
    return () => window.clearInterval(timer)
  }, [enabled, resetKey])

  return displayed
}

export function AgentStepPanel({
  selectedAgent,
  stepResults,
  stream,
}: {
  selectedAgent?: string
  stepResults: AgentStepResult[]
  taskMeta?: Record<string, unknown>
  stream?: AgentProgressMessage['stream']
}) {
  const step = useMemo(
    () => stepResults.find((s) => s.agent === selectedAgent) || stepResults[stepResults.length - 1],
    [stepResults, selectedAgent],
  )

  const agentName = step?.agent || selectedAgent || '—'
  const focusText = useMemo(() => focusToStreamText(agentName, step?.focus), [agentName, step?.focus])

  // 当前选中 Agent 正在被后端流式推送 → 用 stream.text（真打字）
  const isLiveStreaming = !!stream && stream.agent === agentName
  const streamTarget = isLiveStreaming ? stream!.text : ''
  const typedStreamText = useTypewriter(streamTarget, agentName, isLiveStreaming)
  const previewText = isLiveStreaming ? typedStreamText : focusText
  const showCursor =
    isLiveStreaming && (!stream!.done || typedStreamText.length < streamTarget.length)

  if (!step) {
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
            <p className="mt-1 text-xs text-gray-500 line-clamp-2">
              {readableAgentSummary(agentName, step?.summary) || '等待产出…'}
            </p>
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
        <div className="mt-3 text-xs font-semibold text-primary">过程结果</div>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
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
            step?.status !== 'running' && <p className="text-sm text-gray-500">该步骤暂无结果</p>
          )}
        </div>
      </div>
    </Card>
  )
}
