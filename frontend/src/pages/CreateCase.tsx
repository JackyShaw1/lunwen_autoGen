import { useFieldArray, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Input, Label, Select, Textarea } from '@/components/ui/Input'
import { createCase } from '@/features/cases/api'

const schema = z.object({
  title: z.string().min(5, '标题至少 5 个字'),
  subject: z.string(),
  course_name: z.string().min(1),
  case_type: z.string(),
  difficulty: z.string(),
  target_audience: z.string(),
  target_words: z.coerce.number().min(1500).max(5000),
  workflow_template: z.string(),
  learning_objectives: z.array(z.object({ value: z.string().min(1) })).min(1),
  special_requirements: z.string().optional(),
})

type FormValues = z.infer<typeof schema>

export default function CreateCase() {
  const navigate = useNavigate()
  const { register, control, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: '制造企业数字化转型中的组织阻力',
      subject: '管理学',
      course_name: '组织行为学',
      case_type: '决策型',
      difficulty: '中级',
      target_audience: '本科',
      target_words: 2800,
      workflow_template: 'sequential_standard',
      learning_objectives: [
        { value: '分析组织变革中不同利益相关方的立场与诉求' },
        { value: '识别数字化转型中的典型阻力来源' },
      ],
      special_requirements: '希望突出中层与一线员工的立场冲突，适合 2 课时讨论。',
    },
  })
  const { fields, append, remove } = useFieldArray({ control, name: 'learning_objectives' })

  const onSubmit = async (data: FormValues) => {
    const task = await createCase({
      title: data.title,
      subject: data.subject,
      course_name: data.course_name,
      case_type: data.case_type,
      difficulty: data.difficulty,
      target_audience: data.target_audience,
      target_words: data.target_words,
      workflow_template: data.workflow_template,
      learning_objectives: data.learning_objectives.map((o) => o.value),
      special_requirements: data.special_requirements,
    })
    navigate(`/case/${task.id}/generate`)
  }

  return (
    <div className="max-w-2xl">
      <h1 className="mb-6 text-2xl font-bold">配置教学案例任务</h1>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <Card>
          <h3 className="mb-4 border-b pb-2 font-semibold">基本信息</h3>
          <div className="space-y-4">
            <div>
              <Label>案例主题</Label>
              <Input {...register('title')} />
              {errors.title && <p className="mt-1 text-xs text-red-600">{errors.title.message}</p>}
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <Label>学科分类</Label>
                <Select {...register('subject')}>
                  <option>管理学</option>
                  <option>经济学</option>
                  <option>计算机科学</option>
                  <option>法学</option>
                </Select>
              </div>
              <div>
                <Label>课程名称</Label>
                <Input {...register('course_name')} />
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <Label>案例类型</Label>
                <Select {...register('case_type')}>
                  <option>决策型</option>
                  <option>分析型</option>
                  <option>情境模拟</option>
                  <option>问题诊断</option>
                </Select>
              </div>
              <div>
                <Label>适用对象</Label>
                <Select {...register('target_audience')}>
                  <option>本科</option>
                  <option>硕士</option>
                  <option>企业培训</option>
                </Select>
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <Label>难度</Label>
                <Select {...register('difficulty')}>
                  <option>初级</option>
                  <option>中级</option>
                  <option>高级</option>
                </Select>
              </div>
              <div>
                <Label>案例正文字数</Label>
                <Input type="number" {...register('target_words')} />
              </div>
            </div>
          </div>
        </Card>

        <Card>
          <h3 className="mb-4 border-b pb-2 font-semibold">教学目标</h3>
          {fields.map((field, index) => (
            <div key={field.id} className="mb-2 flex gap-2">
              <Input {...register(`learning_objectives.${index}.value`)} />
              <Button type="button" variant="outline" size="sm" onClick={() => remove(index)}>×</Button>
            </div>
          ))}
          <Button type="button" variant="outline" size="sm" onClick={() => append({ value: '' })}>
            + 添加教学目标
          </Button>
        </Card>

        <Card>
          <h3 className="mb-4 border-b pb-2 font-semibold">AutoGen 编排</h3>
          <div className="space-y-4">
            <div>
              <Label>Agent 工作流模板</Label>
              <Select {...register('workflow_template')}>
                <option value="sequential_standard">标准流水线（Sequential 五 Agent）</option>
                <option value="groupchat_review">深度评审（GroupChat 多轮修订）</option>
              </Select>
            </div>
            <div>
              <Label>特殊要求</Label>
              <Textarea rows={3} {...register('special_requirements')} />
            </div>
          </div>
        </Card>

        <div className="flex justify-end gap-3">
          <Button type="button" variant="outline" onClick={() => navigate('/dashboard')}>取消</Button>
          <Button type="submit" size="lg" disabled={isSubmitting}>启动 AutoGen 生成 →</Button>
        </div>
      </form>
    </div>
  )
}
