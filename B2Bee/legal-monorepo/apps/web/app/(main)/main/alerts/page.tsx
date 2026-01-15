'use client'

import * as React from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { EmptyState } from '@/components/ui/empty-state'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { ptBR } from '@/lib/i18n'
import { formatDateBR } from '@/lib/utils'
import {
  Bell,
  Clock,
  FileText,
  CheckSquare,
  Briefcase,
  Check,
  MoreVertical,
} from 'lucide-react'
import {
  Dropdown,
  DropdownTrigger,
  DropdownContent,
  DropdownItem,
} from '@/components/ui/dropdown'

// Mock data
const mockAlerts = [
  {
    id: '1',
    type: 'deadline',
    title: 'Prazo vencendo',
    message: 'O prazo para contestacao vence em 3 dias',
    caseNumber: '1234567-89.2024.8.26.0100',
    isRead: false,
    createdAt: new Date('2026-01-15T10:00:00'),
  },
  {
    id: '2',
    type: 'publication',
    title: 'Nova publicacao',
    message: 'Intimacao recebida no processo 9876543-21.2024.8.26.0100',
    caseNumber: '9876543-21.2024.8.26.0100',
    isRead: false,
    createdAt: new Date('2026-01-15T09:30:00'),
  },
  {
    id: '3',
    type: 'task',
    title: 'Tarefa atrasada',
    message: 'A tarefa "Revisar peticao" esta atrasada',
    caseNumber: '5555555-55.2024.8.26.0100',
    isRead: true,
    createdAt: new Date('2026-01-14T16:00:00'),
  },
  {
    id: '4',
    type: 'case_movement',
    title: 'Andamento processual',
    message: 'Novo andamento registrado: Juntada de documento',
    caseNumber: '1234567-89.2024.8.26.0100',
    isRead: true,
    createdAt: new Date('2026-01-14T14:00:00'),
  },
]

export default function AlertsPage() {
  const t = ptBR
  const [alerts, setAlerts] = React.useState(mockAlerts)
  const [activeTab, setActiveTab] = React.useState('all')

  const filteredAlerts = alerts.filter((alert) => {
    if (activeTab === 'all') return true
    if (activeTab === 'unread') return !alert.isRead
    return alert.type === activeTab
  })

  const unreadCount = alerts.filter((a) => !a.isRead).length

  const getAlertIcon = (type: string) => {
    switch (type) {
      case 'deadline':
        return <Clock className="h-5 w-5 text-yellow-500" />
      case 'publication':
        return <FileText className="h-5 w-5 text-blue-500" />
      case 'task':
        return <CheckSquare className="h-5 w-5 text-purple-500" />
      case 'case_movement':
        return <Briefcase className="h-5 w-5 text-green-500" />
      default:
        return <Bell className="h-5 w-5 text-gray-500" />
    }
  }

  const getTypeLabel = (type: string) => {
    return t.alerts.types[type as keyof typeof t.alerts.types] || type
  }

  const markAsRead = (id: string) => {
    setAlerts(
      alerts.map((alert) =>
        alert.id === id ? { ...alert, isRead: true } : alert
      )
    )
  }

  const markAllAsRead = () => {
    setAlerts(alerts.map((alert) => ({ ...alert, isRead: true })))
  }

  const formatTimeAgo = (date: Date) => {
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 60) return `${diffMins} min atras`
    if (diffHours < 24) return `${diffHours}h atras`
    return `${diffDays}d atras`
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t.alerts.title}</h1>
          <p className="mt-1 text-gray-500">
            {unreadCount > 0
              ? `Voce tem ${unreadCount} ${unreadCount === 1 ? 'alerta nao lido' : 'alertas nao lidos'}`
              : 'Todos os alertas foram lidos'}
          </p>
        </div>
        {unreadCount > 0 && (
          <Button variant="outline" onClick={markAllAsRead}>
            <Check className="mr-2 h-4 w-4" />
            {t.alerts.markAllAsRead}
          </Button>
        )}
      </div>

      {/* Tabs */}
      <Tabs defaultValue="all" value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="all">
            Todos ({alerts.length})
          </TabsTrigger>
          <TabsTrigger value="unread">
            Nao lidos ({unreadCount})
          </TabsTrigger>
          <TabsTrigger value="deadline">{t.alerts.types.deadline}</TabsTrigger>
          <TabsTrigger value="publication">{t.alerts.types.publication}</TabsTrigger>
          <TabsTrigger value="task">{t.alerts.types.task}</TabsTrigger>
        </TabsList>

        <TabsContent value={activeTab}>
          {filteredAlerts.length > 0 ? (
            <div className="space-y-3">
              {filteredAlerts.map((alert) => (
                <Card
                  key={alert.id}
                  className={`transition-colors ${!alert.isRead ? 'bg-blue-50' : ''}`}
                >
                  <CardContent className="flex items-start gap-4 py-4">
                    <div className="mt-0.5">{getAlertIcon(alert.type)}</div>

                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium text-gray-900">{alert.title}</h3>
                        <Badge variant="outline" className="text-xs">
                          {getTypeLabel(alert.type)}
                        </Badge>
                        {!alert.isRead && (
                          <span className="h-2 w-2 rounded-full bg-blue-500" />
                        )}
                      </div>
                      <p className="mt-1 text-sm text-gray-600">{alert.message}</p>
                      {alert.caseNumber && (
                        <p className="mt-1 font-mono text-xs text-gray-400">
                          {alert.caseNumber}
                        </p>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-400">
                        {formatTimeAgo(alert.createdAt)}
                      </span>
                      <Dropdown>
                        <DropdownTrigger>
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownTrigger>
                        <DropdownContent>
                          {!alert.isRead && (
                            <DropdownItem onClick={() => markAsRead(alert.id)}>
                              {t.alerts.markAsRead}
                            </DropdownItem>
                          )}
                          <DropdownItem>Ver processo</DropdownItem>
                          <DropdownItem destructive>Excluir</DropdownItem>
                        </DropdownContent>
                      </Dropdown>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <EmptyState
              icon="alerts"
              title={t.alerts.emptyState.title}
              description={t.alerts.emptyState.description}
            />
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
