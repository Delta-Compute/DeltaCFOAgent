'use client'

import * as React from 'react'
import { Modal, ModalHeader, ModalTitle, ModalContent, ModalFooter } from '@/components/ui/modal'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Avatar } from '@/components/ui/avatar'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { ptBR } from '@/lib/i18n'
import { formatDateBR } from '@/lib/utils'
import { ContactFormData } from '@/lib/types'
import {
  User,
  Mail,
  Phone,
  FileText,
  MapPin,
  Briefcase,
  Clock,
  Save,
  X,
} from 'lucide-react'

interface ContactModalProps {
  isOpen: boolean
  onClose: () => void
  contact?: ContactFormData | null
  mode: 'view' | 'edit' | 'create'
  onSave?: (contact: ContactFormData) => void
}

const contactTypes = [
  { value: 'client', label: 'Cliente' },
  { value: 'opposing', label: 'Parte contraria' },
  { value: 'witness', label: 'Testemunha' },
  { value: 'expert', label: 'Perito' },
  { value: 'other', label: 'Outro' },
]

export function ContactModal({
  isOpen,
  onClose,
  contact,
  mode,
  onSave,
}: ContactModalProps) {
  const t = ptBR
  const [activeTab, setActiveTab] = React.useState('info')
  const [formData, setFormData] = React.useState<ContactFormData>({
    name: '',
    type: 'client',
    document: '',
    email: '',
    phone: '',
    address: '',
    notes: '',
  })
  const [isSubmitting, setIsSubmitting] = React.useState(false)

  React.useEffect(() => {
    if (contact) {
      setFormData({
        id: contact.id,
        name: contact.name,
        type: contact.type,
        document: contact.document || '',
        email: contact.email || '',
        phone: contact.phone || '',
        address: contact.address || '',
        notes: contact.notes || '',
        cases: contact.cases,
        services: contact.services,
      })
    } else {
      setFormData({
        name: '',
        type: 'client',
        document: '',
        email: '',
        phone: '',
        address: '',
        notes: '',
      })
    }
    setActiveTab('info')
  }, [contact, isOpen])

  const formatPhone = (value: string) => {
    const numbers = value.replace(/\D/g, '')
    if (numbers.length <= 2) return numbers
    if (numbers.length <= 7) return `(${numbers.slice(0, 2)}) ${numbers.slice(2)}`
    if (numbers.length <= 11) {
      return `(${numbers.slice(0, 2)}) ${numbers.slice(2, 7)}-${numbers.slice(7)}`
    }
    return `(${numbers.slice(0, 2)}) ${numbers.slice(2, 7)}-${numbers.slice(7, 11)}`
  }

  const formatDocument = (value: string) => {
    const numbers = value.replace(/\D/g, '')
    if (numbers.length <= 11) {
      // CPF
      if (numbers.length <= 3) return numbers
      if (numbers.length <= 6) return `${numbers.slice(0, 3)}.${numbers.slice(3)}`
      if (numbers.length <= 9) return `${numbers.slice(0, 3)}.${numbers.slice(3, 6)}.${numbers.slice(6)}`
      return `${numbers.slice(0, 3)}.${numbers.slice(3, 6)}.${numbers.slice(6, 9)}-${numbers.slice(9)}`
    } else {
      // CNPJ
      if (numbers.length <= 2) return numbers
      if (numbers.length <= 5) return `${numbers.slice(0, 2)}.${numbers.slice(2)}`
      if (numbers.length <= 8) return `${numbers.slice(0, 2)}.${numbers.slice(2, 5)}.${numbers.slice(5)}`
      if (numbers.length <= 12) return `${numbers.slice(0, 2)}.${numbers.slice(2, 5)}.${numbers.slice(5, 8)}/${numbers.slice(8)}`
      return `${numbers.slice(0, 2)}.${numbers.slice(2, 5)}.${numbers.slice(5, 8)}/${numbers.slice(8, 12)}-${numbers.slice(12, 14)}`
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.name.trim()) return

    setIsSubmitting(true)
    try {
      onSave?.(formData)
      onClose()
    } finally {
      setIsSubmitting(false)
    }
  }

  const isEditable = mode === 'edit' || mode === 'create'
  const title = mode === 'create'
    ? t.contacts.newContact
    : mode === 'edit'
      ? 'Editar Contato'
      : contact?.name || 'Contato'

  return (
    <Modal open={isOpen} onClose={onClose} className="max-w-2xl">
      <ModalHeader>
        <ModalTitle>{title}</ModalTitle>
      </ModalHeader>

      <form onSubmit={handleSubmit}>
        <ModalContent>
          {mode === 'view' && contact ? (
            <Tabs defaultValue="info" value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="mb-4">
                <TabsTrigger value="info">Informacoes</TabsTrigger>
                <TabsTrigger value="cases">
                  Processos ({contact.cases?.length || 0})
                </TabsTrigger>
                <TabsTrigger value="services">
                  Atendimentos ({contact.services?.length || 0})
                </TabsTrigger>
              </TabsList>

              <TabsContent value="info">
                <div className="space-y-4">
                  <div className="flex items-center gap-4">
                    <Avatar fallback={contact.name} size="lg" />
                    <div>
                      <h3 className="text-lg font-medium text-gray-900">{contact.name}</h3>
                      <Badge variant="outline">
                        {contactTypes.find((t) => t.value === contact.type)?.label || contact.type}
                      </Badge>
                    </div>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    {contact.document && (
                      <div className="flex items-center gap-2 text-gray-600">
                        <FileText className="h-4 w-4 text-gray-400" />
                        <span>{contact.document}</span>
                      </div>
                    )}
                    {contact.email && (
                      <div className="flex items-center gap-2 text-gray-600">
                        <Mail className="h-4 w-4 text-gray-400" />
                        <a href={`mailto:${contact.email}`} className="text-primary-600 hover:underline">
                          {contact.email}
                        </a>
                      </div>
                    )}
                    {contact.phone && (
                      <div className="flex items-center gap-2 text-gray-600">
                        <Phone className="h-4 w-4 text-gray-400" />
                        <a href={`tel:${contact.phone}`} className="text-primary-600 hover:underline">
                          {contact.phone}
                        </a>
                      </div>
                    )}
                    {contact.address && (
                      <div className="flex items-center gap-2 text-gray-600">
                        <MapPin className="h-4 w-4 text-gray-400" />
                        <span>{contact.address}</span>
                      </div>
                    )}
                  </div>

                  {contact.notes && (
                    <div className="rounded-lg bg-gray-50 p-4">
                      <h4 className="mb-2 text-sm font-medium text-gray-700">Observacoes</h4>
                      <p className="text-gray-600">{contact.notes}</p>
                    </div>
                  )}
                </div>
              </TabsContent>

              <TabsContent value="cases">
                {contact.cases && contact.cases.length > 0 ? (
                  <div className="space-y-2">
                    {contact.cases.map((c) => (
                      <div
                        key={c.id}
                        className="flex items-center justify-between rounded-lg border border-gray-200 p-3"
                      >
                        <div className="flex items-center gap-3">
                          <Briefcase className="h-5 w-5 text-gray-400" />
                          <div>
                            <p className="font-medium text-gray-900">{c.title}</p>
                            <p className="font-mono text-xs text-gray-500">{c.cnjNumber}</p>
                          </div>
                        </div>
                        <Badge variant="outline">{c.role}</Badge>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-center text-gray-500">Nenhum processo vinculado</p>
                )}
              </TabsContent>

              <TabsContent value="services">
                {contact.services && contact.services.length > 0 ? (
                  <div className="space-y-2">
                    {contact.services.map((s) => (
                      <div
                        key={s.id}
                        className="flex items-center justify-between rounded-lg border border-gray-200 p-3"
                      >
                        <div className="flex items-center gap-3">
                          <Clock className="h-5 w-5 text-gray-400" />
                          <div>
                            <p className="font-medium text-gray-900">{s.title}</p>
                            <p className="text-sm text-gray-500">
                              {formatDateBR(s.date)} - {s.duration} min
                            </p>
                          </div>
                        </div>
                        <Badge variant="outline">{s.type}</Badge>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-center text-gray-500">Nenhum atendimento registrado</p>
                )}
              </TabsContent>
            </Tabs>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-gray-700">
                  Nome *
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                  <Input
                    type="text"
                    placeholder="Nome completo"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="pl-10"
                    required
                    disabled={!isEditable}
                  />
                </div>
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium text-gray-700">
                  Tipo
                </label>
                <Select
                  options={contactTypes}
                  value={formData.type}
                  onChange={(value) => setFormData({ ...formData, type: value })}
                  disabled={!isEditable}
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-gray-700">
                    CPF/CNPJ
                  </label>
                  <div className="relative">
                    <FileText className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                    <Input
                      type="text"
                      placeholder="000.000.000-00"
                      value={formData.document}
                      onChange={(e) => setFormData({ ...formData, document: formatDocument(e.target.value) })}
                      className="pl-10"
                      disabled={!isEditable}
                    />
                  </div>
                </div>

                <div>
                  <label className="mb-1.5 block text-sm font-medium text-gray-700">
                    Telefone
                  </label>
                  <div className="relative">
                    <Phone className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                    <Input
                      type="tel"
                      placeholder="(11) 99999-9999"
                      value={formData.phone}
                      onChange={(e) => setFormData({ ...formData, phone: formatPhone(e.target.value) })}
                      className="pl-10"
                      disabled={!isEditable}
                    />
                  </div>
                </div>
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium text-gray-700">
                  Email
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                  <Input
                    type="email"
                    placeholder="email@exemplo.com"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="pl-10"
                    disabled={!isEditable}
                  />
                </div>
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium text-gray-700">
                  Endereco
                </label>
                <div className="relative">
                  <MapPin className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                  <Input
                    type="text"
                    placeholder="Endereco completo"
                    value={formData.address}
                    onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                    className="pl-10"
                    disabled={!isEditable}
                  />
                </div>
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium text-gray-700">
                  Observacoes
                </label>
                <Textarea
                  placeholder="Notas sobre o contato..."
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  rows={3}
                  disabled={!isEditable}
                />
              </div>
            </div>
          )}
        </ModalContent>

        <ModalFooter>
          <Button type="button" variant="outline" onClick={onClose}>
            <X className="mr-2 h-4 w-4" />
            {mode === 'view' ? 'Fechar' : 'Cancelar'}
          </Button>
          {isEditable && (
            <Button type="submit" disabled={isSubmitting || !formData.name.trim()}>
              <Save className="mr-2 h-4 w-4" />
              {isSubmitting ? 'Salvando...' : 'Salvar'}
            </Button>
          )}
        </ModalFooter>
      </form>
    </Modal>
  )
}
