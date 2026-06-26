import { useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { AgentPipeline } from '@/features/generation/AgentPipeline'
import { useGenerationWs } from '@/features/generation/useGenerationWs'
import { startGeneration } from '@/features/cases/api'

export default function GenerationMonitor() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const progress = useGenerationWs(id, true)

  useEffect(() => {
    if (id) startGeneration(id)
  }, [id])

  if (!progress) return <div className="text-gray-500">连接生成任务…</div>

  return (
    <div>
      <AgentPipeline agents={progress.agents} overall={progress.overall_progress} />
      <div className="mt-8 flex justify-center gap-3">
        <Button variant="outline" onClick={() => navigate('/dashboard')}>返回工作台</Button>
        <Button onClick={() => navigate(`/case/${id}`)}>预览已完成部分</Button>
      </div>
    </div>
  )
}
