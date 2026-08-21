export type UserRole = 'teacher' | 'admin'

export interface User {
  id: string
  email: string
  name: string
  role: UserRole
  quota_remaining: number
}

export interface AuthState {
  user: User | null
  accessToken: string | null
  login: (user: User, token: string) => void
  logout: () => void
  isAuthenticated: () => boolean
  isAdmin: () => boolean
}

const STORAGE_KEY = 'case_autogen_auth'

// 清除旧版本曾持久化的访问令牌；密码从未写入浏览器存储。
localStorage.removeItem(STORAGE_KEY)

export const authStore = {
  getState: (): AuthState => authState,
}

let authState: AuthState = {
  user: null,
  accessToken: null,
  login(user, token) {
    authState.user = user
    authState.accessToken = token
  },
  logout() {
    authState.user = null
    authState.accessToken = null
  },
  isAuthenticated() {
    return !!authState.accessToken
  },
  isAdmin() {
    return authState.user?.role === 'admin'
  },
}
