import type { AgentProgressItem } from '@/types/case'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { cn } from '@/lib/utils'

export const AGENT_LABELS: Record<string, string> = {
  CasePlanner: '结构策划',
  DomainExpert: '学科情境',
  CaseWriter: '案例撰写',
  PedagogyDesigner: '讨论题设计',
  Reviewer: '质量评审',
  TeacherProxy: '任务代理',
}

/** 兼容历史任务：旧版本曾把模型 JSON 截断后作为摘要保存，展示前统一拦截。 */
export function readableAgentSummary(agent: string, summary?: string): string {
  if (!summary) return ''
  const value = summary.trim()
  const looksLikeProtocol =
    value.startsWith('{') ||
    value.startsWith('[') ||
    /"(?:outline|learning_objectives|domain_notes|background|narrative|quality)"\s*:/.test(value)
  if (looksLikeProtocol) {
    return `${AGENT_LABELS[agent] || '当前'}阶段结果已生成，请在右侧查看可读预览。`
  }
  return value
}

function StepIcon({ status }: { status: AgentProgressItem['status'] }) {
  if (status === 'completed') {
    return <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-100 text-green-600">✓</div>
  }
  if (status === 'running') {
    return (
      <div className="flex h-12 w-12 animate-pulse items-center justify-center rounded-full bg-primary-light text-primary">
        ⟳
      </div>
    )
  }
  if (status === 'failed') {
    return <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-100 text-red-600">!</div>
  }
  return <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gray-100 text-gray-400">○</div>
}

export function AgentPipeline({
  agents,
  overall,
  selectedAgent,
  onSelect,
}: {
  agents: AgentProgressItem[]
  overall: number
  selectedAgent?: string
  onSelect?: (name: string) => void
}) {
  return (
    <div>
      <div className="mb-8 text-center">
        <div className="mx-auto mb-3 flex h-24 w-24 items-center justify-center rounded-full bg-gradient-to-br from-primary to-teal-400 text-3xl font-bold text-white">
          {overall}%
        </div>
        <h2 className="text-xl font-bold">AI 教研团队协作中</h2>
        <p className="mt-2 text-sm text-gray-500">选择任一环节，查看当前思路与阶段产出</p>
      </div>
      <div className="space-y-0">
        {agents.map((agent, i) => (
          <button
            key={agent.name}
            type="button"
            onClick={() => onSelect?.(agent.name)}
            className={cn(
              'relative flex w-full gap-5 pb-7 text-left',
              selectedAgent === agent.name && 'opacity-100',
            )}
          >
            {i < agents.length - 1 && (
              <div className="absolute left-6 top-12 h-[calc(100%-24px)] w-0.5 bg-gray-200" />
            )}
            <StepIcon status={agent.status} />
            <Card
              className={cn(
                'flex-1 p-4 transition ring-offset-2',
                selectedAgent === agent.name && 'ring-2 ring-primary',
              )}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h4 className="font-semibold">
                  {agent.name}
                  <span className="ml-2 text-xs font-normal text-gray-500">
                    {AGENT_LABELS[agent.name] || ''}
                  </span>
                </h4>
                {agent.status === 'completed' && <Badge variant="green">完成</Badge>}
                {agent.status === 'running' && <Badge variant="yellow">运行中</Badge>}
                {agent.status === 'pending' && <Badge variant="gray">等待</Badge>}
                {agent.status === 'failed' && <Badge variant="red">失败</Badge>}
              </div>
              {agent.output_summary && (
                <p className="mt-2 rounded-lg bg-gray-50 p-3 text-xs text-gray-600 line-clamp-3">
                  {readableAgentSummary(agent.name, agent.output_summary)}
                </p>
              )}
              {agent.status === 'running' && agent.progress != null && (
                <div className="mt-2 h-1 overflow-hidden rounded bg-gray-200">
                  <div className="h-full bg-primary" style={{ width: `${agent.progress}%` }} />
                </div>
              )}
              {(agent.duration_ms || agent.token_usage) && (
                <p className="mt-2 text-xs text-gray-400">
                  {agent.duration_ms ? `${(agent.duration_ms / 1000).toFixed(1)}s` : ''}
                  {agent.duration_ms && agent.token_usage ? ' · ' : ''}
                  {agent.token_usage ? `${agent.token_usage} tokens` : ''}
                </p>
              )}
            </Card>
          </button>
        ))}
      </div>
    </div>
  )
}
