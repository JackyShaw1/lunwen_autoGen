import type { CaseTask, CasePackage, DashboardStats, CreateCasePayload, StatsRange, VideoResource, VisualAsset } from '@/types/case'
import { api } from '@/lib/api-client'

const useMock = import.meta.env.VITE_USE_MOCK === 'true'

export const mockUser = {
  id: '1',
  email: 'teacher@university.edu.cn',
  name: '陈老师',
  role: 'teacher' as const,
  quota_remaining: 30,
}

export const mockCases: CaseTask[] = []
export const mockDashboardStats: DashboardStats = {
  total_cases: 0,
  total_cases_delta: 0,
  finalized_count: 0,
  completion_rate: 0,
  running_count: 0,
  avg_rubric: 0,
  avg_rubric_delta: 0,
  estimated_hours_saved: 0,
  export_count: { docx: 0, pdf: 0, pptx: 0, total: 0 },
  avg_generation_minutes: 0,
  discussion_questions_total: 0,
  agent_regenerate_count: 0,
  quota_remaining: 30,
  subject_distribution: {},
  status_distribution: {},
  monthly_trend: [],
}

async function withOptionalMock<T>(fn: () => Promise<T>, fallback: () => T): Promise<T> {
  try {
    return await fn()
  } catch (err) {
    if (useMock) return fallback()
    throw err
  }
}

export async function loginApi(email: string, password: string, rememberMe: boolean) {
  return withOptionalMock(
    async () => {
      const { data } = await api.post('/auth/login', { email, password, remember_me: rememberMe })
      return data
    },
    () => ({ user: { ...mockUser, email }, access_token: 'demo-token' }),
  )
}

export async function registerApi(name: string, email: string, password: string, rememberMe: boolean) {
  const { data } = await api.post('/auth/register', {
    name,
    email,
    password,
    remember_me: rememberMe,
  })
  return data
}

export async function fetchCases(): Promise<CaseTask[]> {
  return withOptionalMock(async () => {
    const { data } = await api.get<CaseTask[]>('/cases')
    return data
  }, () => mockCases)
}

export async function fetchCase(caseId: string): Promise<CaseTask> {
  const { data } = await api.get<CaseTask>(`/cases/${caseId}`)
  return data
}

export async function fetchDashboardStats(range: StatsRange): Promise<DashboardStats> {
  return withOptionalMock(async () => {
    const { data } = await api.get<DashboardStats>('/dashboard/stats', { params: { range } })
    return data
  }, () => mockDashboardStats)
}

export async function createCase(payload: CreateCasePayload): Promise<CaseTask> {
  const { data } = await api.post<CaseTask>('/cases', payload)
  return data
}

export interface ObjectiveSuggestion {
  framework: 'pyramid' | 'systems' | '3w1h'
  framework_name: string
  rationale: string
  objectives: string[]
}

export async function suggestLearningObjectives(payload: {
  title: string
  subject: string
  course_name: string
  case_type: string
  difficulty: string
  target_audience: string
  variant: number
}): Promise<ObjectiveSuggestion> {
  const { data } = await api.post<ObjectiveSuggestion>('/cases/suggest-objectives', payload)
  return data
}

export async function fetchCasePackage(caseId: string): Promise<CasePackage> {
  const { data } = await api.get<{ package?: CasePackage } & CasePackage>(`/cases/${caseId}/package`)
  if (data.package && data.package.meta) return data.package
  return data as CasePackage
}

export async function saveCasePackage(caseId: string, packageData: CasePackage) {
  const { data } = await api.put(`/cases/${caseId}/package`, packageData)
  return data
}

export async function searchOfficialMaterials(query: string): Promise<VisualAsset[]> {
  const { data } = await api.get<{ items: VisualAsset[] }>('/materials/search', { params: { q: query, limit: 12 } })
  return data.items
}

export async function searchOfficialVideos(query: string): Promise<VideoResource[]> {
  const { data } = await api.get<{ items: VideoResource[] }>('/materials/videos/search', { params: { q: query, limit: 10 } })
  return data.items
}

export async function startGeneration(caseId: string) {
  await api.post(`/cases/${caseId}/generate`)
}

export async function fetchCaseStatus(caseId: string) {
  const { data } = await api.get(`/cases/${caseId}/status`)
  return data
}

export async function fetchLiveProgress(caseId: string) {
  const { data } = await api.get(`/cases/${caseId}/live`)
  return data
}

export type ExportFormat = 'docx' | 'pdf' | 'pptx'
export interface PptOptions {
  theme: 'academic' | 'modern' | 'minimal'
  density: 'concise' | 'standard' | 'detailed'
  audience: 'student' | 'teacher'
  mode: 'lecture' | 'workshop' | 'visual'
  include_speaker_notes: boolean
}

export interface PptOutlinePreview {
  title: string
  slide_count: number
  theme: PptOptions['theme']
  density: PptOptions['density']
  audience: PptOptions['audience']
  mode: PptOptions['mode']
  include_speaker_notes: boolean
  slides: Array<{ index: number; kind: string; title: string; summary: string; teacher_only: boolean }>
}

export async function fetchPptOutline(caseId: string, options: PptOptions) {
  const { data } = await api.post<PptOutlinePreview>(`/cases/${caseId}/ppt-outline`, options)
  return data
}

export async function exportCase(caseId: string, format: ExportFormat, pptOptions?: PptOptions) {
  const { data } = await api.post<{
    export_id: string
    format: string
    download_url: string
    filename: string
    version: number
  }>(
    `/cases/${caseId}/export`,
    { format, ppt_options: format === 'pptx' ? pptOptions : undefined },
  )
  return data
}

export async function downloadExport(caseId: string, exportId: string, filename: string) {
  const { data } = await api.get(`/cases/${caseId}/exports/${exportId}/download`, {
    responseType: 'blob',
  })
  const url = URL.createObjectURL(data)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export interface AgentConfigItem {
  agent_name: string
  version: string
  is_active: boolean
  description?: string | null
}

export async function fetchAgents(): Promise<AgentConfigItem[]> {
  const { data } = await api.get<AgentConfigItem[]>('/admin/agents')
  return data
}

export async function fetchAgentConfig(name: string) {
  const { data } = await api.get<{ agent_name: string; version: string; config_yaml: string }>(
    `/admin/agents/${name}`,
  )
  return data
}

export async function updateAgentConfig(name: string, config_yaml: string) {
  const { data } = await api.put(`/admin/agents/${name}`, { config_yaml, activate: true })
  return data
}
