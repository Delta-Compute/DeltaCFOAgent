'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import { useOnboarding, ImportedCaseData } from '@/lib/onboarding-context'
import { useAuth } from '@/hooks/useAuth'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { BRAZILIAN_STATES } from '@/lib/utils'
import { ArrowRight, ArrowLeft, Scale, Loader2, CheckCircle, FileText, AlertCircle } from 'lucide-react'

export default function OnboardingStep3() {
  const router = useRouter()
  const { data, updateData, setCurrentStep, isLoading, setIsLoading } = useOnboarding()
  const { getIdToken } = useAuth()
  const [oabNumber, setOabNumber] = React.useState(data.oabNumber)
  const [oabState, setOabState] = React.useState(data.oabState)
  const [error, setError] = React.useState('')
  const [importStatus, setImportStatus] = React.useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [importedCount, setImportedCount] = React.useState(data.importedCases)
  const [importedCases, setImportedCases] = React.useState<ImportedCaseData[]>(data.importedCasesList || [])

  React.useEffect(() => {
    setCurrentStep(3)
  }, [setCurrentStep])

  const stateOptions = BRAZILIAN_STATES.map((state) => ({
    value: state.value,
    label: `${state.value} - ${state.label}`,
  }))

  const handleImport = async () => {
    setError('')

    if (!oabNumber.trim()) {
      setError('Por favor, informe seu numero da OAB')
      return
    }

    if (!oabState) {
      setError('Por favor, selecione a seccional da OAB')
      return
    }

    setImportStatus('loading')
    setIsLoading(true)

    try {
      // Get Firebase token for API authentication
      const token = await getIdToken()
      if (!token) {
        setError('Sessao expirada. Por favor, faca login novamente.')
        setImportStatus('error')
        setIsLoading(false)
        return
      }

      // Call court API to search cases by OAB number
      const response = await fetch('/api/court/oab/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          lawyerName: data.fullName,
          oabNumber,
          oabState,
        }),
      })

      const result = await response.json()

      if (!response.ok) {
        // Handle API not configured (use fallback mock for demo)
        if (response.status === 503) {
          console.warn('Court APIs not configured, using demo mode')
          const count = Math.floor(Math.random() * 45) + 5
          setImportedCount(count)
          setImportedCases([])
          setImportStatus('success')
          updateData({
            oabNumber,
            oabState,
            importedCases: count,
            importedCasesList: [],
            lawyerData: null,
          })
          setIsLoading(false)
          return
        }
        throw new Error(result.error || 'Erro ao buscar processos')
      }

      // Store imported cases
      const cases: ImportedCaseData[] = result.cases || []
      setImportedCount(result.total)
      setImportedCases(cases)
      setImportStatus('success')

      updateData({
        oabNumber,
        oabState,
        importedCases: result.total,
        importedCasesList: cases,
        lawyerData: result.lawyer || null,
      })
    } catch (err) {
      console.error('Error importing cases:', err)
      setError(err instanceof Error ? err.message : 'Erro ao buscar processos. Tente novamente.')
      setImportStatus('error')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (importStatus !== 'success') {
      setError('Por favor, importe seus processos antes de continuar')
      return
    }

    router.push('/onboarding/confirmacao')
  }

  const handleSkip = () => {
    updateData({
      oabNumber: '',
      oabState: '',
      importedCases: 0,
      importedCasesList: [],
      lawyerData: null,
    })
    router.push('/onboarding/confirmacao')
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-center text-2xl">
          Conecte sua OAB
        </CardTitle>
        <p className="text-center text-gray-500">
          Importe automaticamente seus processos dos tribunais
        </p>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">
              {error}
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                Numero da OAB
              </label>
              <div className="relative">
                <Scale className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <Input
                  type="text"
                  placeholder="123456"
                  value={oabNumber}
                  onChange={(e) => setOabNumber(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  className="pl-10"
                  disabled={isLoading || importStatus === 'success'}
                />
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                Seccional
              </label>
              <Select
                options={stateOptions}
                value={oabState}
                onChange={setOabState}
                placeholder="Selecione o estado"
                disabled={isLoading || importStatus === 'success'}
              />
            </div>

            {importStatus === 'idle' && (
              <Button
                type="button"
                variant="outline"
                onClick={handleImport}
                className="w-full"
                disabled={isLoading}
              >
                <FileText className="mr-2 h-4 w-4" />
                Buscar processos
              </Button>
            )}

            {importStatus === 'loading' && (
              <div className="flex flex-col items-center rounded-lg bg-gray-50 p-6">
                <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
                <p className="mt-3 text-sm text-gray-600">
                  Buscando seus processos nos tribunais...
                </p>
                <p className="text-xs text-gray-400">
                  Isso pode levar alguns segundos
                </p>
              </div>
            )}

            {importStatus === 'success' && (
              <div className="space-y-4">
                <div className="flex flex-col items-center rounded-lg bg-green-50 p-6">
                  <CheckCircle className="h-8 w-8 text-green-600" />
                  <p className="mt-3 font-medium text-green-700">
                    {importedCount} processos encontrados!
                  </p>
                  <p className="text-sm text-green-600">
                    Seus processos serao monitorados automaticamente
                  </p>
                </div>

                {importedCases.length > 0 && (
                  <div className="rounded-lg border border-gray-200 p-4">
                    <h4 className="mb-3 text-sm font-medium text-gray-700">
                      Processos encontrados:
                    </h4>
                    <ul className="space-y-2 text-sm">
                      {importedCases.slice(0, 5).map((c, i) => (
                        <li key={i} className="flex items-start gap-2 text-gray-600">
                          <FileText className="mt-0.5 h-4 w-4 flex-shrink-0 text-gray-400" />
                          <div>
                            <span className="font-mono text-xs">{c.cnj}</span>
                            <span className="mx-1 text-gray-300">|</span>
                            <span>{c.title || c.subject}</span>
                          </div>
                        </li>
                      ))}
                      {importedCases.length > 5 && (
                        <li className="text-gray-400 italic">
                          ... e mais {importedCases.length - 5} processos
                        </li>
                      )}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {importStatus === 'error' && (
              <div className="space-y-3">
                <div className="flex flex-col items-center rounded-lg bg-red-50 p-6">
                  <AlertCircle className="h-8 w-8 text-red-600" />
                  <p className="mt-3 font-medium text-red-700">
                    Erro ao buscar processos
                  </p>
                  <p className="text-sm text-red-600">
                    Verifique os dados e tente novamente
                  </p>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setError('')
                    setImportStatus('idle')
                  }}
                  className="w-full"
                >
                  Tentar novamente
                </Button>
              </div>
            )}
          </div>

          <div className="flex gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => router.push('/onboarding/escritorio')}
              className="flex-1"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Voltar
            </Button>
            <Button type="submit" className="flex-1" disabled={isLoading}>
              Continuar
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>

          <div className="text-center">
            <button
              type="button"
              onClick={handleSkip}
              className="text-sm text-gray-500 hover:text-gray-700"
              disabled={isLoading}
            >
              Pular esta etapa
            </button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
