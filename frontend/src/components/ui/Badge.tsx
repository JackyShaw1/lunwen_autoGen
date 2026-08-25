import { cn } from '@/lib/utils'

type BadgeVariant = 'green' | 'yellow' | 'teal' | 'blue' | 'gray' | 'purple' | 'red'

const styles: Record<BadgeVariant, string> = {
  green: 'bg-green-100 text-green-700',
  yellow: 'bg-amber-100 text-amber-700',
  teal: 'bg-primary-light text-primary-dark',
  blue: 'bg-blue-100 text-blue-700',
  gray: 'bg-gray-100 text-gray-500',
  purple: 'bg-purple-100 text-purple-700',
  red: 'bg-red-100 text-red-700',
}

export function Badge({
  variant = 'gray',
  className,
  children,
}: {
  variant?: BadgeVariant
  className?: string
  children: React.ReactNode
}) {
  return (
    <span className={cn('inline-block rounded-full px-2 py-0.5 text-xs font-medium', styles[variant], className)}>
      {children}
    </span>
  )
}

export function statusBadge(status: string) {
  switch (status) {
    case 'finalized':
    case 'completed':
      return <Badge variant="green">已定稿</Badge>
    case 'running':
      return <Badge variant="yellow">Agent 协作中</Badge>
    case 'draft':
      return <Badge variant="gray">草稿</Badge>
    default:
      return <Badge variant="blue">待编辑</Badge>
  }
}
