'use client'

import * as React from 'react'
import { Modal, ModalHeader, ModalTitle, ModalContent, ModalFooter } from '@/components/ui/modal'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Select } from '@/components/ui/select'
import { ptBR } from '@/lib/i18n'
import { formatDateBR } from '@/lib/utils'
import {
  FileText,
  Calendar,
  Clock,
  Link as LinkIcon,
  CheckCircle,
  AlertTriangle,
  X,
  ExternalLink,
} from 'lucide-react'

interface Publication {
  id: string
  caseNumber?: string
  source: string
  publicationDate: Date
  content: string
  status: string
  deadline?: Date
  case?: {
    id: string
    cnjNumber: string
    title: string
  }
}

interface PublicationModalProps {
  isOpen: boolean
  onClose: () => void
  publication: Publication | null
  onStatusChange?: (id: string, status: string) => void
  onCreateTask?: (publication: Publication) => void
}

const statusOptions = [
  { value: 'new', label: 'Nova' },
  { value: 'viewed', label: 'Visualizada' },
  { value: 'handled', label: 'Tratada' },
]

export function PublicationModal({
  isOpen,
  onClose,
  publication,
  onStatusChange,
  onCreateTask,
}: PublicationModalProps) {
  const t = ptBR
  const [status, setStatus] = React.useState(publication?.status || 'new')

  React.useEffect(() => {
    if (publication) {
      setStatus(publication.status)
    }
  }, [publication])

  if (!publication) return null

  const getStatusBadge = () => {
    switch (status) {
      case 'new':
        return <Badge variant="default">Nova</Badge>
      case 'viewed':
        return <Badge variant="warning">Visualizada</Badge>
      case 'handled':
        return <Badge variant="success">Tratada</Badge>
      default:
        return <Badge>{status}</Badge>
    }
  }

  const handleStatusChange = (newStatus: string) => {
    setStatus(newStatus)
    onStatusChange?.(publication.id, newStatus)
  }

  const isDeadlineSoon = publication.deadline
    ? new Date(publication.deadline).getTime() - Date.now() < 7 * 24 * 60 * 60 * 1000
    : false

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <ModalHeader>
        <div className="flex items-center justify-between">
          <ModalTitle>Publicacao</ModalTitle>
          {getStatusBadge()}
        </div>
      </ModalHeader>

      <ModalContent>
        <div className="space-y-6">
          {/* Meta info */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex items-center gap-2 text-gray-600">
              <FileText className="h-4 w-4 text-gray-400" />
              <span className="text-sm">Fonte: {publication.source}</span>
            </div>
            <div className="flex items-center gap-2 text-gray-600">
              <Calendar className="h-4 w-4 text-gray-400" />
              <span className="text-sm">
                Publicado em: {formatDateBR(publication.publicationDate)}
              </span>
            </div>
            {publication.caseNumber && (
              <div className="flex items-center gap-2 text-gray-600">
                <LinkIcon className="h-4 w-4 text-gray-400" />
                <span className="font-mono text-sm">{publication.caseNumber}</span>
              </div>
            )}
            {publication.deadline && (
              <div
                className={`flex items-center gap-2 ${
                  isDeadlineSoon ? 'text-red-600' : 'text-gray-600'
                }`}
              >
                {isDeadlineSoon ? (
                  <AlertTriangle className="h-4 w-4" />
                ) : (
                  <Clock className="h-4 w-4 text-gray-400" />
                )}
                <span className="text-sm">
                  Prazo: {formatDateBR(publication.deadline)}
                </span>
              </div>
            )}
          </div>

          {/* Linked case */}
          {publication.case && (
            <div className="rounded-lg border border-gray-200 p-4">
              <h4 className="mb-2 text-sm font-medium text-gray-700">
                Processo vinculado
              </h4>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">{publication.case.title}</p>
                  <p className="font-mono text-sm text-gray-500">
                    {publication.case.cnjNumber}
                  </p>
                </div>
                <Button variant="outline" size="sm">
                  <ExternalLink className="mr-2 h-4 w-4" />
                  Ver processo
                </Button>
              </div>
            </div>
          )}

          {/* Content */}
          <div>
            <h4 className="mb-2 text-sm font-medium text-gray-700">
              Conteudo da publicacao
            </h4>
            <div className="max-h-64 overflow-y-auto rounded-lg bg-gray-50 p-4">
              <p className="whitespace-pre-wrap text-sm text-gray-700">
                {publication.content}
              </p>
            </div>
          </div>

          {/* Status change */}
          <div>
            <h4 className="mb-2 text-sm font-medium text-gray-700">
              Alterar status
            </h4>
            <Select
              options={statusOptions}
              value={status}
              onChange={handleStatusChange}
              className="w-48"
            />
          </div>
        </div>
      </ModalContent>

      <ModalFooter>
        <Button variant="outline" onClick={onClose}>
          <X className="mr-2 h-4 w-4" />
          Fechar
        </Button>
        <Button
          variant="outline"
          onClick={() => onCreateTask?.(publication)}
        >
          <CheckCircle className="mr-2 h-4 w-4" />
          Criar tarefa
        </Button>
        <Button onClick={() => handleStatusChange('handled')}>
          Marcar como tratada
        </Button>
      </ModalFooter>
    </Modal>
  )
}
