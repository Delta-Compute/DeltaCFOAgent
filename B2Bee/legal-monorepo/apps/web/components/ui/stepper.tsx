'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'
import { Check } from 'lucide-react'

export interface Step {
  title: string
  description?: string
}

interface StepperProps {
  steps: Step[]
  currentStep: number
  className?: string
}

const Stepper = ({ steps, currentStep, className }: StepperProps) => {
  return (
    <nav aria-label="Progress" className={className}>
      <ol className="flex items-center">
        {steps.map((step, index) => {
          const isCompleted = index < currentStep
          const isCurrent = index === currentStep
          const isLast = index === steps.length - 1

          return (
            <li key={step.title} className={cn('relative', !isLast && 'flex-1')}>
              <div className="flex items-center">
                <div
                  className={cn(
                    'relative flex h-8 w-8 items-center justify-center rounded-full border-2 transition-colors',
                    isCompleted
                      ? 'border-primary-600 bg-primary-600'
                      : isCurrent
                      ? 'border-primary-600 bg-white'
                      : 'border-gray-300 bg-white'
                  )}
                >
                  {isCompleted ? (
                    <Check className="h-4 w-4 text-white" />
                  ) : (
                    <span
                      className={cn(
                        'text-sm font-medium',
                        isCurrent ? 'text-primary-600' : 'text-gray-500'
                      )}
                    >
                      {index + 1}
                    </span>
                  )}
                </div>

                {!isLast && (
                  <div
                    className={cn(
                      'ml-2 h-0.5 flex-1',
                      isCompleted ? 'bg-primary-600' : 'bg-gray-300'
                    )}
                  />
                )}
              </div>

              <div className="mt-2">
                <span
                  className={cn(
                    'text-xs font-medium',
                    isCompleted || isCurrent ? 'text-primary-600' : 'text-gray-500'
                  )}
                >
                  {step.title}
                </span>
                {step.description && (
                  <p className="text-xs text-gray-500">{step.description}</p>
                )}
              </div>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}

interface VerticalStepperProps {
  steps: Step[]
  currentStep: number
  className?: string
}

const VerticalStepper = ({ steps, currentStep, className }: VerticalStepperProps) => {
  return (
    <nav aria-label="Progress" className={className}>
      <ol className="space-y-4">
        {steps.map((step, index) => {
          const isCompleted = index < currentStep
          const isCurrent = index === currentStep

          return (
            <li key={step.title} className="relative flex gap-3">
              <div className="flex flex-col items-center">
                <div
                  className={cn(
                    'relative flex h-8 w-8 items-center justify-center rounded-full border-2 transition-colors',
                    isCompleted
                      ? 'border-primary-600 bg-primary-600'
                      : isCurrent
                      ? 'border-primary-600 bg-white'
                      : 'border-gray-300 bg-white'
                  )}
                >
                  {isCompleted ? (
                    <Check className="h-4 w-4 text-white" />
                  ) : (
                    <span
                      className={cn(
                        'text-sm font-medium',
                        isCurrent ? 'text-primary-600' : 'text-gray-500'
                      )}
                    >
                      {index + 1}
                    </span>
                  )}
                </div>

                {index < steps.length - 1 && (
                  <div
                    className={cn(
                      'mt-1 h-full w-0.5 flex-1',
                      isCompleted ? 'bg-primary-600' : 'bg-gray-300'
                    )}
                    style={{ minHeight: '24px' }}
                  />
                )}
              </div>

              <div className="pb-4">
                <span
                  className={cn(
                    'text-sm font-medium',
                    isCompleted || isCurrent ? 'text-gray-900' : 'text-gray-500'
                  )}
                >
                  {step.title}
                </span>
                {step.description && (
                  <p className="text-sm text-gray-500">{step.description}</p>
                )}
              </div>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}

export { Stepper, VerticalStepper }
