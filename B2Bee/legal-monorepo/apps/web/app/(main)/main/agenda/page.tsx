'use client'

import * as React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ptBR } from '@/lib/i18n'
import { formatDateBR } from '@/lib/utils'
import {
  Plus,
  ChevronLeft,
  ChevronRight,
  Calendar as CalendarIcon,
  Clock,
  MapPin,
} from 'lucide-react'

// Mock data
const mockEvents = [
  {
    id: '1',
    title: 'Audiencia de conciliacao',
    type: 'hearing',
    startDate: new Date('2026-01-20T14:00:00'),
    endDate: new Date('2026-01-20T15:00:00'),
    location: 'TJSP - 5a Vara Civel',
    caseNumber: '1234567-89.2024.8.26.0100',
  },
  {
    id: '2',
    title: 'Reuniao com cliente',
    type: 'meeting',
    startDate: new Date('2026-01-17T10:00:00'),
    endDate: new Date('2026-01-17T11:00:00'),
    location: 'Escritorio',
    caseNumber: null,
  },
  {
    id: '3',
    title: 'Prazo - Contestacao',
    type: 'deadline',
    startDate: new Date('2026-01-25T23:59:00'),
    endDate: null,
    location: null,
    caseNumber: '9876543-21.2024.8.26.0100',
  },
]

export default function AgendaPage() {
  const t = ptBR
  const [currentDate, setCurrentDate] = React.useState(new Date())
  const [view, setView] = React.useState<'day' | 'week' | 'month'>('week')

  const getEventColor = (type: string) => {
    switch (type) {
      case 'hearing':
        return 'bg-red-100 border-red-300 text-red-800'
      case 'deadline':
        return 'bg-yellow-100 border-yellow-300 text-yellow-800'
      case 'meeting':
        return 'bg-blue-100 border-blue-300 text-blue-800'
      default:
        return 'bg-gray-100 border-gray-300 text-gray-800'
    }
  }

  const getTypeLabel = (type: string) => {
    return t.calendar.typeOptions[type as keyof typeof t.calendar.typeOptions] || type
  }

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  }

  const navigateDate = (direction: 'prev' | 'next') => {
    const newDate = new Date(currentDate)
    if (view === 'day') {
      newDate.setDate(newDate.getDate() + (direction === 'next' ? 1 : -1))
    } else if (view === 'week') {
      newDate.setDate(newDate.getDate() + (direction === 'next' ? 7 : -7))
    } else {
      newDate.setMonth(newDate.getMonth() + (direction === 'next' ? 1 : -1))
    }
    setCurrentDate(newDate)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t.calendar.title}</h1>
          <p className="mt-1 text-gray-500">
            Gerencie suas audiencias, prazos e compromissos
          </p>
        </div>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          {t.calendar.newEvent}
        </Button>
      </div>

      {/* Calendar Controls */}
      <Card>
        <CardContent className="py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Button variant="outline" size="icon" onClick={() => navigateDate('prev')}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="icon" onClick={() => navigateDate('next')}>
                <ChevronRight className="h-4 w-4" />
              </Button>
              <span className="ml-2 text-lg font-medium">
                {currentDate.toLocaleDateString('pt-BR', {
                  month: 'long',
                  year: 'numeric',
                })}
              </span>
            </div>
            <div className="flex gap-1 rounded-lg bg-gray-100 p-1">
              {(['day', 'week', 'month'] as const).map((v) => (
                <Button
                  key={v}
                  variant={view === v ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => setView(v)}
                  className={view === v ? 'bg-white shadow-sm' : ''}
                >
                  {t.calendar.views[v]}
                </Button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Calendar Grid Placeholder */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card>
            <CardContent className="min-h-[500px] p-6">
              <div className="flex h-full flex-col items-center justify-center text-center text-gray-500">
                <CalendarIcon className="h-16 w-16 text-gray-300" />
                <p className="mt-4">Calendario em desenvolvimento...</p>
                <p className="text-sm">A visualizacao completa do calendario sera implementada em breve.</p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Upcoming Events */}
        <div>
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Proximos eventos</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {mockEvents.map((event) => (
                  <div
                    key={event.id}
                    className={`rounded-lg border-l-4 p-3 ${getEventColor(event.type)}`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <p className="font-medium">{event.title}</p>
                        <Badge variant="outline" className="mt-1 text-xs">
                          {getTypeLabel(event.type)}
                        </Badge>
                      </div>
                    </div>

                    <div className="mt-2 space-y-1 text-sm">
                      <div className="flex items-center gap-2">
                        <Clock className="h-3 w-3" />
                        <span>
                          {formatDateBR(event.startDate)} as {formatTime(event.startDate)}
                        </span>
                      </div>
                      {event.location && (
                        <div className="flex items-center gap-2">
                          <MapPin className="h-3 w-3" />
                          <span>{event.location}</span>
                        </div>
                      )}
                    </div>

                    {event.caseNumber && (
                      <p className="mt-2 font-mono text-xs opacity-75">
                        {event.caseNumber}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
