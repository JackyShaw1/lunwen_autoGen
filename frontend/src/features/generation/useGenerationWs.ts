import { useEffect, useState } from 'react'
import type { AgentProgressMessage } from '@/types/case'
import { getWsBaseUrl } from '@/lib/api-client'

const DEMO_PROGRESS: AgentProgressMessage = {
  type: 'agent_progress',
  overall_progress: 60,
  current_agent: 'CaseWriter',
  agents: [
    { name: 'CasePlanner', status: 'completed', duration_ms: 11000, output_summary: '大纲 JSON：4章，核心决策点已定义' },
    { name: 'DomainExpert', status: 'completed', duration_ms: 14000 },
    { name: 'CaseWriter', status: 'running', progress: 60, output_summary: '正在撰写正文…' },
    { name: 'PedagogyDesigner', status: 'pending' },
    { name: 'Reviewer', status: 'pending' },
  ],
  estimated_remaining_seconds: 420,
}

export function useGenerationWs(caseId: string | undefined, useDemo = true) {
  const [progress, setProgress] = useState<AgentProgressMessage | null>(
    useDemo ? DEMO_PROGRESS : null,
  )

  useEffect(() => {
    if (!caseId || useDemo) return

    const ws = new WebSocket(`${getWsBaseUrl()}/ws/cases/${caseId}`)
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data) as AgentProgressMessage
      if (msg.type === 'agent_progress') setProgress(msg)
      if (msg.overall_progress >= 100) ws.close()
    }
    return () => ws.close()
  }, [caseId, useDemo])

  return progress
}
