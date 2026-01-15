'use client'

import { MainLayout } from '@/components/layout'
import { ToastProvider } from '@/components/ui/toast'

export default function MainAppLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ToastProvider>
      <MainLayout>{children}</MainLayout>
    </ToastProvider>
  )
}
