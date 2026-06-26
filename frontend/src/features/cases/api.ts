import type { CaseTask, CasePackage, DashboardStats, CreateCasePayload, StatsRange } from '@/types/case'
import { api } from '@/lib/api-client'

// Demo data when backend is not available
export const mockUser = {
  id: '1',
  email: 'teacher@university.edu.cn',
  name: '陈老师',
  role: 'teacher' as const,
  quota_remaining: 5,
}

export const mockCases: CaseTask[] = [
  {
    id: '1',
    title: '制造企业数字化转型中的组织阻力',
    subject: '管理学',
    course_name: '组织行为学',
    case_type: '决策型',
    difficulty: '中级',
    target_audience: '本科',
    status: 'finalized',
    workflow_template: 'sequential_standard',
    rubric_overall: 4.3,
    created_at: '2026-06-20',
    updated_at: '2026-06-26',
  },
  {
    id: '2',
    title: '新能源汽车供应链中断应对策略',
    subject: '经济学',
    course_name: '供应链管理',
    case_type: '分析型',
    difficulty: '中级',
    target_audience: '硕士',
    status: 'running',
    workflow_template: 'groupchat_review',
    created_at: '2026-06-24',
    updated_at: '2026-06-26',
  },
  {
    id: '3',
    title: '敏捷开发团队中的技术债务抉择',
    subject: '计算机科学',
    course_name: '软件工程',
    case_type: '情境模拟',
    difficulty: '中级',
    target_audience: '本科',
    status: 'completed',
    workflow_template: 'sequential_standard',
    created_at: '2026-06-22',
    updated_at: '2026-06-24',
  },
]

export const mockDashboardStats: DashboardStats = {
  total_cases: 12,
  total_cases_delta: 3,
  finalized_count: 8,
  completion_rate: 66.7,
  running_count: 1,
  avg_rubric: 4.2,
  avg_rubric_delta: 0.3,
  estimated_hours_saved: 96,
  export_count: { docx: 11, pdf: 4, total: 15 },
  avg_generation_minutes: 14.2,
  discussion_questions_total: 68,
  agent_regenerate_count: 23,
  quota_remaining: 5,
  subject_distribution: { 管理学: 5, 经济学: 4, 计算机: 3, 其他: 1 },
  status_distribution: { finalized: 8, running: 1, editing: 2, draft: 1 },
  monthly_trend: [
    { month: '1月', count: 1 },
    { month: '2月', count: 2 },
    { month: '3月', count: 2 },
    { month: '4月', count: 2 },
    { month: '5月', count: 3 },
    { month: '6月', count: 4 },
  ],
}

export const mockCasePackage: CasePackage = {
  meta: {
    title: '制造企业数字化转型中的组织阻力',
    subject: '管理学',
    course: '组织行为学',
    difficulty: 'intermediate',
    case_type: 'decision',
    fictional_disclaimer: '本案例为教学虚构情境',
  },
  learning_objectives: [
    { id: 'LO1', level: '分析', description: '分析组织变革中不同利益相关方的立场与诉求' },
  ],
  body: {
    background: '华鑫制造有限公司是一家拥有 30 年历史的中型装备制造企业……',
    narrative:
      '生产部副部长王强在部门会议上公开质疑新系统增加一线负担。IT 负责人陈薇则认为变革必然有阵痛……',
    decision_point: '是否暂停数字化项目第二阶段，先化解一线抵触，还是按原计划全面推进。',
    characters: [
      { name: '李明', role: '总经理', stance: '全面推进' },
      { name: '王强', role: '生产部副部长', stance: '暂缓二期' },
    ],
  },
  discussion_questions: [
    { level: '理解', question: '案例中三类利益相关方各自的核心诉求是什么？', teaching_intent: '识别角色立场' },
    { level: '分析', question: '组织阻力背后反映了哪些深层次的组织文化或管理问题？' },
    { level: '评价', question: '王强「公开质疑」的行为是否合适？' },
    { level: '创造', question: '如果你是李明，在高管会上将如何发言并做出决策？' },
  ],
  instructor_guide: {
    teaching_flow: '第1课时阅读+小组讨论；第2课时辩论+汇报',
    key_points: ['利益相关方分析', '变革阻力来源'],
    common_misconceptions: ['将问题简化为纯技术问题'],
  },
  alignment_matrix: [
    { objective_id: 'LO1', case_section: '冲突升级段落', activity: '小组讨论', assessment: '汇报点评' },
  ],
  quality: { overall_score: 4.3, reviewer_summary: '讨论价值良好，决策点清晰' },
}

async function withFallback<T>(fn: () => Promise<T>, fallback: T): Promise<T> {
  try {
    return await fn()
  } catch {
    return fallback
  }
}

export async function loginApi(email: string, password: string) {
  return withFallback(
    async () => {
      const { data } = await api.post('/auth/login', { email, password })
      return data
    },
    { user: { ...mockUser, email }, access_token: 'demo-token' },
  )
}

export async function fetchCases(): Promise<CaseTask[]> {
  return withFallback(async () => {
    const { data } = await api.get<CaseTask[]>('/cases')
    return data
  }, mockCases)
}

export async function fetchDashboardStats(range: StatsRange): Promise<DashboardStats> {
  return withFallback(async () => {
    const { data } = await api.get<DashboardStats>('/dashboard/stats', { params: { range } })
    return data
  }, mockDashboardStats)
}

export async function createCase(payload: CreateCasePayload): Promise<CaseTask> {
  return withFallback(async () => {
    const { data } = await api.post<CaseTask>('/cases', payload)
    return data
  }, {
    ...mockCases[0],
    id: String(Date.now()),
    title: payload.title,
    subject: payload.subject,
    course_name: payload.course_name,
    status: 'draft',
    updated_at: new Date().toISOString(),
  })
}

export async function fetchCasePackage(caseId: string): Promise<CasePackage> {
  return withFallback(async () => {
    const { data } = await api.get<CasePackage>(`/cases/${caseId}/package`)
    return data
  }, mockCasePackage)
}

export async function startGeneration(caseId: string) {
  return withFallback(async () => {
    await api.post(`/cases/${caseId}/generate`)
  }, undefined)
}

export async function exportCase(caseId: string, format: 'docx' | 'pdf') {
  return withFallback(async () => {
    const { data } = await api.post(`/cases/${caseId}/export`, { format })
    return data
  }, { download_url: '#' })
}
