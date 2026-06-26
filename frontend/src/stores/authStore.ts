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

function loadPersisted(): { user: User | null; accessToken: string | null } {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { user: null, accessToken: null }
    return JSON.parse(raw)
  } catch {
    return { user: null, accessToken: null }
  }
}

export const authStore = {
  getState: (): AuthState => authState,
}

let authState: AuthState = {
  user: loadPersisted().user,
  accessToken: loadPersisted().accessToken,
  login(user, token) {
    authState.user = user
    authState.accessToken = token
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ user, accessToken: token }))
  },
  logout() {
    authState.user = null
    authState.accessToken = null
    localStorage.removeItem(STORAGE_KEY)
  },
  isAuthenticated() {
    return !!authState.accessToken
  },
  isAdmin() {
    return authState.user?.role === 'admin'
  },
}
