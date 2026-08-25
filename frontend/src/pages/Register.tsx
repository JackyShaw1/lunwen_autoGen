import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, BookOpen, Check, CheckCircle2, ShieldCheck, Sparkles, UserPlus } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input, Label } from '@/components/ui/Input'
import { registerApi } from '@/features/cases/api'
import { authStore } from '@/stores/authStore'

export default function Register() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const requirements = [
    { label: '至少 8 个字符', met: password.length >= 8 },
    { label: '包含字母', met: /[A-Za-z]/.test(password) },
    { label: '包含数字', met: /\d/.test(password) },
  ]

  const handleRegister = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    if (name.trim().length < 2) return setError('请输入至少 2 个字的姓名或称呼')
    if (!requirements.every((item) => item.met)) return setError('密码未满足安全要求')
    if (password !== confirmPassword) return setError('两次输入的密码不一致')

    setLoading(true)
    try {
      const data = await registerApi(name.trim(), email, password, rememberMe)
      authStore.getState().login(data.user, data.access_token)
      navigate('/dashboard', { replace: true })
    } catch (e: unknown) {
      const response = (e as { response?: { data?: { detail?: string | Array<{ msg?: string }> } } })?.response
      const detail = response?.data?.detail
      setError(typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((item) => item.msg).filter(Boolean).join('；') : '注册失败，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid min-h-screen bg-white lg:grid-cols-[.9fr_1.1fr]">
      <section className="relative hidden overflow-hidden bg-slate-950 p-12 text-white lg:flex lg:flex-col">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(99,102,241,0.32),transparent_34%),radial-gradient(circle_at_85%_90%,rgba(14,165,233,0.18),transparent_30%)]" />
        <Link to="/" className="relative flex items-center gap-3 text-white no-underline">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary"><BookOpen size={21} /></span>
          <span><strong className="block">知案</strong><small className="text-slate-400">AI 教学案例工作台</small></span>
        </Link>
        <div className="relative my-auto max-w-lg">
          <span className="inline-flex items-center gap-2 rounded-full border border-indigo-400/30 bg-indigo-400/10 px-3 py-1.5 text-sm text-indigo-200"><Sparkles size={15} /> 注册即得 30 次案例生成额度</span>
          <h1 className="mt-6 text-4xl font-bold leading-tight">建立属于你的教学案例资产库</h1>
          <div className="mt-8 space-y-4 text-slate-300">
            {['保存并持续迭代每一份课程案例', '实时查看 AI 教研团队协作过程', '导出可编辑、可归档的完整授课包'].map((item) => <div key={item} className="flex items-center gap-3"><CheckCircle2 size={18} className="text-emerald-400" /><span>{item}</span></div>)}
          </div>
        </div>
        <p className="relative flex items-center gap-2 text-xs text-slate-500"><ShieldCheck size={15} />公开注册仅创建教师账号，管理权限需由平台授予</p>
      </section>

      <main className="flex items-center justify-center px-5 py-10 sm:px-10">
        <div className="w-full max-w-lg">
          <Link to="/" className="mb-8 inline-flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-slate-900 lg:hidden"><ArrowLeft size={16} />返回首页</Link>
          <div className="mb-7">
            <p className="text-sm font-semibold text-primary">创建教师账号</p>
            <h2 className="mt-2 text-3xl font-bold tracking-tight text-slate-950">开始建设课程案例库</h2>
            <p className="mt-2 text-sm text-slate-500">使用常用邮箱注册，案例和导出记录将保存在此账号下。</p>
          </div>

          <form onSubmit={handleRegister} className="space-y-4">
            <div><Label htmlFor="name">姓名或称呼</Label><Input id="name" value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" placeholder="例如：陈老师" /></div>
            <div><Label htmlFor="register-email">邮箱</Label><Input id="register-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" placeholder="name@university.edu.cn" /></div>
            <div><Label htmlFor="register-password">设置密码</Label><Input id="register-password" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" placeholder="请输入安全密码" />
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">{requirements.map((item) => <span key={item.label} className={`flex items-center gap-1 text-xs ${item.met ? 'text-emerald-600' : 'text-slate-400'}`}><Check size={12} />{item.label}</span>)}</div>
            </div>
            <div><Label htmlFor="confirm-password">确认密码</Label><Input id="confirm-password" type="password" required value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} autoComplete="new-password" placeholder="再次输入密码" /></div>
            <label className="flex cursor-pointer items-center gap-2.5 text-sm text-slate-600"><input type="checkbox" checked={rememberMe} onChange={(e) => setRememberMe(e.target.checked)} className="h-4 w-4 rounded border-slate-300 text-primary focus:ring-primary" />7 天内保持登录</label>
            {error && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
            <Button type="submit" className="w-full" size="lg" disabled={loading}><UserPlus size={18} />{loading ? '正在创建账号…' : '注册并进入工作台'}</Button>
          </form>
          <p className="mt-6 text-center text-sm text-slate-500">已经注册？ <Link to="/auth" className="font-semibold text-primary hover:text-primary-dark">直接登录</Link></p>
        </div>
      </main>
    </div>
  )
}
