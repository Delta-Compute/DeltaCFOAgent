'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import { useOnboarding } from '@/lib/onboarding-context'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ArrowRight, ArrowLeft, User, Users, Building2, Building } from 'lucide-react'
import { cn } from '@/lib/utils'

const firmSizes = [
  {
    id: 'solo',
    label: 'Advogado Solo',
    description: 'Atuo sozinho(a) ou com apoio administrativo',
    icon: User,
    volume: 'Ate 50 processos',
  },
  {
    id: 'small',
    label: 'Escritorio Pequeno',
    description: '2-5 advogados',
    icon: Users,
    volume: '50-200 processos',
  },
  {
    id: 'medium',
    label: 'Escritorio Medio',
    description: '6-20 advogados',
    icon: Building2,
    volume: '200-1000 processos',
  },
  {
    id: 'large',
    label: 'Escritorio Grande',
    description: 'Mais de 20 advogados',
    icon: Building,
    volume: 'Mais de 1000 processos',
  },
] as const

export default function OnboardingStep2() {
  const router = useRouter()
  const { data, updateData, setCurrentStep } = useOnboarding()
  const [selected, setSelected] = React.useState<string>(data.firmSize)
  const [error, setError] = React.useState('')

  React.useEffect(() => {
    setCurrentStep(2)
  }, [setCurrentStep])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!selected) {
      setError('Por favor, selecione o tamanho do seu escritorio')
      return
    }

    const selectedFirm = firmSizes.find((f) => f.id === selected)
    updateData({
      firmSize: selected as 'solo' | 'small' | 'medium' | 'large',
      processVolume: selectedFirm?.volume || '',
    })
    router.push('/onboarding/oab')
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-center text-2xl">
          Qual o tamanho do seu escritorio?
        </CardTitle>
        <p className="text-center text-gray-500">
          Isso nos ajuda a personalizar sua experiencia
        </p>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">
              {error}
            </div>
          )}

          <div className="grid gap-3 sm:grid-cols-2">
            {firmSizes.map((size) => {
              const Icon = size.icon
              return (
                <button
                  key={size.id}
                  type="button"
                  onClick={() => setSelected(size.id)}
                  className={cn(
                    'flex flex-col items-center rounded-lg border-2 p-4 text-center transition-all',
                    selected === size.id
                      ? 'border-primary-600 bg-primary-50'
                      : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                  )}
                >
                  <div
                    className={cn(
                      'mb-3 rounded-full p-3',
                      selected === size.id ? 'bg-primary-100' : 'bg-gray-100'
                    )}
                  >
                    <Icon
                      className={cn(
                        'h-6 w-6',
                        selected === size.id ? 'text-primary-600' : 'text-gray-500'
                      )}
                    />
                  </div>
                  <h3
                    className={cn(
                      'font-medium',
                      selected === size.id ? 'text-primary-700' : 'text-gray-900'
                    )}
                  >
                    {size.label}
                  </h3>
                  <p className="mt-1 text-sm text-gray-500">{size.description}</p>
                  <p className="mt-2 text-xs text-gray-400">{size.volume}</p>
                </button>
              )
            })}
          </div>

          <div className="flex gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => router.push('/onboarding')}
              className="flex-1"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Voltar
            </Button>
            <Button type="submit" className="flex-1">
              Continuar
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
