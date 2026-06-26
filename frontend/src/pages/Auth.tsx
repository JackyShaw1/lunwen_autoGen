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
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const handleLogin = async () => {
    setLoading(true)
    try {
      const data = await loginApi(email, password)
      authStore.getState().login(data.user, data.access_token)
      navigate('/dashboard')
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
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="任意密码（演示）" />
          </div>
          <Button className="w-full" onClick={handleLogin} disabled={loading}>
            {loading ? '登录中…' : '登录'}
          </Button>
        </div>
      </Card>
    </div>
  )
}
