'use client'

import * as React from 'react'
import { useAuth } from '@/hooks/useAuth'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { EmptyState } from '@/components/ui/empty-state'
import { ptBR } from '@/lib/i18n'
import {
  Briefcase,
  FileText,
  Calendar,
  CheckSquare,
  Plus,
  ArrowRight,
  Clock,
  AlertCircle,
} from 'lucide-react'

export default function WorkspacePage() {
  const { user } = useAuth()
  const t = ptBR

  // Mock data - will be replaced with real API calls
  const todaysTasks = [
    { id: '1', title: 'Revisar peticao inicial', dueDate: '14:00', priority: 'high', caseNumber: '1234567-89.2024.8.26.0100' },
    { id: '2', title: 'Ligar para cliente Maria Silva', dueDate: '15:30', priority: 'medium' },
    { id: '3', title: 'Preparar documentos para audiencia', dueDate: '17:00', priority: 'urgent', caseNumber: '9876543-21.2024.8.26.0100' },
  ]

  const recentMovements = [
    { id: '1', caseNumber: '1234567-89.2024.8.26.0100', description: 'Juntada de documento', date: 'Hoje, 10:30', isImportant: true },
    { id: '2', caseNumber: '9876543-21.2024.8.26.0100', description: 'Despacho do juiz', date: 'Hoje, 09:15', isImportant: true },
    { id: '3', caseNumber: '5555555-55.2024.8.26.0100', description: 'Conclusao ao juiz', date: 'Ontem, 16:45', isImportant: false },
  ]

  const upcomingHearings = [
    { id: '1', caseNumber: '1234567-89.2024.8.26.0100', date: '20/01/2026', time: '14:00', court: '5a Vara Civel', type: 'Audiencia de conciliacao' },
    { id: '2', caseNumber: '9876543-21.2024.8.26.0100', date: '22/01/2026', time: '10:30', court: '2a Vara Trabalhista', type: 'Audiencia de instrucao' },
  ]

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent': return 'destructive'
      case 'high': return 'warning'
      case 'medium': return 'default'
      default: return 'secondary'
    }
  }

  const getPriorityLabel = (priority: string) => {
    switch (priority) {
      case 'urgent': return t.tasks.priorityOptions.urgent
      case 'high': return t.tasks.priorityOptions.high
      case 'medium': return t.tasks.priorityOptions.medium
      default: return t.tasks.priorityOptions.low
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          {t.dashboard.welcome}, {user?.displayName || user?.email?.split('@')[0]}!
        </h1>
        <p className="mt-1 text-gray-500">
          Aqui esta um resumo do seu dia
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="rounded-lg bg-primary-100 p-3">
                <Briefcase className="h-6 w-6 text-primary-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Processos ativos</p>
                <p className="text-2xl font-bold text-gray-900">42</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="rounded-lg bg-yellow-100 p-3">
                <FileText className="h-6 w-6 text-yellow-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Publicacoes novas</p>
                <p className="text-2xl font-bold text-gray-900">7</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="rounded-lg bg-green-100 p-3">
                <CheckSquare className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Tarefas pendentes</p>
                <p className="text-2xl font-bold text-gray-900">12</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="rounded-lg bg-purple-100 p-3">
                <Calendar className="h-6 w-6 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Audiencias esta semana</p>
                <p className="text-2xl font-bold text-gray-900">3</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Today's Tasks */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <CheckSquare className="h-5 w-5" />
              {t.dashboard.todaysTasks}
            </CardTitle>
            <Button variant="ghost" size="sm">
              Ver todas <ArrowRight className="ml-1 h-4 w-4" />
            </Button>
          </CardHeader>
          <CardContent>
            {todaysTasks.length > 0 ? (
              <div className="space-y-3">
                {todaysTasks.map((task) => (
                  <div
                    key={task.id}
                    className="flex items-center justify-between rounded-lg border border-gray-100 bg-gray-50 p-3"
                  >
                    <div className="flex-1">
                      <p className="font-medium text-gray-900">{task.title}</p>
                      {task.caseNumber && (
                        <p className="mt-0.5 text-xs text-gray-500">{task.caseNumber}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={getPriorityColor(task.priority) as 'default'}>
                        {getPriorityLabel(task.priority)}
                      </Badge>
                      <span className="flex items-center text-sm text-gray-500">
                        <Clock className="mr-1 h-3 w-3" />
                        {task.dueDate}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                icon="calendar"
                title="Nenhuma tarefa para hoje"
                description="Todas as tarefas foram concluidas!"
              />
            )}
          </CardContent>
        </Card>

        {/* Recent Movements */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              {t.dashboard.recentMovements}
            </CardTitle>
            <Button variant="ghost" size="sm">
              Ver todos <ArrowRight className="ml-1 h-4 w-4" />
            </Button>
          </CardHeader>
          <CardContent>
            {recentMovements.length > 0 ? (
              <div className="space-y-3">
                {recentMovements.map((movement) => (
                  <div
                    key={movement.id}
                    className="flex items-start gap-3 rounded-lg border border-gray-100 bg-gray-50 p-3"
                  >
                    {movement.isImportant && (
                      <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-yellow-500" />
                    )}
                    <div className="flex-1">
                      <p className="font-medium text-gray-900">{movement.description}</p>
                      <p className="mt-0.5 text-xs text-gray-500">{movement.caseNumber}</p>
                    </div>
                    <span className="text-xs text-gray-500">{movement.date}</span>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                icon="cases"
                title="Nenhum andamento recente"
                description="Os andamentos dos seus processos aparecerao aqui."
              />
            )}
          </CardContent>
        </Card>

        {/* Upcoming Hearings */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              {t.dashboard.upcomingHearings}
            </CardTitle>
            <Button variant="ghost" size="sm">
              Ver agenda <ArrowRight className="ml-1 h-4 w-4" />
            </Button>
          </CardHeader>
          <CardContent>
            {upcomingHearings.length > 0 ? (
              <div className="grid gap-4 sm:grid-cols-2">
                {upcomingHearings.map((hearing) => (
                  <div
                    key={hearing.id}
                    className="rounded-lg border border-gray-200 bg-white p-4"
                  >
                    <div className="flex items-center justify-between">
                      <Badge variant="outline">{hearing.type}</Badge>
                      <span className="text-sm font-medium text-primary-600">
                        {hearing.date} as {hearing.time}
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-gray-500">{hearing.caseNumber}</p>
                    <p className="mt-1 text-sm text-gray-700">{hearing.court}</p>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                icon="calendar"
                title="Nenhuma audiencia agendada"
                description="As proximas audiencias aparecerao aqui."
              />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>{t.dashboard.quickActions}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Button variant="outline" className="h-auto flex-col gap-2 py-4">
              <Plus className="h-5 w-5" />
              <span>{t.cases.newCase}</span>
            </Button>
            <Button variant="outline" className="h-auto flex-col gap-2 py-4">
              <Plus className="h-5 w-5" />
              <span>{t.contacts.newContact}</span>
            </Button>
            <Button variant="outline" className="h-auto flex-col gap-2 py-4">
              <Plus className="h-5 w-5" />
              <span>{t.tasks.newTask}</span>
            </Button>
            <Button variant="outline" className="h-auto flex-col gap-2 py-4">
              <Plus className="h-5 w-5" />
              <span>{t.financial.newEntry}</span>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
