'use client'

import * as React from 'react'
import { useParams, useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Avatar } from '@/components/ui/avatar'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { ptBR } from '@/lib/i18n'
import { formatDateBR, formatCurrencyBR } from '@/lib/utils'
import {
  ArrowLeft,
  FileText,
  Users,
  Scale,
  Clock,
  CheckSquare,
  DollarSign,
  MessageSquare,
  MoreVertical,
  Plus,
  Building,
  User,
  Calendar,
  AlertCircle,
  ExternalLink,
} from 'lucide-react'
import {
  Dropdown,
  DropdownTrigger,
  DropdownContent,
  DropdownItem,
} from '@/components/ui/dropdown'

// Mock data for a single case
const mockCase = {
  id: '1',
  cnjNumber: '1234567-89.2024.8.26.0100',
  title: 'Acao de Cobranca',
  status: 'active',
  area: 'civil',
  court: 'TJSP - 1a Vara Civel',
  judge: 'Dr. Carlos Alberto Silva',
  distributionDate: new Date('2024-01-15'),
  value: 150000,
  client: {
    id: '1',
    name: 'Maria Silva Santos',
    type: 'client',
    document: '123.456.789-00',
    email: 'maria@email.com',
    phone: '(11) 99999-9999',
  },
  parties: [
    { id: '1', name: 'Maria Silva Santos', role: 'Autor', type: 'client' },
    { id: '2', name: 'Empresa ABC Ltda', role: 'Reu', type: 'opposing' },
    { id: '3', name: 'Dr. Joao Pereira', role: 'Advogado do Reu', type: 'lawyer' },
  ],
  movements: [
    {
      id: '1',
      date: new Date('2024-03-15'),
      title: 'Juntada de documento',
      description: 'Juntada da contestacao apresentada pela parte re',
    },
    {
      id: '2',
      date: new Date('2024-02-20'),
      title: 'Citacao realizada',
      description: 'Citacao da parte re efetuada com sucesso',
    },
    {
      id: '3',
      date: new Date('2024-01-15'),
      title: 'Distribuicao',
      description: 'Processo distribuido para a 1a Vara Civel',
    },
  ],
  tasks: [
    {
      id: '1',
      title: 'Apresentar replica',
      dueDate: new Date('2024-04-01'),
      status: 'pending',
      assignee: 'Dr. Roberto Lima',
    },
    {
      id: '2',
      title: 'Revisar documentos',
      dueDate: new Date('2024-03-25'),
      status: 'completed',
      assignee: 'Ana Costa',
    },
  ],
  documents: [
    { id: '1', name: 'Peticao inicial.pdf', date: new Date('2024-01-15'), type: 'petition' },
    { id: '2', name: 'Procuracao.pdf', date: new Date('2024-01-15'), type: 'power' },
    { id: '3', name: 'Contestacao.pdf', date: new Date('2024-03-15'), type: 'defense' },
  ],
  financials: [
    { id: '1', description: 'Honorarios iniciais', value: 5000, date: new Date('2024-01-20'), type: 'income' },
    { id: '2', description: 'Custas judiciais', value: -350, date: new Date('2024-01-15'), type: 'expense' },
  ],
  notes: 'Cliente muito atento aos prazos. Preferencia por contato via WhatsApp.',
}

const statusColors: Record<string, string> = {
  active: 'bg-green-100 text-green-700',
  suspended: 'bg-yellow-100 text-yellow-700',
  archived: 'bg-gray-100 text-gray-700',
  won: 'bg-blue-100 text-blue-700',
  lost: 'bg-red-100 text-red-700',
}

export default function CaseDetailPage() {
  const t = ptBR
  const params = useParams()
  const router = useRouter()
  const [activeTab, setActiveTab] = React.useState('overview')

  // In production, fetch case by params.id
  const caseData = mockCase

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => router.push('/main/cases')}
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900">
                {caseData.title}
              </h1>
              <Badge className={statusColors[caseData.status]}>
                {t.cases.statusOptions[caseData.status as keyof typeof t.cases.statusOptions]}
              </Badge>
            </div>
            <p className="mt-1 font-mono text-sm text-gray-500">
              {caseData.cnjNumber}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm">
            <ExternalLink className="mr-2 h-4 w-4" />
            Consultar tribunal
          </Button>
          <Dropdown>
            <DropdownTrigger>
              <Button variant="outline" size="icon">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownTrigger>
            <DropdownContent>
              <DropdownItem>Editar processo</DropdownItem>
              <DropdownItem>Arquivar processo</DropdownItem>
              <DropdownItem destructive>Excluir processo</DropdownItem>
            </DropdownContent>
          </Dropdown>
        </div>
      </div>

      {/* Quick Info Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <div className="rounded-lg bg-blue-100 p-2">
              <Building className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Tribunal</p>
              <p className="font-medium text-gray-900">{caseData.court}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <div className="rounded-lg bg-purple-100 p-2">
              <Scale className="h-5 w-5 text-purple-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Juiz</p>
              <p className="font-medium text-gray-900">{caseData.judge}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <div className="rounded-lg bg-green-100 p-2">
              <DollarSign className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Valor da causa</p>
              <p className="font-medium text-gray-900">
                {formatCurrencyBR(caseData.value)}
              </p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 p-4">
            <div className="rounded-lg bg-orange-100 p-2">
              <Calendar className="h-5 w-5 text-orange-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Distribuicao</p>
              <p className="font-medium text-gray-900">
                {formatDateBR(caseData.distributionDate)}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview" value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">
            <FileText className="mr-2 h-4 w-4" />
            Visao Geral
          </TabsTrigger>
          <TabsTrigger value="movements">
            <Clock className="mr-2 h-4 w-4" />
            Andamentos ({caseData.movements.length})
          </TabsTrigger>
          <TabsTrigger value="tasks">
            <CheckSquare className="mr-2 h-4 w-4" />
            Tarefas ({caseData.tasks.length})
          </TabsTrigger>
          <TabsTrigger value="documents">
            <FileText className="mr-2 h-4 w-4" />
            Documentos ({caseData.documents.length})
          </TabsTrigger>
          <TabsTrigger value="financial">
            <DollarSign className="mr-2 h-4 w-4" />
            Financeiro
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview">
          <div className="grid gap-6 lg:grid-cols-3">
            {/* Client Info */}
            <Card className="lg:col-span-1">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <User className="h-4 w-4" />
                  Cliente
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-3">
                  <Avatar fallback={caseData.client.name} size="lg" />
                  <div>
                    <p className="font-medium text-gray-900">{caseData.client.name}</p>
                    <p className="text-sm text-gray-500">{caseData.client.document}</p>
                  </div>
                </div>
                <div className="mt-4 space-y-2 text-sm">
                  <p className="text-gray-600">
                    <span className="text-gray-500">Email:</span> {caseData.client.email}
                  </p>
                  <p className="text-gray-600">
                    <span className="text-gray-500">Telefone:</span> {caseData.client.phone}
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Parties */}
            <Card className="lg:col-span-2">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Users className="h-4 w-4" />
                  Partes do Processo
                </CardTitle>
                <Button variant="ghost" size="sm">
                  <Plus className="mr-2 h-4 w-4" />
                  Adicionar
                </Button>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {caseData.parties.map((party) => (
                    <div
                      key={party.id}
                      className="flex items-center justify-between rounded-lg border border-gray-200 p-3"
                    >
                      <div className="flex items-center gap-3">
                        <Avatar fallback={party.name} size="sm" />
                        <div>
                          <p className="font-medium text-gray-900">{party.name}</p>
                          <p className="text-sm text-gray-500">{party.role}</p>
                        </div>
                      </div>
                      <Badge variant="outline">{party.type}</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Notes */}
            <Card className="lg:col-span-3">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="flex items-center gap-2 text-base">
                  <MessageSquare className="h-4 w-4" />
                  Anotacoes
                </CardTitle>
                <Button variant="ghost" size="sm">Editar</Button>
              </CardHeader>
              <CardContent>
                <p className="text-gray-600">
                  {caseData.notes || 'Nenhuma anotacao adicionada.'}
                </p>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Movements Tab */}
        <TabsContent value="movements">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Andamentos Processuais</CardTitle>
              <Button variant="outline" size="sm">
                <Plus className="mr-2 h-4 w-4" />
                Adicionar
              </Button>
            </CardHeader>
            <CardContent>
              <div className="relative space-y-4">
                {/* Timeline line */}
                <div className="absolute left-4 top-2 h-[calc(100%-16px)] w-px bg-gray-200" />

                {caseData.movements.map((movement, index) => (
                  <div key={movement.id} className="relative flex gap-4 pl-10">
                    <div
                      className={`absolute left-2 top-1 h-5 w-5 rounded-full border-2 ${
                        index === 0
                          ? 'border-primary-600 bg-primary-100'
                          : 'border-gray-300 bg-white'
                      }`}
                    />
                    <div className="flex-1 rounded-lg border border-gray-200 p-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <h4 className="font-medium text-gray-900">{movement.title}</h4>
                          <p className="mt-1 text-sm text-gray-600">
                            {movement.description}
                          </p>
                        </div>
                        <p className="text-sm text-gray-500">
                          {formatDateBR(movement.date)}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tasks Tab */}
        <TabsContent value="tasks">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Tarefas</CardTitle>
              <Button size="sm">
                <Plus className="mr-2 h-4 w-4" />
                Nova Tarefa
              </Button>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {caseData.tasks.map((task) => (
                  <div
                    key={task.id}
                    className="flex items-center justify-between rounded-lg border border-gray-200 p-4"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`h-4 w-4 rounded border-2 ${
                          task.status === 'completed'
                            ? 'border-green-500 bg-green-500'
                            : 'border-gray-300'
                        }`}
                      >
                        {task.status === 'completed' && (
                          <svg className="h-3 w-3 text-white" fill="currentColor" viewBox="0 0 12 12">
                            <path d="M10.28 2.28L3.989 8.575 1.695 6.28A1 1 0 00.28 7.695l3 3a1 1 0 001.414 0l7-7A1 1 0 0010.28 2.28z" />
                          </svg>
                        )}
                      </div>
                      <div>
                        <p
                          className={`font-medium ${
                            task.status === 'completed'
                              ? 'text-gray-400 line-through'
                              : 'text-gray-900'
                          }`}
                        >
                          {task.title}
                        </p>
                        <p className="text-sm text-gray-500">
                          Responsavel: {task.assignee}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-right">
                        <p className="text-sm text-gray-500">Vencimento</p>
                        <p
                          className={`text-sm font-medium ${
                            task.status !== 'completed' &&
                            new Date(task.dueDate) < new Date()
                              ? 'text-red-600'
                              : 'text-gray-900'
                          }`}
                        >
                          {formatDateBR(task.dueDate)}
                        </p>
                      </div>
                      {task.status !== 'completed' &&
                        new Date(task.dueDate) < new Date() && (
                          <AlertCircle className="h-5 w-5 text-red-500" />
                        )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Documents Tab */}
        <TabsContent value="documents">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Documentos</CardTitle>
              <Button size="sm">
                <Plus className="mr-2 h-4 w-4" />
                Upload
              </Button>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {caseData.documents.map((doc) => (
                  <div
                    key={doc.id}
                    className="flex items-center justify-between rounded-lg border border-gray-200 p-3 hover:bg-gray-50"
                  >
                    <div className="flex items-center gap-3">
                      <FileText className="h-5 w-5 text-red-500" />
                      <div>
                        <p className="font-medium text-gray-900">{doc.name}</p>
                        <p className="text-sm text-gray-500">
                          {formatDateBR(doc.date)}
                        </p>
                      </div>
                    </div>
                    <Button variant="ghost" size="sm">
                      Download
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Financial Tab */}
        <TabsContent value="financial">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Movimentacao Financeira</CardTitle>
              <Button size="sm">
                <Plus className="mr-2 h-4 w-4" />
                Novo Lancamento
              </Button>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {caseData.financials.map((entry) => (
                  <div
                    key={entry.id}
                    className="flex items-center justify-between rounded-lg border border-gray-200 p-3"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`rounded-full p-2 ${
                          entry.type === 'income' ? 'bg-green-100' : 'bg-red-100'
                        }`}
                      >
                        <DollarSign
                          className={`h-4 w-4 ${
                            entry.type === 'income' ? 'text-green-600' : 'text-red-600'
                          }`}
                        />
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">{entry.description}</p>
                        <p className="text-sm text-gray-500">
                          {formatDateBR(entry.date)}
                        </p>
                      </div>
                    </div>
                    <p
                      className={`font-medium ${
                        entry.value >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}
                    >
                      {entry.value >= 0 ? '+' : ''}
                      {formatCurrencyBR(Math.abs(entry.value))}
                    </p>
                  </div>
                ))}
              </div>

              {/* Summary */}
              <div className="mt-6 rounded-lg bg-gray-50 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Total de receitas</span>
                  <span className="font-medium text-green-600">
                    {formatCurrencyBR(
                      caseData.financials
                        .filter((e) => e.value > 0)
                        .reduce((sum, e) => sum + e.value, 0)
                    )}
                  </span>
                </div>
                <div className="mt-2 flex items-center justify-between">
                  <span className="text-gray-600">Total de despesas</span>
                  <span className="font-medium text-red-600">
                    {formatCurrencyBR(
                      Math.abs(
                        caseData.financials
                          .filter((e) => e.value < 0)
                          .reduce((sum, e) => sum + e.value, 0)
                      )
                    )}
                  </span>
                </div>
                <div className="mt-3 border-t border-gray-200 pt-3">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-gray-900">Saldo</span>
                    <span className="font-bold text-gray-900">
                      {formatCurrencyBR(
                        caseData.financials.reduce((sum, e) => sum + e.value, 0)
                      )}
                    </span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
