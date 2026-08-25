import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { AgentPipeline, AGENT_LABELS } from '@/features/generation/AgentPipeline'
import { AgentStepPanel } from '@/features/generation/AgentStepPanel'
import { useGenerationWs } from '@/features/generation/useGenerationWs'
import { fetchCaseStatus, startGeneration } from '@/features/cases/api'

export default function GenerationMonitor() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const progress = useGenerationWs(id)
  const started = useRef(false)
  const [selectedAgent, setSelectedAgent] = useState<string>('CasePlanner')
  const [autoJump, setAutoJump] = useState(true)
  const [manualSelect, setManualSelect] = useState(false)
  const [retrying, setRetrying] = useState(false)

  useEffect(() => {
    if (!id || started.current) return
    started.current = true
    const resume = searchParams.get('resume') === '1'

    const boot = async () => {
      try {
        if (resume) return
        const st = await fetchCaseStatus(id)
        if (st.status === 'running') return
        if (st.status === 'finalized' || st.status === 'completed') {
          navigate(`/case/${id}`, { replace: true })
          return
        }
        if (st.status === 'failed') return
        await startGeneration(id)
      } catch (err: unknown) {
        console.error(err)
        alert(
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
            '启动生成失败',
        )
      }
    }
    void boot()
  }, [id, searchParams, navigate])

  // 跟随进度：流式输出中锁定该 Agent；否则跟随 running / current
  useEffect(() => {
    if (!progress || manualSelect) return
    if (progress.stream?.agent) {
      setSelectedAgent(progress.stream.agent)
      return
    }
    const running = progress.agents.find((a) => a.status === 'running')
    if (running) {
      setSelectedAgent(running.name)
      return
    }
    if (progress.current_agent) setSelectedAgent(progress.current_agent)
  }, [progress, manualSelect])

  useEffect(() => {
    if (!autoJump) return
    // 全部完成且最后一段流也结束才跳转
    const streamDone = !progress?.stream || progress.stream.done
    if (progress && progress.overall_progress >= 100 && streamDone) {
      const t = window.setTimeout(() => navigate(`/case/${id}`), 2000)
      return () => window.clearTimeout(t)
    }
  }, [progress, id, navigate, autoJump])

  if (!progress) return <div className="text-gray-500">连接生成任务…</div>

  const title = (progress.task_meta?.title as string) || '教学案例生成'
  const remain = progress.estimated_remaining_seconds
  const streaming = progress.stream && !progress.stream.done

  const retry = async () => {
    if (!id || retrying) return
    setRetrying(true)
    try {
      await startGeneration(id)
      setManualSelect(false)
      setAutoJump(true)
    } catch (err: unknown) {
      alert(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          '重新生成失败',
      )
    } finally {
      setRetrying(false)
    }
  }

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">{title}</h1>
          <p className="mt-1 text-sm text-gray-500">
            五个专业角色正在依次完成策划、写作与质量评审
            {remain != null && remain > 0 ? ` · 预计剩余约 ${Math.ceil(remain / 60)} 分钟` : ''}
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            <Badge variant="teal">整体进度 {progress.overall_progress}%</Badge>
            {progress.current_agent && <Badge variant="yellow">当前：{AGENT_LABELS[progress.current_agent] || progress.current_agent}</Badge>}
            {streaming && <Badge variant="blue">正在形成阶段产出</Badge>}
          </div>
        </div>
        <label className="flex items-center gap-2 text-xs text-gray-500">
          <input
            type="checkbox"
            checked={autoJump}
            onChange={(e) => setAutoJump(e.target.checked)}
          />
          完成后自动跳转详情
        </label>
      </div>

      {progress.error && (
        <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          <div className="font-bold">
            {progress.failure_stage === 'quality_gate' ? '最终质量校验未通过' : '生成环节执行失败'}
          </div>
          <p className="mt-1 leading-6">{progress.error}</p>
          <Button className="mt-3" variant="outline" onClick={() => void retry()} disabled={retrying}>
            {retrying ? '正在重新启动…' : '重新生成'}
          </Button>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(320px,420px)]">
        <div>
          <AgentPipeline
            agents={progress.agents}
            overall={progress.overall_progress}
            selectedAgent={selectedAgent}
            onSelect={(name) => {
              setSelectedAgent(name)
              setManualSelect(true)
              setAutoJump(false)
            }}
          />
          <div className="mt-6 flex justify-center gap-3">
            <Button variant="outline" onClick={() => navigate('/dashboard')}>
              返回工作台
            </Button>
            <Button
              disabled={progress.overall_progress < 100}
              onClick={() => navigate(`/case/${id}`)}
            >
              {progress.overall_progress >= 100 ? '查看案例' : '生成中…'}
            </Button>
          </div>
        </div>

        <AgentStepPanel
          selectedAgent={selectedAgent}
          stepResults={progress.step_results || []}
          taskMeta={progress.task_meta}
          stream={progress.stream}
        />
      </div>
    </div>
  )
}
