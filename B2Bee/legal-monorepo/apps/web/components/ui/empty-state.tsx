import * as React from 'react'
import { cn } from '@/lib/utils'
import { Button } from './button'
import { FileText, Users, Calendar, DollarSign, Briefcase, Bell } from 'lucide-react'

type EmptyStateIcon = 'documents' | 'contacts' | 'calendar' | 'financial' | 'cases' | 'alerts'

interface EmptyStateProps {
  icon?: EmptyStateIcon
  title: string
  description: string
  actionLabel?: string
  onAction?: () => void
  secondaryActionLabel?: string
  onSecondaryAction?: () => void
  className?: string
}

const iconMap = {
  documents: FileText,
  contacts: Users,
  calendar: Calendar,
  financial: DollarSign,
  cases: Briefcase,
  alerts: Bell,
}

const EmptyState = ({
  icon = 'documents',
  title,
  description,
  actionLabel,
  onAction,
  secondaryActionLabel,
  onSecondaryAction,
  className,
}: EmptyStateProps) => {
  const Icon = iconMap[icon]

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center rounded-xl border border-dashed border-gray-300 bg-gray-50 px-6 py-12 text-center',
        className
      )}
    >
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gray-100">
        <Icon className="h-8 w-8 text-gray-400" />
      </div>

      <h3 className="mb-2 text-lg font-semibold text-gray-900">{title}</h3>
      <p className="mb-6 max-w-sm text-sm text-gray-500">{description}</p>

      <div className="flex gap-3">
        {actionLabel && onAction && (
          <Button onClick={onAction}>{actionLabel}</Button>
        )}
        {secondaryActionLabel && onSecondaryAction && (
          <Button variant="outline" onClick={onSecondaryAction}>
            {secondaryActionLabel}
          </Button>
        )}
      </div>
    </div>
  )
}

export { EmptyState }
