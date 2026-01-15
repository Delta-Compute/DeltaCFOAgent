'use client'

import * as React from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { ptBR } from '@/lib/i18n'
import {
  Sparkles,
  FileText,
  MessageSquare,
  Zap,
  CheckCircle,
  Lock,
  Play,
  ExternalLink,
} from 'lucide-react'

export default function AIHubPage() {
  const t = ptBR.aiHub

  // Mock user plan - would come from auth/subscription context
  const currentPlan = 'UP'

  const features = [
    {
      id: 'publicationProcessing',
      icon: FileText,
      title: t.features.publicationProcessing.title,
      description: t.features.publicationProcessing.description,
      plans: ['COMPANY', 'VIP'],
      color: 'purple',
    },
    {
      id: 'clientUpdates',
      icon: MessageSquare,
      title: t.features.clientUpdates.title,
      description: t.features.clientUpdates.description,
      plans: ['SMART', 'COMPANY', 'VIP'],
      color: 'blue',
    },
    {
      id: 'documentCreation',
      icon: Sparkles,
      title: t.features.documentCreation.title,
      description: t.features.documentCreation.description,
      plans: ['UP', 'SMART', 'COMPANY', 'VIP'],
      color: 'orange',
    },
    {
      id: 'progressPrioritization',
      icon: Zap,
      title: t.features.progressPrioritization.title,
      description: t.features.progressPrioritization.description,
      plans: ['LIGHT', 'UP', 'SMART', 'COMPANY', 'VIP'],
      color: 'green',
    },
  ]

  const isFeatureAvailable = (plans: string[]) => plans.includes(currentPlan)

  const getColorClasses = (color: string, available: boolean) => {
    if (!available) return 'bg-gray-100 text-gray-400'
    switch (color) {
      case 'purple':
        return 'bg-purple-100 text-purple-600'
      case 'blue':
        return 'bg-blue-100 text-blue-600'
      case 'orange':
        return 'bg-orange-100 text-orange-600'
      case 'green':
        return 'bg-green-100 text-green-600'
      default:
        return 'bg-primary-100 text-primary-600'
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        <div className="mb-4 inline-flex items-center justify-center rounded-full bg-gradient-to-r from-purple-100 to-blue-100 p-4">
          <Sparkles className="h-8 w-8 text-purple-600" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900">{t.title}</h1>
        <p className="mx-auto mt-2 max-w-2xl text-gray-500">{t.subtitle}</p>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview">
        <TabsList className="mx-auto flex justify-center">
          <TabsTrigger value="overview">{t.tabs.overview}</TabsTrigger>
          <TabsTrigger value="publicationProcessing">
            {t.tabs.publicationProcessing}
          </TabsTrigger>
          <TabsTrigger value="clientUpdates">{t.tabs.clientUpdates}</TabsTrigger>
          <TabsTrigger value="documentCreation">{t.tabs.documentCreation}</TabsTrigger>
          <TabsTrigger value="progressPrioritization">
            {t.tabs.progressPrioritization}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="grid gap-6 md:grid-cols-2">
            {features.map((feature) => {
              const available = isFeatureAvailable(feature.plans)
              const Icon = feature.icon

              return (
                <Card
                  key={feature.id}
                  className={`relative overflow-hidden ${!available ? 'opacity-75' : ''}`}
                >
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div
                        className={`rounded-lg p-3 ${getColorClasses(feature.color, available)}`}
                      >
                        <Icon className="h-6 w-6" />
                      </div>
                      <Badge variant={available ? 'ai' : 'secondary'}>
                        {available ? (
                          <>
                            <Sparkles className="mr-1 h-3 w-3" />
                            IA
                          </>
                        ) : (
                          <>
                            <Lock className="mr-1 h-3 w-3" />
                            {feature.plans[0]}+
                          </>
                        )}
                      </Badge>
                    </div>
                    <CardTitle className="mt-4">{feature.title}</CardTitle>
                    <CardDescription>{feature.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    {available ? (
                      <Button className="w-full">
                        Usar agora
                        <ExternalLink className="ml-2 h-4 w-4" />
                      </Button>
                    ) : (
                      <Button variant="outline" className="w-full">
                        Fazer upgrade
                      </Button>
                    )}
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </TabsContent>

        <TabsContent value="documentCreation">
          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <Card>
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-orange-100 p-3">
                      <Sparkles className="h-6 w-6 text-orange-600" />
                    </div>
                    <div>
                      <CardTitle>{t.features.documentCreation.title}</CardTitle>
                      <Badge variant="ai" className="mt-1">
                        <Sparkles className="mr-1 h-3 w-3" />
                        IA
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-gray-600">
                    {ptBR.documentCreator.subtitle}
                  </p>

                  <div className="space-y-3">
                    {Object.values(ptBR.documentCreator.benefits).map((benefit, i) => (
                      <div key={i} className="flex items-start gap-2">
                        <CheckCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-green-500" />
                        <span className="text-sm text-gray-600">{benefit}</span>
                      </div>
                    ))}
                  </div>

                  {isFeatureAvailable(['UP', 'SMART', 'COMPANY', 'VIP']) ? (
                    <Button className="w-full" size="lg">
                      Comecar a criar
                      <Sparkles className="ml-2 h-4 w-4" />
                    </Button>
                  ) : (
                    <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4">
                      <p className="font-medium text-yellow-800">
                        {ptBR.documentCreator.notAvailable}
                      </p>
                      <p className="mt-1 text-sm text-yellow-700">
                        {ptBR.documentCreator.upgradePrompt}
                      </p>
                      <Button variant="outline" className="mt-3">
                        {ptBR.documentCreator.viewPlans}
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

            <div>
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">{ptBR.documentCreator.howToStart}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="mb-4 text-sm text-gray-500">
                    {ptBR.documentCreator.howToStartDesc}
                  </p>
                  <div className="aspect-video rounded-lg bg-gray-100 flex items-center justify-center">
                    <Button variant="ghost" size="lg" className="gap-2">
                      <Play className="h-8 w-8" />
                    </Button>
                  </div>
                </CardContent>
              </Card>

              <Card className="mt-4">
                <CardHeader>
                  <CardTitle className="text-lg">Categorias disponiveis</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {Object.values(ptBR.documentCreator.categories).map((category) => (
                      <Badge key={category} variant="outline">
                        {category}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="publicationProcessing">
          <Card>
            <CardContent className="py-12 text-center">
              <FileText className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-4 text-lg font-semibold text-gray-900">
                {t.features.publicationProcessing.title}
              </h3>
              <p className="mt-2 text-gray-500">
                {t.features.publicationProcessing.description}
              </p>
              <p className="mt-4 text-sm text-gray-400">
                Disponivel nos planos: {t.features.publicationProcessing.plans}
              </p>
              {!isFeatureAvailable(['COMPANY', 'VIP']) && (
                <Button className="mt-4">Fazer upgrade</Button>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="clientUpdates">
          <Card>
            <CardContent className="py-12 text-center">
              <MessageSquare className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-4 text-lg font-semibold text-gray-900">
                {t.features.clientUpdates.title}
              </h3>
              <p className="mt-2 text-gray-500">
                {t.features.clientUpdates.description}
              </p>
              <p className="mt-4 text-sm text-gray-400">
                Disponivel nos planos: {t.features.clientUpdates.plans}
              </p>
              {!isFeatureAvailable(['SMART', 'COMPANY', 'VIP']) && (
                <Button className="mt-4">Fazer upgrade</Button>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="progressPrioritization">
          <Card>
            <CardContent className="py-12 text-center">
              <Zap className="mx-auto h-12 w-12 text-green-500" />
              <h3 className="mt-4 text-lg font-semibold text-gray-900">
                {t.features.progressPrioritization.title}
              </h3>
              <p className="mt-2 text-gray-500">
                {t.features.progressPrioritization.description}
              </p>
              <Badge variant="success" className="mt-4">
                Disponivel em todos os planos
              </Badge>
              <Button className="mt-4">Usar agora</Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
