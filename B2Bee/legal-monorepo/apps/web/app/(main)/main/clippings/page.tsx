'use client'

import * as React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { EmptyState } from '@/components/ui/empty-state'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { ptBR } from '@/lib/i18n'
import { formatDateBR } from '@/lib/utils'
import { Search, FileText, Clock, CheckCircle, Eye, Link, Plus } from 'lucide-react'

// Mock data
const mockPublications = [
  {
    id: '1',
    date: new Date('2026-01-15'),
    source: 'diario_oficial',
    journal: 'DJE - Diario da Justica Eletronico',
    type: 'intimacao',
    status: 'new',
    excerpt: 'INTIMACAO: Fica a parte autora intimada para manifestacao sobre os documentos juntados pela parte re...',
    caseNumber: '1234567-89.2024.8.26.0100',
    deadline: new Date('2026-01-30'),
  },
  {
    id: '2',
    date: new Date('2026-01-14'),
    source: 'tribunal',
    journal: 'DJE - Diario da Justica Eletronico',
    type: 'despacho',
    status: 'new',
    excerpt: 'DESPACHO: Defiro o prazo de 15 dias para manifestacao. Intimem-se...',
    caseNumber: '9876543-21.2024.8.26.0100',
    deadline: new Date('2026-01-29'),
  },
  {
    id: '3',
    date: new Date('2026-01-13'),
    source: 'diario_oficial',
    journal: 'DJE - Diario da Justica Eletronico',
    type: 'sentenca',
    status: 'viewed',
    excerpt: 'SENTENCA: Vistos. Julgo procedente o pedido formulado pela parte autora para condenar a parte re...',
    caseNumber: '5555555-55.2024.8.26.0100',
    deadline: null,
  },
  {
    id: '4',
    date: new Date('2026-01-10'),
    source: 'diario_oficial',
    journal: 'DJE - Diario da Justica Eletronico',
    type: 'citacao',
    status: 'handled',
    excerpt: 'CITACAO: Fica a parte re citada para apresentar contestacao no prazo de 15 dias...',
    caseNumber: '1234567-89.2024.8.26.0100',
    deadline: new Date('2026-01-25'),
  },
]

export default function ClippingsPage() {
  const t = ptBR
  const [searchTerm, setSearchTerm] = React.useState('')
  const [statusFilter, setStatusFilter] = React.useState('all')
  const [activeTab, setActiveTab] = React.useState('all')

  const filteredPublications = mockPublications.filter((pub) => {
    const matchesSearch =
      pub.excerpt.toLowerCase().includes(searchTerm.toLowerCase()) ||
      pub.caseNumber.includes(searchTerm)
    const matchesStatus = statusFilter === 'all' || pub.status === statusFilter
    const matchesTab =
      activeTab === 'all' ||
      (activeTab === 'pending' && pub.status !== 'handled') ||
      (activeTab === 'handled' && pub.status === 'handled')
    return matchesSearch && matchesStatus && matchesTab
  })

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'new':
        return <Badge variant="destructive">{t.publications.statusOptions.new}</Badge>
      case 'viewed':
        return <Badge variant="warning">{t.publications.statusOptions.viewed}</Badge>
      case 'handled':
        return <Badge variant="success">{t.publications.statusOptions.handled}</Badge>
      default:
        return <Badge>{status}</Badge>
    }
  }

  const getTypeBadge = (type: string) => {
    return (
      <Badge variant="outline">
        {t.publications.typeOptions[type as keyof typeof t.publications.typeOptions] || type}
      </Badge>
    )
  }

  const newCount = mockPublications.filter((p) => p.status === 'new').length
  const pendingCount = mockPublications.filter((p) => p.status !== 'handled').length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t.publications.title}</h1>
          <p className="mt-1 text-gray-500">
            Acompanhe as publicacoes do Diario Oficial
          </p>
        </div>
        <div className="flex items-center gap-2">
          {newCount > 0 && (
            <Badge variant="destructive" className="text-sm">
              {newCount} novas
            </Badge>
          )}
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="all" value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="all">
            Todas ({mockPublications.length})
          </TabsTrigger>
          <TabsTrigger value="pending">
            Pendentes ({pendingCount})
          </TabsTrigger>
          <TabsTrigger value="handled">
            Tratadas ({mockPublications.length - pendingCount})
          </TabsTrigger>
        </TabsList>

        <TabsContent value={activeTab}>
          {/* Filters */}
          <Card className="mb-6">
            <CardContent className="pt-6">
              <div className="flex flex-wrap gap-4">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                  <Input
                    placeholder="Pesquisar por conteudo ou numero CNJ..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-9"
                  />
                </div>
                <Select
                  options={[
                    { value: 'all', label: 'Todos os status' },
                    { value: 'new', label: t.publications.statusOptions.new },
                    { value: 'viewed', label: t.publications.statusOptions.viewed },
                    { value: 'handled', label: t.publications.statusOptions.handled },
                  ]}
                  value={statusFilter}
                  onChange={setStatusFilter}
                  className="w-48"
                />
              </div>
            </CardContent>
          </Card>

          {/* Publications List */}
          {filteredPublications.length > 0 ? (
            <div className="space-y-4">
              {filteredPublications.map((publication) => (
                <Card key={publication.id} className="overflow-hidden">
                  <div className="flex">
                    <div
                      className={`w-1 ${
                        publication.status === 'new'
                          ? 'bg-red-500'
                          : publication.status === 'viewed'
                          ? 'bg-yellow-500'
                          : 'bg-green-500'
                      }`}
                    />
                    <CardContent className="flex-1 py-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            {getTypeBadge(publication.type)}
                            {getStatusBadge(publication.status)}
                            <span className="text-sm text-gray-500">
                              {formatDateBR(publication.date)}
                            </span>
                          </div>

                          <p className="mt-2 text-gray-900">{publication.excerpt}</p>

                          <div className="mt-3 flex items-center gap-4 text-sm text-gray-500">
                            <span className="flex items-center gap-1">
                              <FileText className="h-4 w-4" />
                              {publication.caseNumber}
                            </span>
                            {publication.deadline && (
                              <span className="flex items-center gap-1 text-yellow-600">
                                <Clock className="h-4 w-4" />
                                Prazo: {formatDateBR(publication.deadline)}
                              </span>
                            )}
                          </div>
                        </div>

                        <div className="ml-4 flex flex-col gap-2">
                          <Button variant="outline" size="sm">
                            <Eye className="mr-1 h-4 w-4" />
                            Ver
                          </Button>
                          {publication.status !== 'handled' && (
                            <>
                              <Button variant="outline" size="sm">
                                <Link className="mr-1 h-4 w-4" />
                                Vincular
                              </Button>
                              <Button size="sm">
                                <Plus className="mr-1 h-4 w-4" />
                                Tarefa
                              </Button>
                            </>
                          )}
                          {publication.status === 'handled' && (
                            <Button variant="ghost" size="sm" className="text-green-600">
                              <CheckCircle className="mr-1 h-4 w-4" />
                              Tratada
                            </Button>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            <EmptyState
              icon="documents"
              title={t.publications.emptyState.title}
              description={t.publications.emptyState.description}
            />
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
