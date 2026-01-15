'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import { useOnboarding } from '@/lib/onboarding-context'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { User, Phone, ArrowRight } from 'lucide-react'

export default function OnboardingStep1() {
  const router = useRouter()
  const { data, updateData, setCurrentStep } = useOnboarding()
  const [fullName, setFullName] = React.useState(data.fullName)
  const [phone, setPhone] = React.useState(data.phone)
  const [error, setError] = React.useState('')

  React.useEffect(() => {
    setCurrentStep(1)
  }, [setCurrentStep])

  const formatPhone = (value: string) => {
    const numbers = value.replace(/\D/g, '')
    if (numbers.length <= 2) return numbers
    if (numbers.length <= 7) return `(${numbers.slice(0, 2)}) ${numbers.slice(2)}`
    if (numbers.length <= 11) {
      return `(${numbers.slice(0, 2)}) ${numbers.slice(2, 7)}-${numbers.slice(7)}`
    }
    return `(${numbers.slice(0, 2)}) ${numbers.slice(2, 7)}-${numbers.slice(7, 11)}`
  }

  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPhone(formatPhone(e.target.value))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!fullName.trim()) {
      setError('Por favor, informe seu nome completo')
      return
    }

    if (phone.replace(/\D/g, '').length < 10) {
      setError('Por favor, informe um telefone valido')
      return
    }

    updateData({ fullName, phone })
    router.push('/onboarding/escritorio')
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-center text-2xl">
          Bem-vindo ao LEGAL AI
        </CardTitle>
        <p className="text-center text-gray-500">
          Vamos configurar sua conta em poucos minutos
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
                Nome completo
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <Input
                  type="text"
                  placeholder="Seu nome completo"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                Telefone
              </label>
              <div className="relative">
                <Phone className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <Input
                  type="tel"
                  placeholder="(11) 99999-9999"
                  value={phone}
                  onChange={handlePhoneChange}
                  className="pl-10"
                />
              </div>
            </div>
          </div>

          <Button type="submit" className="w-full">
            Continuar
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
