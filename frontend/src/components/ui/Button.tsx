import { cn } from '@/lib/utils'
import { ButtonHTMLAttributes, forwardRef } from 'react'

type Variant = 'primary' | 'outline' | 'ghost' | 'heroPrimary' | 'heroSecondary'
type Size = 'sm' | 'md' | 'lg'

const variants: Record<Variant, string> = {
  primary: 'bg-primary text-white shadow-sm shadow-indigo-200 hover:bg-primary-dark hover:shadow-md',
  outline: 'bg-white text-slate-700 border border-slate-300 hover:border-slate-400 hover:bg-slate-50',
  ghost: 'bg-transparent text-slate-500 hover:bg-slate-100 hover:text-slate-800',
  heroPrimary: 'bg-white text-primary-dark font-semibold shadow-lg shadow-indigo-950/20 hover:bg-indigo-50',
  heroSecondary: 'bg-transparent text-white border-2 border-white/75 hover:bg-white/10',
}

const sizes: Record<Size, string> = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-3 text-base',
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    />
  ),
)
Button.displayName = 'Button'
