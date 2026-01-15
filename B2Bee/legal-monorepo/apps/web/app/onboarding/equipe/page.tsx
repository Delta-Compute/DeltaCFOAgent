'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import { useOnboarding } from '@/lib/onboarding-context'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ArrowRight, ArrowLeft, Mail, Plus, X, Users } from 'lucide-react'

export default function OnboardingStep5() {
  const router = useRouter()
  const { data, updateData, setCurrentStep, isLoading, setIsLoading } = useOnboarding()
  const [emails, setEmails] = React.useState<string[]>(
    data.invitedEmails.length > 0 ? data.invitedEmails : ['']
  )
  const [error, setError] = React.useState('')

  React.useEffect(() => {
    setCurrentStep(5)
  }, [setCurrentStep])

  const addEmailField = () => {
    if (emails.length < 5) {
      setEmails([...emails, ''])
    }
  }

  const removeEmailField = (index: number) => {
    if (emails.length > 1) {
      setEmails(emails.filter((_, i) => i !== index))
    }
  }

  const updateEmail = (index: number, value: string) => {
    const newEmails = [...emails]
    newEmails[index] = value
    setEmails(newEmails)
  }

  const validateEmail = (email: string) => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    const validEmails = emails.filter((email) => email.trim())

    // Validate emails that are filled
    for (const email of validEmails) {
      if (!validateEmail(email)) {
        setError(`Email invalido: ${email}`)
        return
      }
    }

    setIsLoading(true)

    // Simulate sending invitations
    await new Promise((resolve) => setTimeout(resolve, 1000))

    updateData({ invitedEmails: validEmails })
    setIsLoading(false)
    router.push('/onboarding/completo')
  }

  const handleSkip = () => {
    updateData({ invitedEmails: [] })
    router.push('/onboarding/completo')
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-center text-2xl">
          Convide sua equipe
        </CardTitle>
        <p className="text-center text-gray-500">
          Adicione colegas para colaborar no escritorio
        </p>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">
              {error}
            </div>
          )}

          <div className="rounded-lg bg-gray-50 p-4">
            <div className="flex items-center gap-3">
              <div className="rounded-full bg-primary-100 p-2">
                <Users className="h-5 w-5 text-primary-600" />
              </div>
              <div>
                <p className="font-medium text-gray-900">Trabalho em equipe</p>
                <p className="text-sm text-gray-500">
                  Membros convidados podem acessar processos, criar tarefas e colaborar
                </p>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            {emails.map((email, index) => (
              <div key={index} className="flex gap-2">
                <div className="relative flex-1">
                  <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                  <Input
                    type="email"
                    placeholder="email@exemplo.com"
                    value={email}
                    onChange={(e) => updateEmail(index, e.target.value)}
                    className="pl-10"
                    disabled={isLoading}
                  />
                </div>
                {emails.length > 1 && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => removeEmailField(index)}
                    disabled={isLoading}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                )}
              </div>
            ))}

            {emails.length < 5 && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={addEmailField}
                className="w-full"
                disabled={isLoading}
              >
                <Plus className="mr-2 h-4 w-4" />
                Adicionar outro email
              </Button>
            )}
          </div>

          <div className="flex gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => router.push('/onboarding/confirmacao')}
              className="flex-1"
              disabled={isLoading}
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Voltar
            </Button>
            <Button type="submit" className="flex-1" disabled={isLoading}>
              {isLoading ? 'Enviando...' : 'Enviar convites'}
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
