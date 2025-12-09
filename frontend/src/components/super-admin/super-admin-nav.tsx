'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  Users,
  Building2,
  Layers,
  AlertCircle,
  Server,
  Shield,
  LogOut,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

const navItems = [
  {
    label: 'Overview',
    href: '/super-admin',
    icon: LayoutDashboard,
  },
  {
    label: 'Users',
    href: '/super-admin/users',
    icon: Users,
  },
  {
    label: 'Tenants',
    href: '/super-admin/tenants',
    icon: Building2,
  },
  {
    label: 'Features',
    href: '/super-admin/features',
    icon: Layers,
  },
  {
    label: 'Errors',
    href: '/super-admin/errors',
    icon: AlertCircle,
  },
  {
    label: 'System',
    href: '/super-admin/system',
    icon: Server,
  },
];

export function SuperAdminNav() {
  const pathname = usePathname();

  return (
    <nav className="sticky top-0 z-50 bg-zinc-900 text-white">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Logo and Badge */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <Shield className="h-6 w-6 text-amber-400" />
              <span className="text-lg font-semibold">Super Admin</span>
            </div>
            <span className="rounded-full bg-amber-500/20 px-2 py-0.5 text-xs font-medium text-amber-400">
              Internal Only
            </span>
          </div>

          {/* Navigation Links */}
          <div className="hidden md:flex md:items-center md:gap-1">
            {navItems.map((item) => {
              const isActive =
                pathname === item.href ||
                (item.href !== '/super-admin' && pathname.startsWith(item.href));

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    'flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-zinc-800 text-white'
                      : 'text-zinc-400 hover:bg-zinc-800 hover:text-white'
                  )}
                >
                  <item.icon className="h-4 w-4" />
                  {item.label}
                </Link>
              );
            })}
          </div>

          {/* Exit to Dashboard */}
          <div className="flex items-center gap-2">
            <Link href="/dashboard">
              <Button
                variant="ghost"
                size="sm"
                className="text-zinc-400 hover:bg-zinc-800 hover:text-white"
              >
                <LogOut className="mr-2 h-4 w-4" />
                Exit to Dashboard
              </Button>
            </Link>
          </div>
        </div>

        {/* Mobile Navigation */}
        <div className="flex gap-1 overflow-x-auto pb-2 md:hidden">
          {navItems.map((item) => {
            const isActive =
              pathname === item.href ||
              (item.href !== '/super-admin' && pathname.startsWith(item.href));

            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'flex shrink-0 items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                  isActive
                    ? 'bg-zinc-800 text-white'
                    : 'text-zinc-400 hover:bg-zinc-800 hover:text-white'
                )}
              >
                <item.icon className="h-3.5 w-3.5" />
                {item.label}
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
