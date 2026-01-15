import * as React from 'react'
import { cn } from '@/lib/utils'
import { Loader2 } from 'lucide-react'

interface SpinnerProps {
  size?: 'sm' | 'default' | 'lg'
  className?: string
}

export const Spinner = ({ size = 'default', className }: SpinnerProps) => {
  const sizes = {
    sm: 'h-4 w-4',
    default: 'h-6 w-6',
    lg: 'h-8 w-8',
  }

  return (
    <Loader2 className={cn('animate-spin text-primary-600', sizes[size], className)} />
  )
}

interface LoadingOverlayProps {
  message?: string
}

export const LoadingOverlay = ({ message = 'Aguarde, estamos processando suas informacoes' }: LoadingOverlayProps) => (
  <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-white/80 backdrop-blur-sm">
    <Spinner size="lg" />
    <p className="mt-4 text-sm text-gray-600">{message}</p>
  </div>
)

interface SkeletonProps {
  className?: string
}

export const Skeleton = ({ className }: SkeletonProps) => (
  <div
    className={cn(
      'animate-pulse rounded-md bg-gray-200',
      className
    )}
  />
)

interface CardSkeletonProps {
  lines?: number
}

export const CardSkeleton = ({ lines = 3 }: CardSkeletonProps) => (
  <div className="rounded-xl border border-gray-200 bg-white p-6">
    <Skeleton className="mb-4 h-6 w-1/3" />
    {Array.from({ length: lines }).map((_, i) => (
      <Skeleton key={i} className="mb-2 h-4 w-full" />
    ))}
  </div>
)

interface TableSkeletonProps {
  rows?: number
  cols?: number
}

export const TableSkeleton = ({ rows = 5, cols = 4 }: TableSkeletonProps) => (
  <div className="rounded-xl border border-gray-200 bg-white">
    <div className="border-b border-gray-200 p-4">
      <div className="flex gap-4">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-4 flex-1" />
        ))}
      </div>
    </div>
    {Array.from({ length: rows }).map((_, rowIndex) => (
      <div key={rowIndex} className="border-b border-gray-100 p-4 last:border-0">
        <div className="flex gap-4">
          {Array.from({ length: cols }).map((_, colIndex) => (
            <Skeleton key={colIndex} className="h-4 flex-1" />
          ))}
        </div>
      </div>
    ))}
  </div>
)
