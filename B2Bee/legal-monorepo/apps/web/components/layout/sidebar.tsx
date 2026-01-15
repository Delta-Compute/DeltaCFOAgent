'use client'

import * as React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { sidebarConfig, type NavItem } from '@/lib/sidebar-config'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Search, Menu, X } from 'lucide-react'

interface SidebarProps {
  className?: string
}

export const Sidebar = ({ className }: SidebarProps) => {
  const pathname = usePathname()
  const [isCollapsed, setIsCollapsed] = React.useState(false)
  const [isMobileOpen, setIsMobileOpen] = React.useState(false)

  return (
    <>
      {/* Mobile menu button */}
      <button
        onClick={() => setIsMobileOpen(!isMobileOpen)}
        className="fixed left-4 top-4 z-50 rounded-lg bg-white p-2 shadow-md lg:hidden"
      >
        {isMobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      {/* Mobile overlay */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed left-0 top-0 z-40 flex h-full flex-col border-r border-gray-200 bg-white transition-all duration-300',
          isCollapsed ? 'w-16' : 'w-64',
          isMobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
          className
        )}
      >
        {/* Logo */}
        <div className="flex h-16 items-center justify-between border-b border-gray-200 px-4">
          {!isCollapsed && (
            <Link href="/main/workspace" className="flex items-center gap-2">
              <span className="text-xl font-bold text-primary-600">LEGAL AI</span>
            </Link>
          )}
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="hidden rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 lg:block"
          >
            <Menu className="h-5 w-5" />
          </button>
        </div>

        {/* Search */}
        {!isCollapsed && (
          <div className="p-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <Input
                placeholder="Pesquisar contato, processo ou tarefa"
                className="h-9 pl-9 text-sm"
              />
            </div>
          </div>
        )}

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-2 py-2">
          {sidebarConfig.map((section, sectionIndex) => (
            <div key={sectionIndex}>
              {sectionIndex > 0 && (
                <div className="my-4 h-px bg-gray-200" />
              )}
              <ul className="space-y-1">
                {section.items.map((item) => (
                  <SidebarItem
                    key={item.href}
                    item={item}
                    isActive={pathname === item.href || pathname.startsWith(item.href + '/')}
                    isCollapsed={isCollapsed}
                  />
                ))}
              </ul>
            </div>
          ))}
        </nav>

        {/* Upgrade CTA */}
        {!isCollapsed && (
          <div className="border-t border-gray-200 p-4">
            <Button className="w-full" size="sm">
              CONTRATAR
            </Button>
          </div>
        )}
      </aside>
    </>
  )
}

interface SidebarItemProps {
  item: NavItem
  isActive: boolean
  isCollapsed: boolean
}

const SidebarItem = ({ item, isActive, isCollapsed }: SidebarItemProps) => {
  const Icon = item.icon

  return (
    <li>
      <Link
        href={item.href}
        className={cn(
          'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
          isActive
            ? 'bg-primary-50 text-primary-700'
            : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900',
          isCollapsed && 'justify-center px-2'
        )}
        title={isCollapsed ? item.label : undefined}
      >
        <Icon className={cn('h-5 w-5 flex-shrink-0', isActive && 'text-primary-600')} />
        {!isCollapsed && (
          <>
            <span className="flex-1">{item.label}</span>
            {item.badge && (
              <Badge variant={item.badgeVariant === 'ai' ? 'ai' : 'default'} className="text-[10px]">
                {item.badge}
              </Badge>
            )}
          </>
        )}
      </Link>
    </li>
  )
}
