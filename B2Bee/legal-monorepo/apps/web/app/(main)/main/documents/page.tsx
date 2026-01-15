'use client'

import * as React from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { EmptyState } from '@/components/ui/empty-state'
import { ptBR } from '@/lib/i18n'
import { formatDateBR } from '@/lib/utils'
import {
  Upload,
  Search,
  FolderPlus,
  FileText,
  FileImage,
  File,
  MoreVertical,
  Download,
  Eye,
  Folder,
} from 'lucide-react'
import {
  Dropdown,
  DropdownTrigger,
  DropdownContent,
  DropdownItem,
} from '@/components/ui/dropdown'

// Mock data
const mockFolders = [
  { id: '1', name: 'Contratos', count: 12 },
  { id: '2', name: 'Procuracoes', count: 8 },
  { id: '3', name: 'Peticoes', count: 24 },
]

const mockDocuments = [
  {
    id: '1',
    name: 'Contrato de honorarios - Maria Silva.pdf',
    type: 'pdf',
    size: 256000,
    folder: 'Contratos',
    caseNumber: '1234567-89.2024.8.26.0100',
    createdAt: new Date('2026-01-10'),
  },
  {
    id: '2',
    name: 'Procuracao ad judicia.pdf',
    type: 'pdf',
    size: 128000,
    folder: 'Procuracoes',
    caseNumber: '1234567-89.2024.8.26.0100',
    createdAt: new Date('2026-01-08'),
  },
  {
    id: '3',
    name: 'Comprovante de residencia.jpg',
    type: 'image',
    size: 512000,
    folder: null,
    caseNumber: '9876543-21.2024.8.26.0100',
    createdAt: new Date('2026-01-12'),
  },
]

export default function DocumentsPage() {
  const t = ptBR
  const [searchTerm, setSearchTerm] = React.useState('')
  const [currentFolder, setCurrentFolder] = React.useState<string | null>(null)

  const filteredDocuments = mockDocuments.filter((doc) => {
    const matchesSearch = doc.name.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesFolder = currentFolder === null || doc.folder === currentFolder
    return matchesSearch && matchesFolder
  })

  const getFileIcon = (type: string) => {
    switch (type) {
      case 'pdf':
        return <FileText className="h-10 w-10 text-red-500" />
      case 'image':
        return <FileImage className="h-10 w-10 text-blue-500" />
      default:
        return <File className="h-10 w-10 text-gray-500" />
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t.documents.title}</h1>
          <p className="mt-1 text-gray-500">
            Gerencie seus arquivos e documentos
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <FolderPlus className="mr-2 h-4 w-4" />
            {t.documents.newFolder}
          </Button>
          <Button>
            <Upload className="mr-2 h-4 w-4" />
            {t.documents.upload}
          </Button>
        </div>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="pt-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input
              placeholder="Pesquisar documentos..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9"
            />
          </div>
        </CardContent>
      </Card>

      {/* Breadcrumb */}
      {currentFolder && (
        <div className="flex items-center gap-2 text-sm">
          <button
            onClick={() => setCurrentFolder(null)}
            className="text-primary-600 hover:underline"
          >
            Todos os documentos
          </button>
          <span className="text-gray-400">/</span>
          <span className="text-gray-600">{currentFolder}</span>
        </div>
      )}

      {/* Folders */}
      {!currentFolder && (
        <div>
          <h2 className="mb-3 text-sm font-medium text-gray-700">Pastas</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {mockFolders.map((folder) => (
              <Card
                key={folder.id}
                className="cursor-pointer transition-shadow hover:shadow-md"
                onClick={() => setCurrentFolder(folder.name)}
              >
                <CardContent className="flex items-center gap-3 p-4">
                  <Folder className="h-10 w-10 text-yellow-500" />
                  <div>
                    <p className="font-medium text-gray-900">{folder.name}</p>
                    <p className="text-sm text-gray-500">{folder.count} arquivos</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Documents Grid */}
      <div>
        <h2 className="mb-3 text-sm font-medium text-gray-700">
          {currentFolder ? `Arquivos em ${currentFolder}` : 'Arquivos recentes'}
        </h2>
        {filteredDocuments.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {filteredDocuments.map((doc) => (
              <Card key={doc.id} className="group relative">
                <CardContent className="p-4">
                  <div className="absolute right-2 top-2 opacity-0 transition-opacity group-hover:opacity-100">
                    <Dropdown>
                      <DropdownTrigger>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownTrigger>
                      <DropdownContent>
                        <DropdownItem>
                          <Eye className="h-4 w-4" />
                          Visualizar
                        </DropdownItem>
                        <DropdownItem>
                          <Download className="h-4 w-4" />
                          Baixar
                        </DropdownItem>
                        <DropdownItem>Mover para pasta</DropdownItem>
                        <DropdownItem destructive>Excluir</DropdownItem>
                      </DropdownContent>
                    </Dropdown>
                  </div>

                  <div className="flex flex-col items-center text-center">
                    {getFileIcon(doc.type)}
                    <p className="mt-3 line-clamp-2 text-sm font-medium text-gray-900">
                      {doc.name}
                    </p>
                    <p className="mt-1 text-xs text-gray-500">
                      {formatFileSize(doc.size)}
                    </p>
                    {doc.caseNumber && (
                      <Badge variant="outline" className="mt-2 text-xs">
                        {doc.caseNumber.slice(0, 15)}...
                      </Badge>
                    )}
                    <p className="mt-2 text-xs text-gray-400">
                      {formatDateBR(doc.createdAt)}
                    </p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <EmptyState
            icon="documents"
            title={t.documents.emptyState.title}
            description={t.documents.emptyState.description}
            actionLabel={t.documents.upload}
            onAction={() => console.log('Upload')}
          />
        )}
      </div>
    </div>
  )
}
