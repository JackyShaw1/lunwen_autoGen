import { Link, useNavigate } from 'react-router-dom'
import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  FileCheck2,
  GraduationCap,
  Image as ImageIcon,
  ShieldCheck,
  Sparkles,
  TimerReset,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'

const outcomes = [
  {
    icon: FileCheck2,
    title: '一次生成完整授课包',
    desc: '案例正文、分层讨论题、教师参考与教学目标对齐表，无需来回拼接。',
  },
  {
    icon: GraduationCap,
    title: '围绕课堂效果设计',
    desc: '从学习目标反推情境冲突和讨论路径，让案例真正可教、可讨论。',
  },
  {
    icon: ImageIcon,
    title: '权威图片带回课堂现场',
    desc: '按主题推荐政府或机构官网素材，保留来源、摄影者和使用提示，并同步进入授课包与课件。',
  },
]

const steps = [
  ['01', '描述课程与目标', '填写主题、学生层次和希望达成的课堂目标'],
  ['02', 'AI 教研团队协作', '策划、学科、写作、教学设计和质量评审依次完成'],
  ['03', '审阅并投入课堂', '在线修改并选择官方素材后，导出 Word、PDF 或 PPTX'],
]

export default function Landing() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-white text-slate-950">
      <header className="sticky top-0 z-20 border-b border-slate-200/70 bg-white/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 lg:px-8">
          <Link to="/" className="flex items-center gap-3 text-slate-950 no-underline">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-white shadow-sm">
              <BookOpen size={20} />
            </span>
            <span>
              <strong className="block text-sm leading-4">知案</strong>
              <span className="text-[11px] text-slate-500">AI 教学案例工作台</span>
            </span>
          </Link>
          <div className="flex items-center gap-2">
            <Link to="/auth" className="px-3 py-2 text-sm font-medium text-slate-600 hover:text-slate-950">
              登录
            </Link>
            <Button size="sm" onClick={() => navigate('/register')}>免费注册 <ArrowRight size={15} /></Button>
          </div>
        </div>
      </header>

      <main>
        <section className="relative overflow-hidden border-b border-slate-200 bg-slate-950">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_20%,rgba(99,102,241,0.32),transparent_35%),radial-gradient(circle_at_20%_80%,rgba(14,165,233,0.18),transparent_30%)]" />
          <div className="relative mx-auto grid max-w-7xl items-center gap-14 px-5 py-20 lg:grid-cols-[1.1fr_.9fr] lg:px-8 lg:py-28">
            <div>
              <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-indigo-400/30 bg-indigo-400/10 px-3 py-1.5 text-sm font-medium text-indigo-200">
                <Sparkles size={15} /> 为高校教师打造的 AI 教研助手
              </div>
              <h1 className="max-w-3xl text-4xl font-bold tracking-tight text-white md:text-6xl md:leading-[1.12]">
                把课程目标，变成一套
                <span className="text-indigo-300">真正可上课</span>的教学案例
              </h1>
              <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">
                从情境设计到质量评审，多角色 AI 协同完成案例授课包。教师专注判断与教学，重复写作交给系统。
              </p>
              <div className="mt-9 flex flex-wrap items-center gap-3">
                <Button variant="heroPrimary" size="lg" onClick={() => navigate('/register')}>免费创建账号 <ArrowRight size={18} /></Button>
                <a href="#workflow" className="rounded-xl px-5 py-3 text-sm font-semibold text-slate-300 hover:bg-white/10 hover:text-white">
                  查看工作方式
                </a>
              </div>
              <div className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm text-slate-400">
                <span className="flex items-center gap-2"><ShieldCheck size={16} className="text-emerald-400" /> 教师全程可控</span>
                <span className="flex items-center gap-2"><CheckCircle2 size={16} className="text-emerald-400" /> 支持 Word / PDF / PPTX</span>
                <span className="flex items-center gap-2"><TimerReset size={16} className="text-emerald-400" /> 节省约 8 小时/案例</span>
              </div>
            </div>

            <div className="rounded-3xl border border-white/10 bg-white/5 p-3 shadow-2xl shadow-indigo-950/50 backdrop-blur">
              <div className="rounded-2xl bg-white p-6">
                <div className="flex items-start justify-between border-b border-slate-100 pb-5">
                  <div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-primary">案例授课包</span>
                    <h2 className="mt-1 text-lg font-bold">数字化转型中的组织阻力</h2>
                    <p className="mt-1 text-xs text-slate-500">组织行为学 · 本科 · 2 课时</p>
                  </div>
                  <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">质量评分 4.7</span>
                </div>
                <div className="space-y-3 py-5">
                  {['案例正文与关键决策点', '权威官网图片与来源', '分层讨论题与授课流程', '学习目标对齐矩阵'].map((item, index) => (
                    <div key={item} className="flex items-center gap-3 rounded-xl bg-slate-50 px-4 py-3">
                      <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-100 text-xs font-bold text-primary">{index + 1}</span>
                      <span className="text-sm font-medium text-slate-700">{item}</span>
                      <CheckCircle2 size={16} className="ml-auto text-emerald-500" />
                    </div>
                  ))}
                </div>
                <div className="flex items-center justify-between rounded-xl bg-indigo-50 px-4 py-3 text-sm">
                  <span className="font-medium text-indigo-950">已完成 5 轮专业协作</span>
                  <span className="text-indigo-600">准备导出 →</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-5 py-20 lg:px-8">
          <div className="max-w-2xl">
            <p className="text-sm font-bold uppercase tracking-widest text-primary">面向真实教学成果</p>
            <h2 className="mt-3 text-3xl font-bold tracking-tight md:text-4xl">不是生成更多文字，而是减少备课摩擦</h2>
            <p className="mt-4 text-slate-600">每一项能力都对应教师工作流中的具体耗时点。</p>
          </div>
          <div className="mt-10 grid gap-5 md:grid-cols-3">
            {outcomes.map(({ icon: Icon, title, desc }) => (
              <article key={title} className="rounded-2xl border border-slate-200 bg-white p-7 shadow-sm transition hover:-translate-y-1 hover:shadow-soft">
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-50 text-primary"><Icon size={22} /></span>
                <h3 className="mt-5 text-lg font-bold">{title}</h3>
                <p className="mt-3 text-sm leading-6 text-slate-600">{desc}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="workflow" className="border-y border-slate-200 bg-slate-50">
          <div className="mx-auto max-w-7xl px-5 py-20 lg:px-8">
            <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
              <div>
                <p className="text-sm font-bold uppercase tracking-widest text-primary">三步完成</p>
                <h2 className="mt-3 text-3xl font-bold">从想法到授课包，过程清晰可控</h2>
              </div>
              <p className="max-w-md text-sm leading-6 text-slate-600">系统展示每个专业角色的工作进度与产出，教师可以随时查看、修改并保存为新版本。</p>
            </div>
            <div className="mt-10 grid gap-5 md:grid-cols-3">
              {steps.map(([number, title, desc]) => (
                <div key={number} className="relative overflow-hidden rounded-2xl bg-white p-7 shadow-sm ring-1 ring-slate-200">
                  <span className="text-4xl font-black text-indigo-100">{number}</span>
                  <h3 className="mt-4 text-lg font-bold">{title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      <footer className="bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-5 py-8 text-sm text-slate-500 md:flex-row md:items-center md:justify-between lg:px-8">
          <span>© 2026 知案 · AI 教学案例工作台</span>
          <span>教学案例生成，不用于学术论文代写</span>
        </div>
      </footer>
    </div>
  )
}
