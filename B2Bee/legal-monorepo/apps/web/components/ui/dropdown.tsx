'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

interface DropdownContextValue {
  isOpen: boolean
  setIsOpen: (open: boolean) => void
}

const DropdownContext = React.createContext<DropdownContextValue | undefined>(undefined)

const useDropdown = () => {
  const context = React.useContext(DropdownContext)
  if (!context) {
    throw new Error('Dropdown components must be used within a Dropdown provider')
  }
  return context
}

interface DropdownProps {
  children: React.ReactNode
}

const Dropdown = ({ children }: DropdownProps) => {
  const [isOpen, setIsOpen] = React.useState(false)

  React.useEffect(() => {
    const handleClickOutside = () => setIsOpen(false)
    if (isOpen) {
      document.addEventListener('click', handleClickOutside)
    }
    return () => document.removeEventListener('click', handleClickOutside)
  }, [isOpen])

  return (
    <DropdownContext.Provider value={{ isOpen, setIsOpen }}>
      <div className="relative inline-block text-left">{children}</div>
    </DropdownContext.Provider>
  )
}

interface DropdownTriggerProps {
  children: React.ReactNode
  className?: string
}

const DropdownTrigger = ({ children, className }: DropdownTriggerProps) => {
  const { isOpen, setIsOpen } = useDropdown()

  return (
    <div
      onClick={(e) => {
        e.stopPropagation()
        setIsOpen(!isOpen)
      }}
      className={cn('cursor-pointer', className)}
    >
      {children}
    </div>
  )
}

interface DropdownContentProps {
  children: React.ReactNode
  align?: 'left' | 'right'
  className?: string
}

const DropdownContent = ({ children, align = 'right', className }: DropdownContentProps) => {
  const { isOpen } = useDropdown()

  if (!isOpen) return null

  return (
    <div
      className={cn(
        'absolute z-50 mt-2 min-w-[200px] rounded-lg border border-gray-200 bg-white py-1 shadow-lg',
        'animate-in fade-in-0 zoom-in-95',
        align === 'right' ? 'right-0' : 'left-0',
        className
      )}
      onClick={(e) => e.stopPropagation()}
    >
      {children}
    </div>
  )
}

interface DropdownItemProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  destructive?: boolean
}

const DropdownItem = React.forwardRef<HTMLButtonElement, DropdownItemProps>(
  ({ className, destructive, ...props }, ref) => {
    const { setIsOpen } = useDropdown()

    return (
      <button
        ref={ref}
        className={cn(
          'flex w-full items-center gap-2 px-4 py-2 text-left text-sm transition-colors',
          'focus:bg-gray-100 focus:outline-none',
          destructive
            ? 'text-red-600 hover:bg-red-50'
            : 'text-gray-700 hover:bg-gray-100',
          className
        )}
        onClick={(e) => {
          props.onClick?.(e)
          setIsOpen(false)
        }}
        {...props}
      />
    )
  }
)
DropdownItem.displayName = 'DropdownItem'

const DropdownSeparator = ({ className }: { className?: string }) => (
  <div className={cn('my-1 h-px bg-gray-200', className)} />
)

const DropdownLabel = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn('px-4 py-1.5 text-xs font-medium text-gray-500', className)}
    {...props}
  />
)

export {
  Dropdown,
  DropdownTrigger,
  DropdownContent,
  DropdownItem,
  DropdownSeparator,
  DropdownLabel,
}
