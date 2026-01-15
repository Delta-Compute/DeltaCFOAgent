'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import { useOnboarding } from '@/lib/onboarding-context'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  ArrowRight,
  ArrowLeft,
  User,
  Building2,
  Scale,
  FileText,
  CheckCircle,
} from 'lucide-react'

export default function OnboardingStep4() {
  const router = useRouter()
  const { data, updateData, setCurrentStep } = useOnboarding()

  React.useEffect(() => {
    setCurrentStep(4)
  }, [setCurrentStep])

  const firmSizeLabels: Record<string, string> = {
    solo: 'Advogado Solo',
    small: 'Escritorio Pequeno (2-5 advogados)',
    medium: 'Escritorio Medio (6-20 advogados)',
    large: 'Escritorio Grande (20+ advogados)',
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    updateData({ confirmed: true })
    router.push('/onboarding/equipe')
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-center text-2xl">
          Confirme suas informacoes
        </CardTitle>
        <p className="text-center text-gray-500">
          Revise os dados antes de finalizar
        </p>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-4">
            {/* Profile */}
            <div className="rounded-lg border border-gray-200 p-4">
              <div className="flex items-center gap-3">
                <div className="rounded-full bg-primary-100 p-2">
                  <User className="h-5 w-5 text-primary-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Nome</p>
                  <p className="font-medium text-gray-900">{data.fullName || '-'}</p>
                </div>
              </div>
            </div>

            {/* Firm */}
            <div className="rounded-lg border border-gray-200 p-4">
              <div className="flex items-center gap-3">
                <div className="rounded-full bg-blue-100 p-2">
                  <Building2 className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Escritorio</p>
                  <p className="font-medium text-gray-900">
                    {firmSizeLabels[data.firmSize] || '-'}
                  </p>
                </div>
              </div>
            </div>

            {/* OAB */}
            <div className="rounded-lg border border-gray-200 p-4">
              <div className="flex items-center gap-3">
                <div className="rounded-full bg-purple-100 p-2">
                  <Scale className="h-5 w-5 text-purple-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">OAB</p>
                  <p className="font-medium text-gray-900">
                    {data.oabNumber && data.oabState
                      ? `${data.oabNumber}/${data.oabState}`
                      : 'Nao informado'}
                  </p>
                </div>
              </div>
            </div>

            {/* Imported Cases */}
            {data.importedCases > 0 && (
              <div className="rounded-lg border border-green-200 bg-green-50 p-4">
                <div className="flex items-center gap-3">
                  <div className="rounded-full bg-green-100 p-2">
                    <FileText className="h-5 w-5 text-green-600" />
                  </div>
                  <div>
                    <p className="text-sm text-green-600">Processos importados</p>
                    <p className="font-medium text-green-700">
                      {data.importedCases} processos
                    </p>
                  </div>
                  <CheckCircle className="ml-auto h-5 w-5 text-green-600" />
                </div>
              </div>
            )}
          </div>

          <div className="rounded-lg bg-gray-50 p-4">
            <h4 className="font-medium text-gray-900">O que acontece agora?</h4>
            <ul className="mt-2 space-y-2 text-sm text-gray-600">
              <li className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-primary-600" />
                Monitoramento automatico de publicacoes
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-primary-600" />
                Alertas de prazos processuais
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-primary-600" />
                Gestao completa do escritorio
              </li>
            </ul>
          </div>

          <div className="flex gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => router.push('/onboarding/oab')}
              className="flex-1"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Voltar
            </Button>
            <Button type="submit" className="flex-1">
              Confirmar
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
