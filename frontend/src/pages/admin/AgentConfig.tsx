import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Input, Label, Textarea } from '@/components/ui/Input'
import { AdminSubSection } from '@/components/layout/AdminLayout'
import { fetchAgentConfig, fetchAgents, updateAgentConfig } from '@/features/cases/api'
import { authStore } from '@/stores/authStore'

export default function AgentConfig() {
  const qc = useQueryClient()
  const isAdmin = authStore.getState().isAdmin()
  const [selected, setSelected] = useState<string | null>(null)
  const [yamlText, setYamlText] = useState('')
  const [loadError, setLoadError] = useState('')

  const { data: agents = [], isLoading, error, refetch } = useQuery({
    queryKey: ['admin-agents'],
    queryFn: fetchAgents,
    retry: 1,
  })

  const detailQ = useQuery({
    queryKey: ['admin-agent', selected],
    queryFn: () => fetchAgentConfig(selected!),
    enabled: !!selected,
  })

  const saveMut = useMutation({
    mutationFn: () => updateAgentConfig(selected!, yamlText),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-agents'] })
      qc.invalidateQueries({ queryKey: ['admin-agent', selected] })
      alert('配置已保存')
    },
    onError: (e: unknown) => {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      alert(detail || '保存失败（需要管理员权限）')
    },
  })

  const openEditor = async (name: string) => {
    setLoadError('')
    setSelected(name)
    try {
      const cfg = await fetchAgentConfig(name)
      setYamlText(cfg.config_yaml)
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setLoadError(String(detail || '加载 YAML 失败'))
    }
  }

  return (
    <div>
      <AdminSubSection
        id="agent-list"
        title="Agent 角色配置"
        description="查看各 AutoGen Agent 的职责与 Prompt；管理员可编辑 YAML"
      >
        {!isAdmin && (
          <p className="mb-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
            当前为教师账号：可查看配置。编辑保存请使用管理员账号登录。
          </p>
        )}
        {isLoading && <p className="text-sm text-gray-500">加载中…</p>}
        {error && (
          <div className="mb-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">
            无法加载 Agent 配置，请确认已登录且后端可用。
            <Button className="ml-3" size="sm" variant="outline" onClick={() => refetch()}>
              重试
            </Button>
          </div>
        )}
        <Card className="overflow-hidden p-0">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs text-gray-500">
              <tr>
                <th className="p-3">Agent</th>
                <th className="p-3">职责</th>
                <th className="p-3">版本</th>
                <th className="p-3">状态</th>
                <th className="p-3">操作</th>
              </tr>
            </thead>
            <tbody>
              {agents.length === 0 && !isLoading && !error && (
                <tr>
                  <td colSpan={5} className="p-6 text-center text-gray-500">
                    暂无 Agent 配置数据
                  </td>
                </tr>
              )}
              {agents.map((a) => (
                <tr key={a.agent_name} className="border-t hover:bg-gray-50">
                  <td className="p-3 font-semibold">{a.agent_name}</td>
                  <td className="p-3 text-gray-500">{a.description}</td>
                  <td className="p-3">
                    <Badge variant="teal">{a.version}</Badge>
                  </td>
                  <td className="p-3">
                    {a.is_active ? (
                      <Badge variant="green">启用</Badge>
                    ) : (
                      <Badge variant="gray">停用</Badge>
                    )}
                  </td>
                  <td className="p-3">
                    <Button size="sm" variant="outline" onClick={() => openEditor(a.agent_name)}>
                      {isAdmin ? '编辑 YAML' : '查看 YAML'}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </AdminSubSection>

      {selected && (
        <AdminSubSection id="prompt-editor" title={`${isAdmin ? '编辑' : '查看'} ${selected}`} description={detailQ.data?.version}>
          <Card className="space-y-3">
            {loadError && <p className="text-sm text-red-600">{loadError}</p>}
            <Textarea
              rows={18}
              className="font-mono text-xs"
              value={yamlText}
              readOnly={!isAdmin}
              onChange={(e) => isAdmin && setYamlText(e.target.value)}
            />
            <div className="flex gap-2">
              {isAdmin && (
                <Button disabled={saveMut.isPending} onClick={() => saveMut.mutate()}>
                  {saveMut.isPending ? '保存中…' : '保存并激活'}
                </Button>
              )}
              <Button variant="outline" onClick={() => setSelected(null)}>
                关闭
              </Button>
            </div>
          </Card>
        </AdminSubSection>
      )}

      <AdminSubSection id="workflow" title="编排模板管理" description="Sequential / GroupChat 流水线">
        <Card>
          <h3 className="font-semibold">
            sequential_standard <Badge variant="green">默认</Badge>
          </h3>
          <p className="mt-1 text-sm text-gray-500">
            CasePlanner → DomainExpert → CaseWriter → PedagogyDesigner → Reviewer
          </p>
        </Card>
      </AdminSubSection>

      <AdminSubSection id="global" title="全局设置">
        <Card className="max-w-lg space-y-4">
          <div>
            <Label>Reviewer 通过阈值</Label>
            <Input type="number" value={4.0} readOnly />
          </div>
          <p className="text-xs text-gray-500">阈值由后端 REVIEWER_PASS_THRESHOLD 环境变量控制</p>
        </Card>
      </AdminSubSection>
    </div>
  )
}
