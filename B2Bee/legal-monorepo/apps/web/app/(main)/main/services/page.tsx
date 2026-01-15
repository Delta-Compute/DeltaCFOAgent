'use client'

import * as React from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Avatar } from '@/components/ui/avatar'
import { EmptyState } from '@/components/ui/empty-state'
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from '@/components/ui/table'
import { ptBR } from '@/lib/i18n'
import { formatDateBR } from '@/lib/utils'
import { Plus, Search, MoreVertical, Clock } from 'lucide-react'
import {
  Dropdown,
  DropdownTrigger,
  DropdownContent,
  DropdownItem,
} from '@/components/ui/dropdown'

// Mock data
const mockServices = [
  {
    id: '1',
    title: 'Consulta inicial',
    client: 'Maria Silva',
    type: 'consultation',
    date: new Date('2026-01-15T10:00:00'),
    duration: 60,
    status: 'completed',
  },
  {
    id: '2',
    title: 'Reuniao de acompanhamento',
    client: 'Joao Santos',
    type: 'meeting',
    date: new Date('2026-01-16T14:00:00'),
    duration: 45,
    status: 'scheduled',
  },
  {
    id: '3',
    title: 'Ligacao sobre andamento',
    client: 'Ana Oliveira',
    type: 'call',
    date: new Date('2026-01-14T16:30:00'),
    duration: 15,
    status: 'completed',
  },
]

export default function ServicesPage() {
  const t = ptBR
  const [searchTerm, setSearchTerm] = React.useState('')

  const filteredServices = mockServices.filter(
    (service) =>
      service.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      service.client.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'scheduled':
        return <Badge variant="default">{t.services.statusOptions.scheduled}</Badge>
      case 'completed':
        return <Badge variant="success">{t.services.statusOptions.completed}</Badge>
      case 'cancelled':
        return <Badge variant="secondary">{t.services.statusOptions.cancelled}</Badge>
      default:
        return <Badge>{status}</Badge>
    }
  }

  const getTypeLabel = (type: string) => {
    return t.services.typeOptions[type as keyof typeof t.services.typeOptions] || type
  }

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t.services.title}</h1>
          <p className="mt-1 text-gray-500">
            Registre e acompanhe seus atendimentos
          </p>
        </div>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          {t.services.newService}
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input
              placeholder="Pesquisar por titulo ou cliente..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9"
            />
          </div>
        </CardContent>
      </Card>

      {/* Services Table */}
      {filteredServices.length > 0 ? (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t.services.client}</TableHead>
                <TableHead>{t.services.serviceTitle}</TableHead>
                <TableHead>{t.services.type}</TableHead>
                <TableHead>{t.services.date}</TableHead>
                <TableHead>{t.services.duration}</TableHead>
                <TableHead>{t.services.status}</TableHead>
                <TableHead className="w-12"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredServices.map((service) => (
                <TableRow key={service.id}>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <Avatar fallback={service.client} size="sm" />
                      <span>{service.client}</span>
                    </div>
                  </TableCell>
                  <TableCell className="font-medium">{service.title}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{getTypeLabel(service.type)}</Badge>
                  </TableCell>
                  <TableCell>
                    <div>
                      <p>{formatDateBR(service.date)}</p>
                      <p className="text-sm text-gray-500">{formatTime(service.date)}</p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1 text-gray-500">
                      <Clock className="h-4 w-4" />
                      {service.duration} {t.services.durationMinutes}
                    </div>
                  </TableCell>
                  <TableCell>{getStatusBadge(service.status)}</TableCell>
                  <TableCell>
                    <Dropdown>
                      <DropdownTrigger>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownTrigger>
                      <DropdownContent>
                        <DropdownItem>Ver detalhes</DropdownItem>
                        <DropdownItem>Editar</DropdownItem>
                        <DropdownItem>Adicionar anotacao</DropdownItem>
                        <DropdownItem destructive>Cancelar</DropdownItem>
                      </DropdownContent>
                    </Dropdown>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      ) : (
        <EmptyState
          icon="contacts"
          title={t.services.emptyState.title}
          description={t.services.emptyState.description}
          actionLabel={t.services.newService}
          onAction={() => console.log('New service')}
        />
      )}
    </div>
  )
}
