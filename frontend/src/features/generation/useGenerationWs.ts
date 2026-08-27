import { useEffect, useRef, useState } from 'react'
import type { AgentProgressMessage } from '@/types/case'
import { getWsBaseUrl } from '@/lib/api-client'
import { fetchLiveProgress } from '@/features/cases/api'

const INITIAL: AgentProgressMessage = {
  type: 'agent_progress',
  overall_progress: 0,
  current_agent: 'CasePlanner',
  agents: [
    { name: 'CasePlanner', status: 'pending' },
    { name: 'DomainExpert', status: 'pending' },
    { name: 'CaseWriter', status: 'pending' },
    { name: 'PedagogyDesigner', status: 'pending' },
    { name: 'Reviewer', status: 'pending' },
  ],
  step_results: [],
}

function mergeProgress(
  prev: AgentProgressMessage | null,
  msg: AgentProgressMessage,
): AgentProgressMessage {
  const steps =
    msg.step_results && msg.step_results.length > 0
      ? msg.step_results
      : prev?.step_results || []

  // 新 agent 开始跑时，丢弃上一 agent 的旧 stream，避免右侧仍显示旧文/占位错乱
  let stream = msg.stream ?? prev?.stream
  if (
    stream &&
    msg.current_agent &&
    stream.agent !== msg.current_agent &&
    !msg.stream
  ) {
    stream = undefined
  }
  if (msg.stream) stream = msg.stream

  return {
    ...(prev || INITIAL),
    ...msg,
    type: 'agent_progress',
    step_results: steps,
    stream,
  }
}

/**
 * 进度订阅：WebSocket 实时推送，HTTP 低频轮询用于断线兜底。
 * WebSocket 走当前站点同源地址，由 Vite 在开发环境代理到后端。
 */
export function useGenerationWs(caseId: string | undefined) {
  const [progress, setProgress] = useState<AgentProgressMessage | null>(INITIAL)
  const stopped = useRef(false)

  useEffect(() => {
    if (!caseId) return
    stopped.current = false

    // --- HTTP 轮询（主通道）---
    const poll = window.setInterval(async () => {
      if (stopped.current) return
      try {
        const msg = (await fetchLiveProgress(caseId)) as AgentProgressMessage
        if (!msg || typeof msg !== 'object') return
        setProgress((prev) => mergeProgress(prev, { ...msg, type: 'agent_progress' }))
        if (msg.error || (msg.overall_progress >= 100 && (!msg.stream || msg.stream.done))) {
          // 结束后再多拉几次确保最后一帧，然后停
          window.setTimeout(() => {
            stopped.current = true
            window.clearInterval(poll)
          }, 1500)
        }
      } catch {
        /* ignore */
      }
    }, 1500)

    // --- WebSocket（辅通道，更快）---
    let ws: WebSocket | null = null
    try {
      ws = new WebSocket(`${getWsBaseUrl()}/ws/cases/${caseId}`)
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data) as AgentProgressMessage
          if (msg.type !== 'agent_progress') return
          setProgress((prev) => mergeProgress(prev, msg))
        } catch {
          /* ignore */
        }
      }
    } catch {
      /* ignore */
    }

    return () => {
      stopped.current = true
      window.clearInterval(poll)
      ws?.close()
    }
  }, [caseId])

  return progress
}
