import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Input, Label } from '@/components/ui/Input'
import { loginApi } from '@/features/cases/api'
import { authStore } from '@/stores/authStore'

export default function Auth() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('teacher@university.edu.cn')
  const [password, setPassword] = useState('demo123')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleLogin = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await loginApi(email, password)
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
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-6">
      <Card className="w-full max-w-md">
        <h2 className="text-center text-xl font-bold">教师登录</h2>
        <p className="mt-2 text-center text-sm text-gray-500">CaseAutoGenSystem 教学案例生成平台</p>
        <div className="mt-6 space-y-4">
          <div>
            <Label>邮箱</Label>
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div>
            <Label>密码</Label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="demo123"
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button className="w-full" onClick={handleLogin} disabled={loading}>
            {loading ? '登录中…' : '登录'}
          </Button>
          <p className="text-center text-xs text-gray-400">
            教师：teacher@university.edu.cn / demo123
            <br />
            管理员：admin@university.edu.cn / admin123
          </p>
        </div>
      </Card>
    </div>
  )
}
