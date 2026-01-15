'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import { cn } from '@/lib/utils'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/button'
import { Avatar } from '@/components/ui/avatar'
import {
  Dropdown,
  DropdownTrigger,
  DropdownContent,
  DropdownItem,
  DropdownSeparator,
  DropdownLabel,
} from '@/components/ui/dropdown'
import {
  Plus,
  RefreshCw,
  Bell,
  MessageSquare,
  Settings,
  ChevronDown,
  User,
  LogOut,
  HelpCircle,
} from 'lucide-react'

interface HeaderProps {
  className?: string
}

export const Header = ({ className }: HeaderProps) => {
  const router = useRouter()
  const { user, signOut } = useAuth()

  const handleSignOut = async () => {
    await signOut()
    router.push('/login')
  }

  return (
    <header
      className={cn(
        'sticky top-0 z-30 flex h-16 items-center justify-between border-b border-gray-200 bg-white px-6',
        className
      )}
    >
      {/* Quick Actions */}
      <div className="flex items-center gap-2">
        <Dropdown>
          <DropdownTrigger>
            <Button variant="outline" size="icon" className="h-9 w-9">
              <Plus className="h-4 w-4" />
            </Button>
          </DropdownTrigger>
          <DropdownContent align="left">
            <DropdownLabel>Adicionar</DropdownLabel>
            <DropdownItem onClick={() => router.push('/main/cases?new=true')}>
              Novo processo
            </DropdownItem>
            <DropdownItem onClick={() => router.push('/main/contacts?new=true')}>
              Novo contato
            </DropdownItem>
            <DropdownItem onClick={() => router.push('/main/services?new=true')}>
              Novo atendimento
            </DropdownItem>
            <DropdownItem onClick={() => router.push('/main/financial/entries?new=true')}>
              Novo lancamento
            </DropdownItem>
          </DropdownContent>
        </Dropdown>

        <Button variant="ghost" size="icon" className="h-9 w-9" title="Sincronizar">
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* Right Side */}
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" className="relative h-9 w-9" title="Notificacoes">
          <Bell className="h-4 w-4" />
          <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-red-500" />
        </Button>

        <Button variant="ghost" size="icon" className="h-9 w-9" title="Mensagens">
          <MessageSquare className="h-4 w-4" />
        </Button>

        <Button variant="ghost" size="icon" className="h-9 w-9" title="Configuracoes">
          <Settings className="h-4 w-4" />
        </Button>

        <div className="ml-2 h-6 w-px bg-gray-200" />

        <Button size="sm" className="ml-2">
          CONTRATAR
        </Button>

        {/* User Menu */}
        <Dropdown>
          <DropdownTrigger>
            <button className="ml-2 flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-gray-100">
              <Avatar
                src={user?.photoURL}
                fallback={user?.displayName || user?.email || 'U'}
                size="sm"
              />
              <span className="hidden text-sm font-medium text-gray-700 md:inline-block">
                {user?.displayName || user?.email?.split('@')[0] || 'Usuario'}
              </span>
              <ChevronDown className="h-4 w-4 text-gray-400" />
            </button>
          </DropdownTrigger>
          <DropdownContent>
            <DropdownLabel>{user?.email}</DropdownLabel>
            <DropdownSeparator />
            <DropdownItem onClick={() => router.push('/main/profile')}>
              <User className="h-4 w-4" />
              Meu perfil
            </DropdownItem>
            <DropdownItem onClick={() => router.push('/main/settings')}>
              <Settings className="h-4 w-4" />
              Configuracoes
            </DropdownItem>
            <DropdownItem onClick={() => router.push('/support')}>
              <HelpCircle className="h-4 w-4" />
              Ajuda
            </DropdownItem>
            <DropdownSeparator />
            <DropdownItem onClick={handleSignOut} destructive>
              <LogOut className="h-4 w-4" />
              Sair
            </DropdownItem>
          </DropdownContent>
        </Dropdown>
      </div>
    </header>
  )
}
