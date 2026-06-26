import { Link, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'

const features = [
  { icon: '📋', title: '案例四件套', desc: '正文、讨论题、教师参考、目标对齐表一次生成' },
  { icon: '🤖', title: 'AutoGen 多 Agent', desc: '多角色协作，非单轮 Chat' },
  { icon: '💡', title: '讨论价值优先', desc: 'Reviewer Agent Rubric 质量把关' },
  { icon: '📚', title: '学科可扩展', desc: 'Agent Prompt 按学科插件配置' },
  { icon: '✏️', title: '人机协同', desc: '局部重跑 Agent、人工编辑' },
  { icon: '📤', title: 'Word / PDF 导出', desc: '授课包直接用于课堂' },
]

const agents = [
  { name: 'CasePlanner', sub: '结构策划' },
  { name: 'DomainExpert', sub: '学科情境' },
  { name: 'CaseWriter', sub: '案例撰写' },
  { name: 'Pedagogy', sub: '讨论题设计' },
  { name: 'Reviewer', sub: '质量评审' },
]

export default function Landing() {
  const navigate = useNavigate()

  return (
    <div>
      <section className="bg-gradient-to-br from-teal-900 via-primary to-teal-500 px-6 py-20 text-center text-white">
        <h1 className="text-4xl font-extrabold md:text-5xl">AutoGen 教学案例自动生成系统</h1>
        <p className="mt-4 text-lg opacity-90">多智能体协作 · 20 分钟产出可授课案例包</p>
        <p className="mt-2 text-sm opacity-80">
          基于 Microsoft AutoGen · 策划 / 专家 / 撰写 / 教学设计 / 评审
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Button variant="heroSecondary" size="lg" onClick={() => navigate('/admin/agents')}>
            ⚙️ Agent 配置中心
          </Button>
          <Button variant="heroPrimary" size="lg" onClick={() => navigate('/case/new')}>
            创建教学案例 →
          </Button>
        </div>
        <div className="mx-auto mt-10 flex max-w-4xl flex-wrap items-center justify-center gap-2 rounded-2xl bg-white/10 p-6">
          {agents.map((a, i) => (
            <div key={a.name} className="flex items-center gap-2">
              <div className="rounded-lg bg-white px-3 py-2 text-center text-sm font-semibold text-gray-900">
                {a.name}
                <small className="block text-xs font-normal text-gray-500">{a.sub}</small>
              </div>
              {i < agents.length - 1 && <span className="text-white">→</span>}
            </div>
          ))}
        </div>
      </section>
      <section className="mx-auto grid max-w-5xl gap-6 px-6 py-16 md:grid-cols-3">
        {features.map((f) => (
          <Card key={f.title} className="text-center">
            <div className="text-3xl">{f.icon}</div>
            <h3 className="mt-3 font-semibold">{f.title}</h3>
            <p className="mt-2 text-sm text-gray-500">{f.desc}</p>
          </Card>
        ))}
      </section>
      <p className="pb-8 text-center text-xs text-gray-500">
        CaseAutoGenSystem · 教学案例生成，非学术论文 ·{' '}
        <Link to="/auth" className="text-primary">教师登录</Link>
      </p>
    </div>
  )
}
