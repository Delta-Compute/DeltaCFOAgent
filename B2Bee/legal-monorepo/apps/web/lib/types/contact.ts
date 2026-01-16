export interface ContactCase {
  id: string
  cnjNumber: string
  title: string
  status: string
  role: string
}

export interface ContactService {
  id: string
  title: string
  type: string
  date: Date
  duration: number
}

// Base contact type for forms and creation
export interface ContactFormData {
  id?: string
  name: string
  type: string
  document?: string
  email?: string
  phone?: string
  address?: string
  notes?: string
  casesCount?: number
  cases?: ContactCase[]
  services?: ContactService[]
}

// Full contact type with required id (for display/list)
export interface Contact extends ContactFormData {
  id: string
  email: string
  phone: string
  casesCount: number
}
