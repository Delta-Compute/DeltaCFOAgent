'use client'

import * as React from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
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
import {
  Plus,
  Search,
  TrendingUp,
  TrendingDown,
  DollarSign,
  MoreVertical,
  Download,
} from 'lucide-react'
import {
  Dropdown,
  DropdownTrigger,
  DropdownContent,
  DropdownItem,
} from '@/components/ui/dropdown'

// Mock data
const mockEntries = [
  {
    id: '1',
    type: 'income',
    category: 'honorarios',
    description: 'Honorarios advocaticios - Maria Silva',
    amount: 5000,
    date: new Date('2026-01-10'),
    status: 'paid',
    caseNumber: '1234567-89.2024.8.26.0100',
  },
  {
    id: '2',
    type: 'expense',
    category: 'custas',
    description: 'Custas processuais - TJSP',
    amount: 350,
    date: new Date('2026-01-12'),
    status: 'paid',
    caseNumber: '9876543-21.2024.8.26.0100',
  },
  {
    id: '3',
    type: 'income',
    category: 'honorarios',
    description: 'Honorarios de exito - Joao Santos',
    amount: 15000,
    date: new Date('2026-01-20'),
    status: 'pending',
    caseNumber: '9876543-21.2024.8.26.0100',
  },
  {
    id: '4',
    type: 'expense',
    category: 'despesas',
    description: 'Material de escritorio',
    amount: 200,
    date: new Date('2026-01-05'),
    status: 'paid',
    caseNumber: null,
  },
]

export default function FinancialEntriesPage() {
  const t = ptBR
  const [activeTab, setActiveTab] = React.useState('entries')
  const [searchTerm, setSearchTerm] = React.useState('')
  const [typeFilter, setTypeFilter] = React.useState('all')

  const filteredEntries = mockEntries.filter((entry) => {
    const matchesSearch = entry.description.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesType = typeFilter === 'all' || entry.type === typeFilter
    return matchesSearch && matchesType
  })

  const totalIncome = mockEntries
    .filter((e) => e.type === 'income')
    .reduce((sum, e) => sum + e.amount, 0)

  const totalExpenses = mockEntries
    .filter((e) => e.type === 'expense')
    .reduce((sum, e) => sum + e.amount, 0)

  const balance = totalIncome - totalExpenses

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'paid':
        return <Badge variant="success">{t.financial.statusOptions.paid}</Badge>
      case 'pending':
        return <Badge variant="warning">{t.financial.statusOptions.pending}</Badge>
      case 'cancelled':
        return <Badge variant="secondary">{t.financial.statusOptions.cancelled}</Badge>
      default:
        return <Badge>{status}</Badge>
    }
  }

  const getCategoryLabel = (category: string) => {
    return t.financial.categories[category as keyof typeof t.financial.categories] || category
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t.financial.title}</h1>
          <p className="mt-1 text-gray-500">
            Gerencie as financas do seu escritorio
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Exportar
          </Button>
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            {t.financial.newEntry}
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="rounded-lg bg-green-100 p-3">
                <TrendingUp className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">{t.financial.typeOptions.income}</p>
                <p className="text-2xl font-bold text-green-600">
                  {formatCurrencyBR(totalIncome)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="rounded-lg bg-red-100 p-3">
                <TrendingDown className="h-6 w-6 text-red-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">{t.financial.typeOptions.expense}</p>
                <p className="text-2xl font-bold text-red-600">
                  {formatCurrencyBR(totalExpenses)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="rounded-lg bg-primary-100 p-3">
                <DollarSign className="h-6 w-6 text-primary-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Saldo</p>
                <p
                  className={`text-2xl font-bold ${
                    balance >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}
                >
                  {formatCurrencyBR(balance)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="entries" value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="entries">{t.financial.entries}</TabsTrigger>
          <TabsTrigger value="invoices">{t.financial.invoices}</TabsTrigger>
          <TabsTrigger value="cashflow">{t.financial.cashFlow}</TabsTrigger>
          <TabsTrigger value="settings">{t.financial.settings}</TabsTrigger>
        </TabsList>

        <TabsContent value="entries">
          {/* Filters */}
          <Card className="mb-6">
            <CardContent className="pt-6">
              <div className="flex flex-wrap gap-4">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                  <Input
                    placeholder="Pesquisar lancamentos..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-9"
                  />
                </div>
                <Select
                  options={[
                    { value: 'all', label: 'Todos os tipos' },
                    { value: 'income', label: t.financial.typeOptions.income },
                    { value: 'expense', label: t.financial.typeOptions.expense },
                  ]}
                  value={typeFilter}
                  onChange={setTypeFilter}
                  className="w-48"
                />
              </div>
            </CardContent>
          </Card>

          {/* Entries Table */}
          {filteredEntries.length > 0 ? (
            <Card>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t.financial.date}</TableHead>
                    <TableHead>{t.financial.description}</TableHead>
                    <TableHead>{t.financial.category}</TableHead>
                    <TableHead>Processo</TableHead>
                    <TableHead className="text-right">{t.financial.amount}</TableHead>
                    <TableHead>{t.financial.status}</TableHead>
                    <TableHead className="w-12"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredEntries.map((entry) => (
                    <TableRow key={entry.id}>
                      <TableCell>{formatDateBR(entry.date)}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {entry.type === 'income' ? (
                            <TrendingUp className="h-4 w-4 text-green-500" />
                          ) : (
                            <TrendingDown className="h-4 w-4 text-red-500" />
                          )}
                          {entry.description}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{getCategoryLabel(entry.category)}</Badge>
                      </TableCell>
                      <TableCell>
                        {entry.caseNumber ? (
                          <span className="font-mono text-xs text-gray-500">
                            {entry.caseNumber}
                          </span>
                        ) : (
                          '-'
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <span
                          className={
                            entry.type === 'income' ? 'text-green-600' : 'text-red-600'
                          }
                        >
                          {entry.type === 'income' ? '+' : '-'}
                          {formatCurrencyBR(entry.amount)}
                        </span>
                      </TableCell>
                      <TableCell>{getStatusBadge(entry.status)}</TableCell>
                      <TableCell>
                        <Dropdown>
                          <DropdownTrigger>
                            <Button variant="ghost" size="icon" className="h-8 w-8">
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownTrigger>
                          <DropdownContent>
                            <DropdownItem>Editar</DropdownItem>
                            <DropdownItem>Marcar como pago</DropdownItem>
                            <DropdownItem destructive>Excluir</DropdownItem>
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
              icon="financial"
              title={t.financial.emptyState.title}
              description={t.financial.emptyState.description}
              actionLabel={t.financial.newEntry}
              onAction={() => console.log('New entry')}
            />
          )}
        </TabsContent>

        <TabsContent value="invoices">
          <EmptyState
            icon="documents"
            title="Nenhuma fatura encontrada"
            description="Crie sua primeira fatura para comecar a cobrar seus clientes."
            actionLabel={t.financial.newInvoice}
            onAction={() => console.log('New invoice')}
          />
        </TabsContent>

        <TabsContent value="cashflow">
          <Card>
            <CardContent className="py-12 text-center text-gray-500">
              Fluxo de caixa em desenvolvimento...
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="settings">
          <Card>
            <CardContent className="py-12 text-center text-gray-500">
              Configuracoes financeiras em desenvolvimento...
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
