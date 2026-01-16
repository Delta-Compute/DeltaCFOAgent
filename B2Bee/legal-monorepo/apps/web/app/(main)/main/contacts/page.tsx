'use client'

import * as React from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Avatar } from '@/components/ui/avatar'
import { EmptyState } from '@/components/ui/empty-state'
import { ContactModal } from '@/components/contacts'
import { ptBR } from '@/lib/i18n'
import { Contact, ContactFormData } from '@/lib/types'
import { Plus, Search, MoreVertical, Mail, Phone, Eye, Edit, Trash2 } from 'lucide-react'
import {
  Dropdown,
  DropdownTrigger,
  DropdownContent,
  DropdownItem,
} from '@/components/ui/dropdown'

// Mock data
const mockContacts: Contact[] = [
  {
    id: '1',
    name: 'Maria Silva',
    email: 'maria.silva@email.com',
    phone: '(11) 98765-4321',
    type: 'client',
    casesCount: 3,
  },
  {
    id: '2',
    name: 'Joao Santos',
    email: 'joao.santos@empresa.com.br',
    phone: '(11) 91234-5678',
    type: 'client',
    casesCount: 1,
  },
  {
    id: '3',
    name: 'Ana Oliveira',
    email: 'ana.oliveira@gmail.com',
    phone: '(21) 99876-5432',
    type: 'client',
    casesCount: 2,
  },
  {
    id: '4',
    name: 'Carlos Ferreira',
    email: 'carlos@adversario.com',
    phone: '(11) 95555-1234',
    type: 'opposing_party',
    casesCount: 1,
  },
]

export default function ContactsPage() {
  const t = ptBR
  const [searchTerm, setSearchTerm] = React.useState('')
  const [typeFilter, setTypeFilter] = React.useState('all')
  const [modalOpen, setModalOpen] = React.useState(false)
  const [modalMode, setModalMode] = React.useState<'view' | 'edit' | 'create'>('view')
  const [selectedContact, setSelectedContact] = React.useState<Contact | null>(null)

  const openModal = (mode: 'view' | 'edit' | 'create', contact?: Contact) => {
    setModalMode(mode)
    setSelectedContact(contact || null)
    setModalOpen(true)
  }

  const handleSaveContact = (contact: ContactFormData) => {
    console.log('Saving contact:', contact)
    // In production, call API here
  }

  const filteredContacts = mockContacts.filter((contact) => {
    const matchesSearch =
      contact.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      contact.email.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesType = typeFilter === 'all' || contact.type === typeFilter
    return matchesSearch && matchesType
  })

  const getTypeBadge = (type: string) => {
    switch (type) {
      case 'client':
        return <Badge variant="success">{t.contacts.typeOptions.client}</Badge>
      case 'opposing_party':
        return <Badge variant="warning">{t.contacts.typeOptions.opposing_party}</Badge>
      case 'witness':
        return <Badge variant="secondary">{t.contacts.typeOptions.witness}</Badge>
      default:
        return <Badge variant="outline">{t.contacts.typeOptions.other}</Badge>
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t.contacts.title}</h1>
          <p className="mt-1 text-gray-500">
            Gerencie seus clientes e contatos
          </p>
        </div>
        <Button onClick={() => openModal('create')}>
          <Plus className="mr-2 h-4 w-4" />
          {t.contacts.newContact}
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <Input
                placeholder="Pesquisar por nome ou e-mail..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select
              options={[
                { value: 'all', label: 'Todos os tipos' },
                { value: 'client', label: t.contacts.typeOptions.client },
                { value: 'opposing_party', label: t.contacts.typeOptions.opposing_party },
                { value: 'witness', label: t.contacts.typeOptions.witness },
                { value: 'other', label: t.contacts.typeOptions.other },
              ]}
              value={typeFilter}
              onChange={setTypeFilter}
              className="w-48"
            />
          </div>
        </CardContent>
      </Card>

      {/* Contacts Grid */}
      {filteredContacts.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredContacts.map((contact) => (
            <Card key={contact.id} className="relative">
              <CardContent className="pt-6">
                <div className="absolute right-4 top-4">
                  <Dropdown>
                    <DropdownTrigger>
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownTrigger>
                    <DropdownContent>
                      <DropdownItem onClick={() => openModal('view', contact)}>
                        <Eye className="h-4 w-4" />
                        Ver detalhes
                      </DropdownItem>
                      <DropdownItem onClick={() => openModal('edit', contact)}>
                        <Edit className="h-4 w-4" />
                        Editar
                      </DropdownItem>
                      <DropdownItem destructive>
                        <Trash2 className="h-4 w-4" />
                        Excluir
                      </DropdownItem>
                    </DropdownContent>
                  </Dropdown>
                </div>

                <div className="flex flex-col items-center text-center">
                  <Avatar fallback={contact.name} size="lg" />
                  <h3 className="mt-3 font-semibold text-gray-900">{contact.name}</h3>
                  <div className="mt-1">{getTypeBadge(contact.type)}</div>

                  <div className="mt-4 space-y-2 text-sm text-gray-500">
                    <div className="flex items-center justify-center gap-2">
                      <Mail className="h-4 w-4" />
                      <span>{contact.email}</span>
                    </div>
                    <div className="flex items-center justify-center gap-2">
                      <Phone className="h-4 w-4" />
                      <span>{contact.phone}</span>
                    </div>
                  </div>

                  <p className="mt-4 text-sm text-gray-500">
                    {contact.casesCount} {contact.casesCount === 1 ? 'processo' : 'processos'}
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState
          icon="contacts"
          title={t.contacts.emptyState.title}
          description={t.contacts.emptyState.description}
          actionLabel={t.contacts.newContact}
          onAction={() => openModal('create')}
        />
      )}

      {/* Contact Modal */}
      <ContactModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        contact={selectedContact}
        mode={modalMode}
        onSave={handleSaveContact}
      />
    </div>
  )
}
