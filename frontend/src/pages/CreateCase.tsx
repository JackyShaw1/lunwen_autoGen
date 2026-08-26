import { useState } from 'react'
import { useFieldArray, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, BookOpenCheck, Check, CheckCircle2, Clock3, FileText, Lightbulb, RefreshCw, Sparkles, Target, Users, WandSparkles } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Input, Label, Select, Textarea } from '@/components/ui/Input'
import { createCase, suggestLearningObjectives, type ObjectiveSuggestion } from '@/features/cases/api'

const schema = z.object({
  title: z.string().min(5, '请用至少 5 个字描述案例主题'),
  subject: z.string().min(1),
  course_name: z.string().min(1, '请输入课程名称'),
  case_type: z.string(),
  difficulty: z.string(),
  target_audience: z.string(),
  target_words: z.coerce.number().min(1500).max(5000),
  class_hours: z.coerce.number().min(1).max(8).default(2),
  workflow_template: z.string(),
  learning_objectives: z.array(z.object({ value: z.string().min(1, '教学目标不能为空') })).min(1),
  objective_brief: z.object({
    learning_challenge: z.string().max(500),
    desired_performance: z.string().max(500),
    required_concepts: z.string().max(500),
    assessment_evidence: z.string().max(500),
  }),
  special_requirements: z.string().optional(),
})

type FormValues = z.infer<typeof schema>

const observableVerbs = ['识别', '解释', '分析', '比较', '评价', '论证', '设计', '建构', '绘制', '提出', '计算', '制定']

function objectiveFeedback(value?: string) {
  const text = (value || '').trim()
  if (!text) return { tone: 'text-slate-400', text: '建议结构：可观察动作＋案例对象＋思维方法＋评价产出' }
  if (['了解', '熟悉', '掌握'].some((word) => text.includes(word))) return { tone: 'text-amber-700', text: '“了解/熟悉/掌握”难以评价，建议改为分析、比较、论证或设计' }
  if (!observableVerbs.some((word) => text.includes(word))) return { tone: 'text-amber-700', text: '建议加入一个可观察动作，例如分析、评价、论证或设计' }
  if (text.length < 18) return { tone: 'text-amber-700', text: '目标还比较宽泛，可补充使用的方法或最终产出' }
  return { tone: 'text-emerald-700', text: '目标具备可观察动作，可继续补充评价标准' }
}

function SectionTitle({ icon: Icon, step, title, desc }: { icon: typeof Target; step: string; title: string; desc: string }) {
  return (
    <div className="mb-6 flex gap-3 border-b border-slate-100 pb-5">
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-primary"><Icon size={20} /></span>
      <div><p className="text-xs font-bold uppercase tracking-wider text-primary">步骤 {step}</p><h2 className="mt-0.5 font-bold text-slate-900">{title}</h2><p className="mt-1 text-xs text-slate-500">{desc}</p></div>
    </div>
  )
}

export default function CreateCase() {
  const navigate = useNavigate()
  const { register, control, handleSubmit, watch, setValue, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: '',
      subject: '管理学',
      course_name: '',
      case_type: '决策型',
      difficulty: '中级',
      target_audience: '本科',
      target_words: 2800,
      class_hours: 2,
      workflow_template: 'sequential_standard',
      learning_objectives: [{ value: '' }],
      objective_brief: { learning_challenge: '', desired_performance: '', required_concepts: '', assessment_evidence: '' },
      special_requirements: '',
    },
  })
  const { fields, append, remove, replace } = useFieldArray({ control, name: 'learning_objectives' })
  const [submitError, setSubmitError] = useState('')
  const [objectiveError, setObjectiveError] = useState('')
  const [objectiveSuggestion, setObjectiveSuggestion] = useState<ObjectiveSuggestion | null>(null)
  const [objectiveVariant, setObjectiveVariant] = useState(0)
  const [isSuggesting, setIsSuggesting] = useState(false)
  const values = watch()
  const contextReady = values.title.trim().length >= 5 && values.course_name.trim().length > 0
  const briefFields = Object.values(values.objective_brief || {}).filter((value) => value.trim()).length

  const fillBriefExample = () => {
    setValue('objective_brief.learning_challenge', '学生只能复述概念，无法结合案例证据解释问题形成机制')
    setValue('objective_brief.desired_performance', '比较不同方案并给出有证据、有取舍的判断')
    setValue('objective_brief.required_concepts', values.course_name ? `${values.course_name}中的核心概念与分析框架` : '本课核心概念与分析框架')
    setValue('objective_brief.assessment_evidence', values.case_type === '问题诊断' ? '一张因果关系图和三分钟诊断汇报' : '一页决策备忘录和小组答辩')
    setObjectiveSuggestion(null)
  }

  const generateObjectives = async () => {
    if (!contextReady || isSuggesting) return
    setObjectiveError('')
    setIsSuggesting(true)
    try {
      const suggestion = await suggestLearningObjectives({
        title: values.title,
        subject: values.subject,
        course_name: values.course_name,
        case_type: values.case_type,
        difficulty: values.difficulty,
        target_audience: values.target_audience,
        variant: objectiveVariant,
        objective_brief: values.objective_brief,
      })
      replace(suggestion.objectives.map((value) => ({ value })))
      setObjectiveSuggestion(suggestion)
      setObjectiveVariant((current) => current + 1)
    } catch {
      setObjectiveError('教学目标生成失败，请稍后重试；你仍可直接手动填写。')
    } finally {
      setIsSuggesting(false)
    }
  }

  const onSubmit = async (data: FormValues) => {
    setSubmitError('')
    try {
      const task = await createCase({
        title: data.title,
        subject: data.subject,
        course_name: data.course_name,
        case_type: data.case_type,
        difficulty: data.difficulty,
        target_audience: data.target_audience,
        target_words: data.target_words,
        class_hours: data.class_hours,
        workflow_template: data.workflow_template,
        learning_objectives: data.learning_objectives.map((o) => o.value),
        special_requirements: data.special_requirements,
        objective_brief: data.objective_brief,
      })
      navigate(`/case/${task.id}/generate`)
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      setSubmitError(typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((d: { msg?: string }) => d.msg || '').join('；') : '创建失败，请稍后重试')
    }
  }

  return (
    <div>
      <button type="button" onClick={() => navigate('/dashboard')} className="mb-5 inline-flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-slate-900"><ArrowLeft size={16} />返回工作台</button>
      <div className="mb-8 max-w-3xl">
        <p className="text-sm font-semibold text-primary">新建教学案例</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-950">告诉 AI 教研团队，你想解决什么教学问题</h1>
        <p className="mt-3 text-sm leading-6 text-slate-500">清晰的学习目标比冗长的背景材料更重要。填写完成后仍可修改，不必一次做到完美。</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="grid items-start gap-7 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-6">
          <Card>
            <SectionTitle icon={BookOpenCheck} step="1/3" title="定义课程情境" desc="让系统理解这份案例服务于哪门课、哪类学生" />
            <div className="space-y-5">
              <div>
                <Label>案例主题 <span className="text-red-500">*</span></Label>
                <Input {...register('title')} placeholder="例如：制造企业数字化转型中的组织阻力" />
                <p className="mt-1.5 text-xs text-slate-400">建议包含具体主体、变化或需要决策的矛盾</p>
                {errors.title && <p className="mt-1 text-xs text-red-600">{errors.title.message}</p>}
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div><Label>学科分类</Label><Select {...register('subject')}><option>管理学</option><option>经济学</option><option>计算机科学</option><option>法学</option></Select></div>
                <div><Label>课程名称 <span className="text-red-500">*</span></Label><Input {...register('course_name')} placeholder="例如：组织行为学" />{errors.course_name && <p className="mt-1 text-xs text-red-600">{errors.course_name.message}</p>}</div>
              </div>
              <div className="grid gap-4 md:grid-cols-3">
                <div><Label>案例类型</Label><Select {...register('case_type')}><option>决策型</option><option>分析型</option><option>情境模拟</option><option>问题诊断</option></Select></div>
                <div><Label>适用对象</Label><Select {...register('target_audience')}><option>本科</option><option>硕士</option><option>企业培训</option></Select></div>
                <div><Label>难度</Label><Select {...register('difficulty')}><option>初级</option><option>中级</option><option>高级</option></Select></div>
              </div>
            </div>
          </Card>

          <Card>
            <SectionTitle icon={Target} step="2/3" title="明确学习目标" desc="目标将用于设计冲突、讨论题和课堂活动" />
            <div className="mb-5 overflow-hidden rounded-2xl border border-indigo-100 bg-indigo-50/60">
              <div className="flex flex-wrap items-start justify-between gap-3 border-b border-indigo-100 bg-white/70 p-4">
                <div className="flex gap-3"><span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-100 text-primary"><WandSparkles size={18} /></span><div><p className="text-sm font-bold text-slate-900">不用写提示词，只回答 4 个教学问题</p><p className="mt-1 text-xs leading-5 text-slate-500">可以只填你最确定的内容，系统会把教学意图整理成专业目标。</p></div></div>
                <div className="flex items-center gap-2"><span className={`rounded-full px-2.5 py-1 text-xs font-bold ${briefFields >= 3 ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>已回答 {briefFields}/4</span><Button type="button" variant="outline" size="sm" onClick={fillBriefExample}><Lightbulb size={14} />填入示例</Button></div>
              </div>
              <div className="grid gap-4 p-4 md:grid-cols-2">
                <div><Label>1. 学生现在卡在哪里？</Label><Input {...register('objective_brief.learning_challenge')} placeholder="例如：会背框架，但不会用证据解释根因" /><p className="mt-1.5 text-xs text-slate-400">描述当前学习困难，不需要写解决办法。</p></div>
                <div><Label>2. 课后希望学生能做什么？</Label><Input {...register('objective_brief.desired_performance')} placeholder="例如：比较两种方案并作出有依据的选择" /><p className="mt-1.5 text-xs text-slate-400">尽量使用分析、比较、论证、设计等动作。</p></div>
                <div><Label>3. 必须用到哪些知识或方法？</Label><Input {...register('objective_brief.required_concepts')} placeholder={`例如：${values.course_name || '本课'}的核心概念、系统思维`} /><p className="mt-1.5 text-xs text-slate-400">避免案例精彩但与课程知识脱节。</p></div>
                <div><Label>4. 用什么证明学生学会了？</Label><Input {...register('objective_brief.assessment_evidence')} placeholder="例如：因果图、决策备忘录、小组答辩" /><p className="mt-1.5 text-xs text-slate-400">填写课堂上能够看到或评分的学习产出。</p></div>
              </div>
              <div className="flex flex-wrap items-center justify-between gap-3 border-t border-indigo-100 bg-white/60 p-4">
                <p className="max-w-xl text-xs leading-5 text-slate-500">{contextReady ? '系统会结合课程情境和以上回答生成 3 条递进目标；再次点击可换一种分析角度。' : '请先填写至少 5 个字的案例主题和课程名称。'}</p>
                <Button type="button" size="sm" disabled={!contextReady || isSuggesting} onClick={generateObjectives}>
                  {objectiveSuggestion ? <RefreshCw size={15} className={isSuggesting ? 'animate-spin' : ''} /> : <Sparkles size={15} />}
                  {isSuggesting ? '正在整理教学意图…' : objectiveSuggestion ? '换一组目标' : '生成 3 条可评价目标'}
                </Button>
              </div>
              {objectiveSuggestion && (
                <div className="border-t border-indigo-100 bg-indigo-100/40 px-4 py-3 text-xs">
                  <div className="flex flex-wrap items-center gap-2"><span className="rounded-full bg-white px-2.5 py-1 font-semibold text-primary">{objectiveSuggestion.framework_name}</span><span className="font-bold text-slate-700">意图完整度 {objectiveSuggestion.quality_score}%</span><span className="text-slate-500">{objectiveSuggestion.rationale}</span></div>
                  <p className="mt-2 leading-5 text-slate-600"><span className="font-bold">系统理解：</span>{objectiveSuggestion.brief_summary}</p>
                  <div className="mt-2 flex flex-wrap gap-2">{objectiveSuggestion.quality_checks.map((item) => <span key={item.key} title={item.hint} className={`inline-flex items-center gap-1 rounded-full px-2 py-1 ${item.passed ? 'bg-emerald-100 text-emerald-700' : 'bg-white text-slate-500'}`}>{item.passed && <CheckCircle2 size={12} />}{item.label}</span>)}</div>
                </div>
              )}
              {objectiveError && <p className="px-4 pb-3 text-xs text-red-600">{objectiveError}</p>}
            </div>
            <div className="space-y-3">
              {fields.map((field, index) => (
                <div key={field.id}>
                  <div className="flex gap-2">
                    <span className="mt-2.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-slate-500">{index + 1}</span>
                    <Input {...register(`learning_objectives.${index}.value`)} placeholder={index === 0 ? '例如：分析不同利益相关方的立场与诉求' : '补充另一个可观察、可评价的学习目标'} />
                    {fields.length > 1 && <Button type="button" variant="ghost" size="sm" aria-label="删除目标" onClick={() => remove(index)}>×</Button>}
                  </div>
                  <p className={`ml-8 mt-1 text-xs ${objectiveFeedback(values.learning_objectives?.[index]?.value).tone}`}>{objectiveFeedback(values.learning_objectives?.[index]?.value).text}</p>
                  {errors.learning_objectives?.[index]?.value && <p className="ml-8 mt-1 text-xs text-red-600">{errors.learning_objectives[index]?.value?.message}</p>}
                </div>
              ))}
            </div>
            <Button type="button" variant="outline" size="sm" className="mt-4" onClick={() => append({ value: '' })}>+ 添加教学目标</Button>
          </Card>

          <Card>
            <SectionTitle icon={Sparkles} step="3/3" title="设定产出偏好" desc="控制篇幅、课堂节奏与 AI 协作深度" />
            <div className="grid gap-4 md:grid-cols-3">
              <div><Label>案例正文字数</Label><Input type="number" {...register('target_words')} /></div>
              <div><Label>计划课时</Label><Input type="number" {...register('class_hours')} /></div>
              <div><Label>生成模式</Label><Select {...register('workflow_template')}><option value="sequential_standard">标准生成</option><option value="groupchat_review">深度评审</option></Select></div>
            </div>
            <div className="mt-5"><Label>需要特别关注的要求</Label><Textarea rows={4} {...register('special_requirements')} placeholder="例如：突出中层与一线员工的立场冲突；避免出现真实企业名称……" /><p className="mt-1.5 text-xs text-slate-400">选填。可以说明希望强调或避免的内容。</p></div>
          </Card>

          {submitError && <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{submitError}</div>}
        </div>

        <aside className="space-y-4 xl:sticky xl:top-8">
          <Card className="border-indigo-200 bg-gradient-to-br from-white to-indigo-50/70">
            <p className="text-xs font-bold uppercase tracking-wider text-primary">生成摘要</p>
            <h2 className="mt-2 line-clamp-2 font-bold text-slate-900">{values.title || '尚未填写案例主题'}</h2>
            <div className="mt-5 space-y-3 text-sm text-slate-600">
              <div className="flex items-center gap-2"><Users size={16} className="text-slate-400" />{values.target_audience} · {values.difficulty}</div>
              <div className="flex items-center gap-2"><Clock3 size={16} className="text-slate-400" />{values.class_hours || 0} 课时 · 约 {values.target_words || 0} 字</div>
              <div className="flex items-center gap-2"><Target size={16} className="text-slate-400" />{values.learning_objectives?.filter((o) => o.value).length || 0} 个学习目标</div>
            </div>
            <div className="my-5 border-t border-indigo-100" />
            <p className="text-xs font-semibold text-slate-500">将生成</p>
            <ul className="mt-3 space-y-2 text-sm text-slate-700">
              {['案例正文与决策点', '分层讨论题', '教师参考手册', '教学目标对齐表'].map((item) => <li key={item} className="flex items-center gap-2"><Check size={15} className="text-emerald-600" />{item}</li>)}
            </ul>
          </Card>
          <div className="rounded-2xl border border-slate-200 bg-white p-4 text-xs leading-5 text-slate-500"><div className="flex gap-2"><FileText size={16} className="mt-0.5 shrink-0 text-primary" /><span>启动后可实时查看各专业角色的产出；完成后所有内容仍可编辑。</span></div></div>
          <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>{isSubmitting ? '正在创建任务…' : <><Sparkles size={18} />开始生成授课包</>}</Button>
          <Button type="button" variant="ghost" className="w-full" onClick={() => navigate('/dashboard')}>取消并返回</Button>
        </aside>
      </form>
    </div>
  )
}
