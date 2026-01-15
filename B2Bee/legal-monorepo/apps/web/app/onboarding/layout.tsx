'use client'

import { OnboardingProvider, useOnboarding } from '@/lib/onboarding-context'
import { Check } from 'lucide-react'
import Link from 'next/link'

const steps = [
  { number: 1, label: 'Perfil' },
  { number: 2, label: 'Escritorio' },
  { number: 3, label: 'OAB' },
  { number: 4, label: 'Confirmacao' },
  { number: 5, label: 'Equipe' },
]

function OnboardingStepper() {
  const { currentStep } = useOnboarding()

  return (
    <div className="flex items-center justify-center gap-2">
      {steps.map((step, index) => (
        <div key={step.number} className="flex items-center">
          <div
            className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium transition-colors ${
              step.number < currentStep
                ? 'bg-primary-600 text-white'
                : step.number === currentStep
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-200 text-gray-500'
            }`}
          >
            {step.number < currentStep ? (
              <Check className="h-4 w-4" />
            ) : (
              step.number
            )}
          </div>
          <span
            className={`ml-2 hidden text-sm sm:block ${
              step.number <= currentStep ? 'text-gray-900' : 'text-gray-400'
            }`}
          >
            {step.label}
          </span>
          {index < steps.length - 1 && (
            <div
              className={`mx-4 h-px w-8 sm:w-12 ${
                step.number < currentStep ? 'bg-primary-600' : 'bg-gray-200'
              }`}
            />
          )}
        </div>
      ))}
    </div>
  )
}

function OnboardingLayoutContent({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex h-16 max-w-4xl items-center justify-between px-4">
          <Link href="/" className="text-xl font-bold text-primary-600">
            LEGAL AI
          </Link>
          <OnboardingStepper />
        </div>
      </header>

      {/* Content */}
      <main className="mx-auto max-w-2xl px-4 py-8">
        {children}
      </main>
    </div>
  )
}

export default function OnboardingLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <OnboardingProvider>
      <OnboardingLayoutContent>{children}</OnboardingLayoutContent>
    </OnboardingProvider>
  )
}
