export type CaseStatus = 'draft' | 'running' | 'completed' | 'failed' | 'finalized'
export type StatsRange = 'month' | 'semester' | 'all'

export interface CaseTask {
  id: string
  title: string
  subject: string
  course_name: string
  case_type: string
  difficulty: string
  target_audience: string
  status: CaseStatus
  workflow_template: string
  rubric_overall?: number
  created_at: string
  updated_at: string
}

export interface LearningObjective {
  id?: string
  level: string
  description: string
  assessment_hint?: string
}

export interface DiscussionQuestion {
  level: string
  question: string
  teaching_intent?: string
}

export interface CasePackage {
  meta: {
    title: string
    subject: string
    course: string
    difficulty: string
    case_type: string
    fictional_disclaimer?: string
  }
  learning_objectives: LearningObjective[]
  body: {
    background?: string
    narrative: string
    decision_point?: string
    characters?: Array<{ name: string; role: string; stance: string }>
  }
  discussion_questions: DiscussionQuestion[]
  instructor_guide: {
    teaching_flow?: string
    key_points?: string[]
    common_misconceptions?: string[]
  }
  alignment_matrix: Array<{
    objective_id: string
    case_section: string
    activity: string
    assessment: string
  }>
  quality?: {
    overall_score?: number
    reviewer_summary?: string
  }
}

export interface DashboardStats {
  total_cases: number
  total_cases_delta: number
  finalized_count: number
  completion_rate: number
  running_count: number
  avg_rubric: number
  avg_rubric_delta: number
  estimated_hours_saved: number
  export_count: { docx: number; pdf: number; total: number }
  avg_generation_minutes: number
  discussion_questions_total: number
  agent_regenerate_count: number
  quota_remaining: number
  subject_distribution: Record<string, number>
  status_distribution: Record<string, number>
  monthly_trend: Array<{ month: string; count: number }>
}

export interface CreateCasePayload {
  title: string
  subject: string
  course_name: string
  case_type: string
  difficulty: string
  target_audience: string
  target_words: number
  learning_objectives: string[]
  workflow_template: string
  class_hours?: number
  special_requirements?: string
}

export interface AgentProgressItem {
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  duration_ms?: number
  token_usage?: number
  progress?: number
  output_summary?: string
}

export interface AgentStepResult {
  agent: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  summary?: string
  input?: {
    task?: Record<string, unknown>
    hint?: string
  }
  output?: Record<string, unknown> | null
  focus?: Record<string, unknown> | null
  duration_ms?: number | null
  token_usage?: number | null
}

export interface AgentProgressMessage {
  type: 'agent_progress'
  overall_progress: number
  current_agent?: string
  agents: AgentProgressItem[]
  estimated_remaining_seconds?: number
  step_results?: AgentStepResult[]
  task_meta?: Record<string, unknown>
  /** 后端流式打字推送（与进度同步） */
  stream?: {
    agent: string
    text: string
    done: boolean
  }
  error?: string
}
