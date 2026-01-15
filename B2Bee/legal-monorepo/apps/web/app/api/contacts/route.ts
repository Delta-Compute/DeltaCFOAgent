import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { adminAuth } from '@/lib/firebase-admin'

async function getAuthUser(request: NextRequest) {
  const authHeader = request.headers.get('Authorization')
  if (!authHeader?.startsWith('Bearer ')) {
    return null
  }

  const token = authHeader.split('Bearer ')[1]
  try {
    const decodedToken = await adminAuth.verifyIdToken(token)
    return decodedToken
  } catch {
    return null
  }
}

async function getTenantId(firebaseUid: string) {
  const dbUser = await prisma.user.findUnique({
    where: { firebaseUid },
    include: { tenantUsers: true },
  })

  if (!dbUser || dbUser.tenantUsers.length === 0) {
    return null
  }

  return dbUser.tenantUsers[0].tenantId
}

// GET /api/contacts - List all contacts
export async function GET(request: NextRequest) {
  try {
    const user = await getAuthUser(request)
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const tenantId = await getTenantId(user.uid)
    if (!tenantId) {
      return NextResponse.json({ error: 'No tenant found' }, { status: 404 })
    }

    const { searchParams } = new URL(request.url)
    const type = searchParams.get('type')
    const search = searchParams.get('search')
    const page = parseInt(searchParams.get('page') || '1')
    const limit = parseInt(searchParams.get('limit') || '20')

    const where: Record<string, unknown> = { tenantId }

    if (type && type !== 'all') {
      where.type = type
    }

    if (search) {
      where.OR = [
        { name: { contains: search, mode: 'insensitive' } },
        { email: { contains: search, mode: 'insensitive' } },
        { document: { contains: search } },
      ]
    }

    const [contacts, total] = await Promise.all([
      prisma.contact.findMany({
        where,
        include: {
          caseParties: {
            include: { case: true },
            take: 3,
          },
          _count: {
            select: { caseParties: true },
          },
        },
        orderBy: { name: 'asc' },
        skip: (page - 1) * limit,
        take: limit,
      }),
      prisma.contact.count({ where }),
    ])

    const transformedContacts = contacts.map((c) => ({
      id: c.id,
      name: c.name,
      type: c.type,
      document: c.document,
      email: c.email,
      phone: c.phone,
      address: c.address,
      casesCount: c._count.caseParties,
      recentCases: c.caseParties.map((cp) => ({
        id: cp.case.id,
        title: cp.case.title,
        cnjNumber: cp.case.cnjNumber,
      })),
    }))

    return NextResponse.json({
      contacts: transformedContacts,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
      },
    })
  } catch (error) {
    console.error('Error fetching contacts:', error)
    return NextResponse.json(
      { error: 'Failed to fetch contacts' },
      { status: 500 }
    )
  }
}

// POST /api/contacts - Create a new contact
export async function POST(request: NextRequest) {
  try {
    const user = await getAuthUser(request)
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const tenantId = await getTenantId(user.uid)
    if (!tenantId) {
      return NextResponse.json({ error: 'No tenant found' }, { status: 404 })
    }

    const body = await request.json()

    if (!body.name) {
      return NextResponse.json(
        { error: 'Name is required' },
        { status: 400 }
      )
    }

    // Check for duplicate document if provided
    if (body.document) {
      const existing = await prisma.contact.findFirst({
        where: { tenantId, document: body.document },
      })

      if (existing) {
        return NextResponse.json(
          { error: 'Contact with this document already exists' },
          { status: 409 }
        )
      }
    }

    const contact = await prisma.contact.create({
      data: {
        tenantId,
        name: body.name,
        type: body.type || 'client',
        document: body.document || null,
        email: body.email || null,
        phone: body.phone || null,
        address: body.address || null,
        notes: body.notes || null,
      },
    })

    return NextResponse.json({ contact }, { status: 201 })
  } catch (error) {
    console.error('Error creating contact:', error)
    return NextResponse.json(
      { error: 'Failed to create contact' },
      { status: 500 }
    )
  }
}
