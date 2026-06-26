import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Input, Label } from '@/components/ui/Input'
import { AdminSubSection } from '@/components/layout/AdminLayout'

const AGENTS = [
  { name: 'CasePlanner', role: '设计案例结构、决策点、教学目标对齐', model: 'gpt-4o', version: 'v1.2', tools: 2 },
  { name: 'DomainExpert', role: '补充学科情境、行业术语', model: 'gpt-4o', version: 'v1.1', tools: 2 },
  { name: 'CaseWriter', role: '撰写案例正文叙事', model: 'gpt-4o', version: 'v1.3', tools: 3 },
  { name: 'PedagogyDesigner', role: '设计分层讨论题与课堂活动', model: 'gpt-4o', version: 'v1.0', tools: 2 },
  { name: 'Reviewer', role: 'Rubric 评分与修订建议', model: 'deepseek-chat', version: 'v1.1', tools: 2 },
]

export default function AgentConfig() {
  return (
    <div>
      <AdminSubSection id="agent-list" title="Agent 角色配置" description="定义每个 AutoGen Agent 的职责、Prompt、模型与工具">
        <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
          {['L1 全局层', 'L2 角色层 ★', 'L3 编排层', 'L4 学科层'].map((l) => (
            <Card key={l} className="p-3 text-xs text-gray-500">{l}</Card>
          ))}
        </div>
        <Card className="overflow-hidden p-0">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs text-gray-500">
              <tr>
                <th className="p-3">Agent</th>
                <th className="p-3">职责</th>
                <th className="p-3">模型</th>
                <th className="p-3">版本</th>
                <th className="p-3">Tool</th>
              </tr>
            </thead>
            <tbody>
              {AGENTS.map((a) => (
                <tr key={a.name} className="border-t hover:bg-gray-50">
                  <td className="p-3 font-semibold">{a.name}</td>
                  <td className="p-3 text-gray-500">{a.role}</td>
                  <td className="p-3">{a.model}</td>
                  <td className="p-3"><Badge variant="teal">{a.version} ★</Badge></td>
                  <td className="p-3">{a.tools}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </AdminSubSection>

      <AdminSubSection id="workflow" title="编排模板管理" description="Sequential / GroupChat 流水线">
        <Card>
          <h3 className="font-semibold">sequential_standard <Badge variant="green">默认</Badge></h3>
          <p className="mt-1 text-sm text-gray-500">TeacherProxy → Planner → Expert → Writer → Pedagogy → Reviewer</p>
        </Card>
      </AdminSubSection>

      <AdminSubSection id="tools" title="Tool 工具注册">
        <Card className="p-0 text-sm">
          <ul className="divide-y">
            {['validate_case_schema', 'load_subject_template', 'compute_rubric_score', 'check_content_safety'].map((t) => (
              <li key={t} className="flex justify-between p-3">
                <span>{t}</span>
                <Badge variant="green">启用</Badge>
              </li>
            ))}
          </ul>
        </Card>
      </AdminSubSection>

      <AdminSubSection id="subjects" title="学科插件包">
        <div className="grid gap-4 md:grid-cols-3">
          {['管理学', '计算机', '经济学'].map((s) => (
            <Card key={s}>
              <h4 className="font-semibold">{s}</h4>
              <p className="mt-2 text-xs text-gray-500">template_outline.json · terminology.json</p>
            </Card>
          ))}
        </div>
      </AdminSubSection>

      <AdminSubSection id="global" title="全局设置">
        <Card className="max-w-lg space-y-4">
          <div>
            <Label>Reviewer 通过阈值</Label>
            <Input type="number" value={4.0} readOnly />
          </div>
          <div>
            <Label>单任务 Token 预算</Label>
            <Input type="number" value={50000} readOnly />
          </div>
          <Button>保存全局设置</Button>
        </Card>
      </AdminSubSection>

      <AdminSubSection id="monitor" title="运行监控">
        <div className="grid grid-cols-3 gap-4">
          <Card className="text-center"><div className="text-2xl font-bold text-primary">12.4s</div><div className="text-xs text-gray-500">Planner 耗时</div></Card>
          <Card className="text-center"><div className="text-2xl font-bold text-primary">28.6s</div><div className="text-xs text-gray-500">Writer 耗时</div></Card>
          <Card className="text-center"><div className="text-2xl font-bold text-primary">81.2</div><div className="text-xs text-gray-500">Rubric 均分</div></Card>
        </div>
      </AdminSubSection>
    </div>
  )
}
