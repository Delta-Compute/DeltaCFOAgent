'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
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
import { formatDateBR, formatCurrencyBR } from '@/lib/utils'
import { Plus, Search, Filter, MoreVertical, Eye } from 'lucide-react'
import {
  Dropdown,
  DropdownTrigger,
  DropdownContent,
  DropdownItem,
} from '@/components/ui/dropdown'

// Mock data
const mockCases = [
  {
    id: '1',
    cnjNumber: '1234567-89.2024.8.26.0100',
    title: 'Acao de cobranca',
    client: 'Maria Silva',
    court: 'TJSP',
    courtUnit: '5a Vara Civel',
    areaOfLaw: 'civil',
    status: 'active',
    value: 50000,
    lastMovementAt: new Date('2026-01-10'),
  },
  {
    id: '2',
    cnjNumber: '9876543-21.2024.8.26.0100',
    title: 'Reclamacao trabalhista',
    client: 'Joao Santos',
    court: 'TRT-2',
    courtUnit: '2a Vara Trabalhista',
    areaOfLaw: 'trabalhista',
    status: 'active',
    value: 75000,
    lastMovementAt: new Date('2026-01-12'),
  },
  {
    id: '3',
    cnjNumber: '5555555-55.2024.8.26.0100',
    title: 'Divorcio consensual',
    client: 'Ana Oliveira',
    court: 'TJSP',
    courtUnit: '1a Vara de Familia',
    areaOfLaw: 'familia',
    status: 'closed',
    value: 0,
    lastMovementAt: new Date('2025-12-20'),
  },
]

export default function CasesPage() {
  const t = ptBR
  const router = useRouter()
  const [searchTerm, setSearchTerm] = React.useState('')
  const [statusFilter, setStatusFilter] = React.useState('all')
  const [areaFilter, setAreaFilter] = React.useState('all')

  const filteredCases = mockCases.filter((c) => {
    const matchesSearch =
      c.cnjNumber.includes(searchTerm) ||
      c.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.client.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesStatus = statusFilter === 'all' || c.status === statusFilter
    const matchesArea = areaFilter === 'all' || c.areaOfLaw === areaFilter
    return matchesSearch && matchesStatus && matchesArea
  })

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return <Badge variant="success">{t.cases.statusOptions.active}</Badge>
      case 'archived':
        return <Badge variant="secondary">{t.cases.statusOptions.archived}</Badge>
      case 'closed':
        return <Badge variant="outline">{t.cases.statusOptions.closed}</Badge>
      default:
        return <Badge>{status}</Badge>
    }
  }

  const getAreaLabel = (area: string) => {
    return t.cases.areasOfLaw[area as keyof typeof t.cases.areasOfLaw] || area
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t.cases.title}</h1>
          <p className="mt-1 text-gray-500">
            Gerencie todos os seus processos e casos
          </p>
        </div>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          {t.cases.newCase}
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <Input
                placeholder="Pesquisar por numero CNJ, titulo ou cliente..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select
              options={[
                { value: 'all', label: 'Todos os status' },
                { value: 'active', label: t.cases.statusOptions.active },
                { value: 'archived', label: t.cases.statusOptions.archived },
                { value: 'closed', label: t.cases.statusOptions.closed },
              ]}
              value={statusFilter}
              onChange={setStatusFilter}
              className="w-48"
            />
            <Select
              options={[
                { value: 'all', label: 'Todas as areas' },
                { value: 'civil', label: t.cases.areasOfLaw.civil },
                { value: 'trabalhista', label: t.cases.areasOfLaw.trabalhista },
                { value: 'familia', label: t.cases.areasOfLaw.familia },
                { value: 'criminal', label: t.cases.areasOfLaw.criminal },
                { value: 'previdenciaria', label: t.cases.areasOfLaw.previdenciaria },
              ]}
              value={areaFilter}
              onChange={setAreaFilter}
              className="w-48"
            />
            <Button variant="outline">
              <Filter className="mr-2 h-4 w-4" />
              Mais filtros
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Cases Table */}
      {filteredCases.length > 0 ? (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t.cases.cnjNumber}</TableHead>
                <TableHead>Titulo / Cliente</TableHead>
                <TableHead>{t.cases.court}</TableHead>
                <TableHead>{t.cases.areaOfLaw}</TableHead>
                <TableHead>{t.cases.value}</TableHead>
                <TableHead>{t.cases.status}</TableHead>
                <TableHead>Ultimo andamento</TableHead>
                <TableHead className="w-12"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredCases.map((caseItem) => (
                <TableRow
                  key={caseItem.id}
                  className="cursor-pointer hover:bg-gray-50"
                  onClick={() => router.push(`/main/cases/${caseItem.id}`)}
                >
                  <TableCell>
                    <span className="font-mono text-sm">{caseItem.cnjNumber}</span>
                  </TableCell>
                  <TableCell>
                    <div>
                      <p className="font-medium text-gray-900">{caseItem.title}</p>
                      <p className="text-sm text-gray-500">{caseItem.client}</p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div>
                      <p className="text-gray-900">{caseItem.court}</p>
                      <p className="text-sm text-gray-500">{caseItem.courtUnit}</p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{getAreaLabel(caseItem.areaOfLaw)}</Badge>
                  </TableCell>
                  <TableCell>
                    {caseItem.value > 0 ? formatCurrencyBR(caseItem.value) : '-'}
                  </TableCell>
                  <TableCell>{getStatusBadge(caseItem.status)}</TableCell>
                  <TableCell className="text-gray-500">
                    {formatDateBR(caseItem.lastMovementAt)}
                  </TableCell>
                  <TableCell onClick={(e) => e.stopPropagation()}>
                    <Dropdown>
                      <DropdownTrigger>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownTrigger>
                      <DropdownContent>
                        <DropdownItem onClick={() => router.push(`/main/cases/${caseItem.id}`)}>
                          <Eye className="h-4 w-4" />
                          Ver detalhes
                        </DropdownItem>
                        <DropdownItem>Editar</DropdownItem>
                        <DropdownItem>Adicionar tarefa</DropdownItem>
                        <DropdownItem destructive>Arquivar</DropdownItem>
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
          icon="cases"
          title={t.cases.emptyState.title}
          description={t.cases.emptyState.description}
          actionLabel={t.cases.newCase}
          onAction={() => console.log('New case')}
        />
      )}
    </div>
  )
}
