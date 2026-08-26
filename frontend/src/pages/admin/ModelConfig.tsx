import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AdminSubSection } from '@/components/layout/AdminLayout'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Input, Label } from '@/components/ui/Input'
import {
  fetchModelConfig,
  testModelConfig,
  updateModelConfig,
} from '@/features/cases/api'

function errorDetail(error: unknown, fallback: string) {
  return String(
    (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || fallback,
  )
}

export default function ModelConfig() {
  const qc = useQueryClient()
  const [enabled, setEnabled] = useState(false)
  const [apiBase, setApiBase] = useState('https://api.openai.com/v1')
  const [model, setModel] = useState('gpt-4o')
  const [apiKey, setApiKey] = useState('')
  const [message, setMessage] = useState('')
  const query = useQuery({ queryKey: ['admin-model-config'], queryFn: fetchModelConfig })

  useEffect(() => {
    if (!query.data) return
    setEnabled(query.data.enabled)
    setApiBase(query.data.api_base)
    setModel(query.data.model)
  }, [query.data])

  const save = useMutation({
    mutationFn: () =>
      updateModelConfig({
        enabled,
        api_base: apiBase,
        model,
        ...(apiKey.trim() ? { api_key: apiKey.trim() } : {}),
      }),
    onSuccess: async () => {
      setApiKey('')
      setMessage('配置已保存并即时生效，无需重启服务。')
      await qc.invalidateQueries({ queryKey: ['admin-model-config'] })
    },
    onError: (error) => setMessage(errorDetail(error, '保存失败')),
  })

  const test = useMutation({
    mutationFn: testModelConfig,
    onSuccess: (data) => setMessage(`连接成功：${data.model}`),
    onError: (error) => setMessage(errorDetail(error, '连接测试失败')),
  })

  return (
    <AdminSubSection
      id="model-config"
      title="大模型配置"
      description="配置 OpenAI Chat Completions 兼容服务；保存后立即用于全部案例生成任务"
    >
      <div className="grid max-w-3xl gap-5">
        <Card className="flex items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 font-semibold text-slate-900">
              运行状态
              {query.data?.available ? <Badge variant="green">可用</Badge> : <Badge variant="gray">未就绪</Badge>}
            </div>
            <p className="mt-1 text-sm text-slate-500">
              {query.data?.api_key_configured ? 'API Key 已安全保存' : '尚未保存 API Key'}
            </p>
          </div>
          <label className="flex cursor-pointer items-center gap-2 text-sm font-semibold text-slate-700">
            <input
              type="checkbox"
              className="h-5 w-5 accent-indigo-600"
              checked={enabled}
              onChange={(event) => setEnabled(event.target.checked)}
            />
            启用大模型
          </label>
        </Card>

        <Card className="space-y-5">
          {query.isLoading && <p className="text-sm text-slate-500">正在读取配置…</p>}
          {query.isError && <p className="text-sm text-red-600">配置读取失败，请刷新重试。</p>}
          <div>
            <Label htmlFor="api-base">接口地址</Label>
            <Input
              id="api-base"
              value={apiBase}
              onChange={(event) => setApiBase(event.target.value)}
              placeholder="https://api.openai.com/v1"
            />
            <p className="mt-1 text-xs text-slate-500">支持 OpenAI、DeepSeek 及其他兼容 Chat Completions 的服务。</p>
          </div>
          <div>
            <Label htmlFor="model-name">模型名称</Label>
            <Input
              id="model-name"
              value={model}
              onChange={(event) => setModel(event.target.value)}
              placeholder="例如：gpt-4o、deepseek-chat"
            />
          </div>
          <div>
            <Label htmlFor="api-key">API Key</Label>
            <Input
              id="api-key"
              type="password"
              autoComplete="new-password"
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              placeholder={query.data?.api_key_configured ? '已配置；留空表示保持不变' : '请输入 API Key'}
            />
            <p className="mt-1 text-xs text-slate-500">
              密钥在服务端加密保存，接口和页面均不会回显明文。
            </p>
          </div>
          {message && (
            <p className={`rounded-lg px-3 py-2 text-sm ${message.includes('失败') || message.includes('请') ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700'}`}>
              {message}
            </p>
          )}
          <div className="flex flex-wrap gap-3">
            <Button disabled={save.isPending || !apiBase.trim() || !model.trim()} onClick={() => save.mutate()}>
              {save.isPending ? '保存中…' : '保存配置'}
            </Button>
            <Button variant="outline" disabled={test.isPending || !query.data?.api_key_configured} onClick={() => test.mutate()}>
              {test.isPending ? '测试中…' : '测试连接'}
            </Button>
          </div>
        </Card>

        <Card className="border-amber-200 bg-amber-50 text-sm text-amber-900">
          管理员需要从模型服务商获取自己的 API Key。系统不会内置或展示任何第三方密钥；正式环境请保持 HTTPS。
        </Card>
      </div>
    </AdminSubSection>
  )
}
