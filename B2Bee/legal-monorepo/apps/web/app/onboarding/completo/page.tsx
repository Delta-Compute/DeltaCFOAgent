'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import { useOnboarding } from '@/lib/onboarding-context'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  CheckCircle,
  FileText,
  Bell,
  BarChart3,
  Sparkles,
  ArrowRight,
} from 'lucide-react'

const features = [
  {
    icon: FileText,
    title: 'Gestao de Processos',
    description: 'Todos seus processos em um so lugar',
  },
  {
    icon: Bell,
    title: 'Alertas Automaticos',
    description: 'Nunca perca um prazo importante',
  },
  {
    icon: BarChart3,
    title: 'Indicadores',
    description: 'Acompanhe o desempenho do escritorio',
  },
  {
    icon: Sparkles,
    title: 'Inteligencia Artificial',
    description: 'Criacao de pecas com IA',
  },
]

export default function OnboardingComplete() {
  const router = useRouter()
  const { data } = useOnboarding()

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="pt-8 text-center">
          <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-green-100">
            <CheckCircle className="h-10 w-10 text-green-600" />
          </div>

          <h1 className="text-2xl font-bold text-gray-900">
            Parabens, {data.fullName?.split(' ')[0] || 'advogado'}!
          </h1>
          <p className="mt-2 text-gray-500">
            Sua conta esta pronta para uso
          </p>

          {data.importedCases > 0 && (
            <div className="mt-4 inline-flex items-center gap-2 rounded-full bg-primary-100 px-4 py-2 text-sm text-primary-700">
              <FileText className="h-4 w-4" />
              {data.importedCases} processos importados
            </div>
          )}

          {data.invitedEmails.length > 0 && (
            <p className="mt-4 text-sm text-gray-500">
              Convites enviados para {data.invitedEmails.length} pessoa(s)
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-6">
          <h2 className="mb-4 text-center text-lg font-medium text-gray-900">
            O que voce pode fazer agora
          </h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {features.map((feature) => {
              const Icon = feature.icon
              return (
                <div
                  key={feature.title}
                  className="flex items-start gap-3 rounded-lg border border-gray-200 p-3"
                >
                  <div className="rounded-lg bg-primary-50 p-2">
                    <Icon className="h-5 w-5 text-primary-600" />
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-900">{feature.title}</h3>
                    <p className="text-sm text-gray-500">{feature.description}</p>
                  </div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      <Button
        onClick={() => router.push('/main/workspace')}
        className="w-full"
        size="lg"
      >
        Ir para o painel
        <ArrowRight className="ml-2 h-4 w-4" />
      </Button>

      <p className="text-center text-sm text-gray-500">
        Precisa de ajuda?{' '}
        <button className="text-primary-600 hover:underline">
          Fale com nosso suporte
        </button>
      </p>
    </div>
  )
}
