import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Check, Download, Eye, FileText, GraduationCap, Images, Layers3, MessageSquareText, Palette, Presentation, ShieldCheck, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { cn } from '@/lib/utils'
import {
  downloadExport,
  exportCase,
  fetchPptOutline,
  type ExportFormat,
  type PptOptions,
  type PptOutlinePreview,
} from '@/features/cases/api'

const FORMATS: Array<{ id: ExportFormat; title: string; desc: string }> = [
  { id: 'docx', title: 'Word 授课包 (.docx)', desc: '适合继续编辑、院系审核和二次排版' },
  { id: 'pdf', title: 'PDF 文档 (.pdf)', desc: '适合定稿归档、打印和课堂分发' },
  { id: 'pptx', title: 'PPT 课堂课件 (.pptx)', desc: '自动提炼内容、按教学节奏分页，可在 WPS 或 PowerPoint 中继续编辑' },
]

const THEMES: Array<{ id: PptOptions['theme']; label: string; desc: string; colors: [string, string, string] }> = [
  { id: 'academic', label: '学术靛蓝', desc: '深色章节页 + 靛蓝信息卡', colors: ['bg-indigo-950', 'bg-indigo-600', 'bg-indigo-100'] },
  { id: 'modern', label: '现代青绿', desc: '青绿数据感 + 清爽大留白', colors: ['bg-slate-800', 'bg-teal-600', 'bg-teal-100'] },
  { id: 'minimal', label: '极简暖灰', desc: '编辑部排版 + 暖金色强调', colors: ['bg-stone-900', 'bg-amber-600', 'bg-amber-100'] },
  { id: 'executive', label: '高管深蓝', desc: '深蓝标题带 + 香槟金重点', colors: ['bg-slate-950', 'bg-amber-500', 'bg-amber-100'] },
  { id: 'vibrant', label: '活力紫红', desc: '紫红撞色 + 课堂互动氛围', colors: ['bg-purple-950', 'bg-rose-500', 'bg-purple-100'] },
]

const DENSITIES: Array<{ id: PptOptions['density']; label: string; desc: string }> = [
  { id: 'concise', label: '精简', desc: '约 24–32 页，突出关键冲突' },
  { id: 'standard', label: '标准', desc: '约 30–40 页，兼顾叙事与可读性' },
  { id: 'detailed', label: '详细', desc: '约 38–50 页，保留更多案例证据' },
]

const MODES: Array<{ id: PptOptions['mode']; label: string; desc: string }> = [
  { id: 'lecture', label: '结构化讲授', desc: '完整呈现情境、分析与教学闭环' },
  { id: 'workshop', label: '课堂研讨', desc: '强化任务、计时、决策与小组汇报' },
  { id: 'visual', label: '视觉叙事', desc: '增加大图与留白，适合投屏讲故事' },
]

export default function Export() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [format, setFormat] = useState<ExportFormat>('docx')
  const [pptOptions, setPptOptions] = useState<PptOptions>({ theme: 'executive', density: 'standard', audience: 'teacher', mode: 'lecture', include_speaker_notes: true })
  const [outline, setOutline] = useState<PptOutlinePreview | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id || format !== 'pptx') return
    let active = true
    setPreviewLoading(true)
    fetchPptOutline(id, pptOptions)
      .then((data) => { if (active) setOutline(data) })
      .catch(() => { if (active) setOutline(null) })
      .finally(() => { if (active) setPreviewLoading(false) })
    return () => { active = false }
  }, [id, format, pptOptions.theme, pptOptions.density, pptOptions.audience, pptOptions.mode, pptOptions.include_speaker_notes])

  const updatePptOption = <K extends keyof PptOptions>(key: K, value: PptOptions[K]) => {
    setPptOptions((current) => ({ ...current, [key]: value }))
  }

  const handleDownload = async () => {
    if (!id) return
    setLoading(true)
    setError('')
    try {
      const res = await exportCase(id, format, pptOptions)
      await downloadExport(id, res.export_id, res.filename)
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        '导出失败，请确认案例已生成并通过质量检查'
      setError(String(msg))
    } finally {
      setLoading(false)
    }
  }

  const formatLabel = format === 'docx' ? 'Word 授课包' : format === 'pdf' ? 'PDF 授课包' : 'PPT 课堂课件'

  return (
    <div className="mx-auto max-w-6xl">
      <button type="button" onClick={() => navigate(`/case/${id}`)} className="mb-5 inline-flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-slate-900"><ArrowLeft size={16} />返回案例</button>
      <div className="mb-8">
        <p className="text-sm font-semibold text-primary">最后一步</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight">把案例变成可直接使用的教学材料</h1>
        <p className="mt-2 text-sm text-slate-500">文档用于审核与分发，PPT 会自动提炼案例内容并按课堂教学节奏重新组织。</p>
      </div>

      <div className="grid items-start gap-7 lg:grid-cols-[330px_minmax(0,1fr)]">
        <Card className="bg-slate-950 text-white lg:sticky lg:top-8">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-white/10">{format === 'pptx' ? <Presentation size={22} /> : <FileText size={22} />}</span>
          <h3 className="mt-5 text-lg font-bold">{format === 'pptx' ? '课堂课件包含' : '授课文档包含'}</h3>
          <ul className="mt-5 space-y-3 text-sm text-slate-300">
            {(format === 'pptx'
              ? ['大图封面、章节转场与课堂路径', '图片画廊、方法路径与价值坐标', '按阶段拆分的视觉叙事', '决策框架、研讨任务与目标评价', pptOptions.audience === 'teacher' ? '逐页讲师备注与授课时间线' : '适合直接投放的学生视图']
              : ['案例正文与决策点', '分层讨论题', '教师参考手册', '教学目标对齐表', '虚构情境声明']
            ).map((item) => <li key={item} className="flex items-start gap-2"><Check size={15} className="mt-0.5 shrink-0 text-emerald-400" />{item}</li>)}
          </ul>
          <div className="mt-7 flex gap-2 rounded-xl bg-white/5 p-3 text-xs leading-5 text-slate-400"><ShieldCheck size={17} className="shrink-0 text-emerald-400" />PPTX 中的文字、图形和表格均可在 WPS 或 PowerPoint 中继续编辑。</div>
        </Card>

        <div className="space-y-5">
          <section className="space-y-3">
            <div><p className="text-xs font-bold uppercase tracking-wider text-slate-400">01</p><h2 className="mt-1 font-bold text-slate-900">选择输出格式</h2></div>
            {FORMATS.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setFormat(item.id)}
                className={cn('w-full rounded-2xl border-2 bg-white p-5 text-left transition hover:border-indigo-300', format === item.id ? 'border-primary bg-primary-light' : 'border-slate-200')}
              >
                <div className="flex items-start justify-between gap-3"><div><h4 className="font-bold">{item.title}</h4><p className="mt-1 text-sm leading-6 text-slate-500">{item.desc}</p></div>{format === item.id && <span className="shrink-0 rounded-full bg-primary px-2 py-1 text-xs font-semibold text-white">已选择</span>}</div>
              </button>
            ))}
          </section>

          {format === 'pptx' && (
            <section className="space-y-5 rounded-2xl border border-slate-200 bg-white p-5 md:p-6">
              <div><p className="text-xs font-bold uppercase tracking-wider text-slate-400">02</p><h2 className="mt-1 font-bold text-slate-900">设置课件风格</h2><p className="mt-1 text-xs text-slate-500">系统会重新组织内容，不会把长文整段复制到幻灯片。</p></div>

              <div>
                <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-700"><Palette size={16} />视觉主题</div>
                <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
                  {THEMES.map((theme) => <button key={theme.id} type="button" onClick={() => updatePptOption('theme', theme.id)} className={cn('overflow-hidden rounded-xl border text-left transition', pptOptions.theme === theme.id ? 'border-primary bg-indigo-50 ring-1 ring-primary/20' : 'border-slate-200 hover:border-slate-300')}><span className="block bg-white p-2"><span className={cn('relative block aspect-[16/8] overflow-hidden rounded-md', theme.colors[2])}><span className={cn('absolute inset-y-0 left-0 w-[42%]', theme.colors[0])} /><span className={cn('absolute left-[9%] top-[24%] h-1.5 w-[22%] rounded-full', theme.colors[1])} /><span className="absolute left-[9%] top-[41%] h-1 w-[25%] rounded-full bg-white/80" /><span className="absolute left-[50%] top-[18%] h-[64%] w-[41%] rounded bg-white shadow-sm" /><span className={cn('absolute left-[55%] top-[30%] h-1.5 w-[27%] rounded-full', theme.colors[1])} /><span className="absolute left-[55%] top-[47%] h-1 w-[27%] rounded-full bg-slate-200" /><span className="absolute left-[55%] top-[60%] h-1 w-[20%] rounded-full bg-slate-200" /></span></span><span className="block px-3 pb-3 pt-1"><span className="block text-sm font-semibold">{theme.label}</span><span className="mt-1 block text-xs leading-5 text-slate-500">{theme.desc}</span></span></button>)}
                </div>
              </div>

              <div>
                <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-700"><Layers3 size={16} />内容密度</div>
                <div className="grid gap-2 md:grid-cols-3">
                  {DENSITIES.map((density) => <button key={density.id} type="button" onClick={() => updatePptOption('density', density.id)} className={cn('rounded-xl border p-3 text-left transition', pptOptions.density === density.id ? 'border-primary bg-indigo-50' : 'border-slate-200 hover:border-slate-300')}><span className="block text-sm font-semibold">{density.label}</span><span className="mt-1 block text-xs leading-5 text-slate-500">{density.desc}</span></button>)}
                </div>
              </div>

              <div>
                <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-700"><MessageSquareText size={16} />课堂模式</div>
                <div className="grid gap-2 md:grid-cols-3">
                  {MODES.map((mode) => <button key={mode.id} type="button" onClick={() => updatePptOption('mode', mode.id)} className={cn('rounded-xl border p-3 text-left transition', pptOptions.mode === mode.id ? 'border-primary bg-indigo-50' : 'border-slate-200 hover:border-slate-300')}><span className="block text-sm font-semibold">{mode.label}</span><span className="mt-1 block text-xs leading-5 text-slate-500">{mode.desc}</span></button>)}
                </div>
              </div>

              <div>
                <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-700"><GraduationCap size={16} />使用对象</div>
                <div className="grid gap-2 md:grid-cols-2">
                  <button type="button" onClick={() => updatePptOption('audience', 'teacher')} className={cn('rounded-xl border p-3 text-left transition', pptOptions.audience === 'teacher' ? 'border-primary bg-indigo-50' : 'border-slate-200')}><span className="block text-sm font-semibold">教师授课版</span><span className="mt-1 block text-xs text-slate-500">包含教学意图、授课流程、误区和目标对齐</span></button>
                  <button type="button" onClick={() => updatePptOption('audience', 'student')} className={cn('rounded-xl border p-3 text-left transition', pptOptions.audience === 'student' ? 'border-primary bg-indigo-50' : 'border-slate-200')}><span className="block text-sm font-semibold">学生展示版</span><span className="mt-1 block text-xs text-slate-500">隐藏教师提示，适合课堂直接投屏或分发</span></button>
                </div>
              </div>


              <label className="flex cursor-pointer items-center justify-between gap-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
                <span><span className="block text-sm font-semibold text-slate-800">生成讲师备注</span><span className="mt-1 block text-xs text-slate-500">在 WPS/PowerPoint 备注区加入讲解提示、提问方式和建议时长</span></span>
                <input type="checkbox" checked={pptOptions.include_speaker_notes} onChange={(event) => updatePptOption('include_speaker_notes', event.target.checked)} className="h-4 w-4 accent-indigo-600" />
              </label>
            </section>
          )}

          {format === 'pptx' && (
            <section className="rounded-2xl border border-slate-200 bg-slate-50 p-5 md:p-6">
              <div className="flex items-center justify-between gap-3"><div><div className="flex items-center gap-2 text-sm font-semibold text-slate-800"><Eye size={16} />课件目录预览</div><p className="mt-1 text-xs text-slate-500">修改上方选项后，目录和页数会自动更新。</p></div>{outline && <span className="rounded-full bg-white px-3 py-1 text-sm font-bold text-primary shadow-sm">{outline.slide_count} 页</span>}</div>
              {previewLoading ? <div className="mt-4 animate-pulse rounded-xl bg-white p-5 text-sm text-slate-400">正在组织课件内容…</div> : outline ? (
                <><div className="mt-4 rounded-xl border border-indigo-100 bg-gradient-to-r from-indigo-50 to-white p-4"><div className="flex items-center gap-2 text-sm font-bold text-indigo-900"><Sparkles size={16} />{outline.design_metrics.quality_label}</div><p className="mt-1 text-xs leading-5 text-indigo-700/80">{outline.design_metrics.quality_summary}</p><div className="mt-3 flex flex-wrap gap-2 text-[11px] font-semibold text-slate-600"><span className="rounded-full bg-white px-2.5 py-1"><Images size={12} className="mr-1 inline" />视觉页 {outline.design_metrics.visual_pages}</span><span className="rounded-full bg-white px-2.5 py-1">互动页 {outline.design_metrics.activity_pages}</span><span className="rounded-full bg-white px-2.5 py-1">资源附录 {outline.design_metrics.appendix_pages}</span></div></div><div className="mt-4 max-h-80 space-y-2 overflow-y-auto pr-1">{outline.slides.map((slide) => <div key={slide.index} className="flex gap-3 rounded-xl border border-slate-200 bg-white px-3 py-3"><span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-xs font-bold text-slate-500">{slide.index}</span><div className="min-w-0"><div className="flex items-center gap-2"><p className="truncate text-sm font-semibold text-slate-800">{slide.title}</p>{slide.teacher_only && <span className="shrink-0 rounded bg-amber-50 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700">教师</span>}</div>{slide.summary && <p className="mt-1 line-clamp-1 text-xs text-slate-400">{slide.summary}</p>}</div></div>)}</div></>
              ) : <p className="mt-4 rounded-xl bg-white p-4 text-xs text-slate-500">暂时无法预览目录，仍可尝试生成课件。</p>}
            </section>
          )}

          {error && <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700">{error}</p>}
          <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs leading-5 text-slate-500">文件将按“案例主题_{format === 'pptx' ? '教学案例课件_视觉主题' : '教学案例授课包'}_V版本号”命名，便于归档和区分不同样式。</div>
          <Button className="w-full" size="lg" disabled={loading || (format === 'pptx' && previewLoading)} onClick={handleDownload}><Download size={18} />{loading ? `正在生成${formatLabel}…` : `下载${formatLabel}`}</Button>
        </div>
      </div>
    </div>
  )
}
