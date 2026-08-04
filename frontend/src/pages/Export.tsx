import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { cn } from '@/lib/utils'
import { downloadExport, exportCase } from '@/features/cases/api'

export default function Export() {
  const { id } = useParams<{ id: string }>()
  const [format, setFormat] = useState<'docx' | 'pdf'>('docx')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleDownload = async () => {
    if (!id) return
    setLoading(true)
    setError('')
    try {
      const res = await exportCase(id, format)
      await downloadExport(id, res.export_id, `case-package.${format}`)
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        '导出失败，请确认案例已生成'
      setError(String(msg))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl">
      <h1 className="mb-6 text-2xl font-bold">导出授课包</h1>
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <h3 className="font-semibold">包含内容</h3>
          <ul className="mt-4 space-y-2 text-sm text-gray-700">
            <li>✓ 案例正文</li>
            <li>✓ 讨论题（分层）</li>
            <li>✓ 教师参考手册</li>
            <li>✓ 教学目标对齐表</li>
            <li>✓ 虚构情境声明</li>
          </ul>
        </Card>
        <div>
          <button
            type="button"
            onClick={() => setFormat('docx')}
            className={cn(
              'mb-3 w-full rounded-xl border-2 p-4 text-left',
              format === 'docx' ? 'border-primary bg-primary-light' : 'border-gray-200',
            )}
          >
            <h4 className="font-semibold">Word 授课包 (.docx)</h4>
            <p className="text-xs text-gray-500">可编辑，合并排版</p>
          </button>
          <button
            type="button"
            onClick={() => setFormat('pdf')}
            className={cn(
              'mb-3 w-full rounded-xl border-2 p-4 text-left',
              format === 'pdf' ? 'border-primary bg-primary-light' : 'border-gray-200',
            )}
          >
            <h4 className="font-semibold">PDF 文档 (.pdf)</h4>
            <p className="text-xs text-gray-500">适合打印分发（中文建议优先 Word）</p>
          </button>
          {error && <p className="text-xs text-red-600">{error}</p>}
          <Button className="mt-4 w-full" size="lg" disabled={loading} onClick={handleDownload}>
            {loading ? '导出中…' : `下载 ${format === 'docx' ? 'Word' : 'PDF'}`}
          </Button>
        </div>
      </div>
    </div>
  )
}
