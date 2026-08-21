import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, BookOpen, CheckCircle2, LockKeyhole, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input, Label } from '@/components/ui/Input'
import { loginApi } from '@/features/cases/api'
import { authStore } from '@/stores/authStore'

export default function Auth() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleLogin = async (event: FormEvent) => {
    event.preventDefault()
    if (!email || !password) {
      setError('请输入邮箱和密码')
      return
    }
    setLoading(true)
    setError('')
    try {
      const data = await loginApi(email, password, rememberMe)
      authStore.getState().login(data.user, data.access_token)
      navigate(data.user.role === 'admin' ? '/admin/agents' : '/dashboard')
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        '登录失败，请检查邮箱与密码'
      setError(String(msg))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid min-h-screen bg-white lg:grid-cols-[1.05fr_.95fr]">
      <section className="relative hidden overflow-hidden bg-slate-950 p-12 text-white lg:flex lg:flex-col">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(99,102,241,0.3),transparent_32%),radial-gradient(circle_at_90%_85%,rgba(14,165,233,0.18),transparent_30%)]" />
        <Link to="/" className="relative flex items-center gap-3 text-white no-underline">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary"><BookOpen size={21} /></span>
          <span><strong className="block">知案</strong><small className="text-slate-400">AI 教学案例工作台</small></span>
        </Link>
        <div className="relative my-auto max-w-xl">
          <span className="inline-flex items-center gap-2 rounded-full border border-indigo-400/30 bg-indigo-400/10 px-3 py-1.5 text-sm text-indigo-200">
            <Sparkles size={15} /> 让备课时间回到教学本身
          </span>
          <h1 className="mt-6 text-4xl font-bold leading-tight">一套工作台，完成从教学目标到课堂案例的全过程</h1>
          <div className="mt-8 space-y-4 text-slate-300">
            {['多角色 AI 协同，降低单次生成偏差', '过程透明可回溯，支持人工编辑与版本管理', 'Word、PDF、PPTX 一键导出，直接进入课堂使用'].map((item) => (
              <div key={item} className="flex items-center gap-3"><CheckCircle2 size={18} className="text-emerald-400" /><span>{item}</span></div>
            ))}
          </div>
        </div>
        <p className="relative text-xs text-slate-500">专为高校课程与企业培训场景设计</p>
      </section>

      <main className="flex items-center justify-center px-5 py-12 sm:px-10">
        <div className="w-full max-w-md">
          <Link to="/" className="mb-10 inline-flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-slate-900 lg:hidden">
            <ArrowLeft size={16} /> 返回首页
          </Link>
          <div className="mb-8">
            <p className="text-sm font-semibold text-primary">欢迎回来</p>
            <h2 className="mt-2 text-3xl font-bold tracking-tight text-slate-950">登录教学工作台</h2>
            <p className="mt-2 text-sm text-slate-500">继续管理案例、查看生成进度和导出授课包。</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-5">
            <div>
              <Label htmlFor="email">工作邮箱</Label>
              <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" placeholder="name@university.edu.cn" />
            </div>
            <div>
              <Label htmlFor="password">密码</Label>
              <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" placeholder="请输入密码" />
            </div>
            <label className="flex cursor-pointer items-center gap-2.5 text-sm text-slate-600">
              <input type="checkbox" checked={rememberMe} onChange={(e) => setRememberMe(e.target.checked)} className="h-4 w-4 rounded border-slate-300 text-primary focus:ring-primary" />
              7 天内保持登录
            </label>
            {error && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
            <Button type="submit" className="w-full" size="lg" disabled={loading}>
              {loading ? '正在安全登录…' : '登录工作台'}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-500">
            还没有账号？{' '}
            <Link to="/register" className="font-semibold text-primary hover:text-primary-dark">免费注册</Link>
          </p>

          <div className="mt-6 flex items-start gap-3 rounded-xl bg-slate-50 p-4 text-xs leading-5 text-slate-500">
            <LockKeyhole size={17} className="mt-0.5 shrink-0 text-emerald-600" />
            <span>密码不会写入网页存储；保持登录凭证使用 HttpOnly 安全 Cookie，页面脚本无法读取。</span>
          </div>
        </div>
      </main>
    </div>
  )
}
