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

// GET /api/contacts/[id] - Get a single contact with related data
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const user = await getAuthUser(request)
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const tenantId = await getTenantId(user.uid)
    if (!tenantId) {
      return NextResponse.json({ error: 'No tenant found' }, { status: 404 })
    }

    const { id } = await params

    const contact = await prisma.contact.findFirst({
      where: { id, tenantId },
      include: {
        caseParties: {
          include: {
            case: {
              select: {
                id: true,
                cnjNumber: true,
                title: true,
                status: true,
                areaOfLaw: true,
              },
            },
          },
        },
        clientServices: {
          orderBy: { date: 'desc' },
          take: 10,
        },
      },
    })

    if (!contact) {
      return NextResponse.json({ error: 'Contact not found' }, { status: 404 })
    }

    const transformed = {
      id: contact.id,
      name: contact.name,
      type: contact.type,
      document: contact.document,
      email: contact.email,
      phone: contact.phone,
      address: contact.address,
      notes: contact.notes,
      createdAt: contact.createdAt,
      cases: contact.caseParties.map((cp) => ({
        id: cp.case.id,
        cnjNumber: cp.case.cnjNumber,
        title: cp.case.title,
        status: cp.case.status,
        areaOfLaw: cp.case.areaOfLaw,
        role: cp.role,
      })),
      services: contact.clientServices.map((s) => ({
        id: s.id,
        title: s.title,
        type: s.type,
        date: s.date,
        duration: s.duration,
        status: s.status,
      })),
    }

    return NextResponse.json({ contact: transformed })
  } catch (error) {
    console.error('Error fetching contact:', error)
    return NextResponse.json(
      { error: 'Failed to fetch contact' },
      { status: 500 }
    )
  }
}

// PUT /api/contacts/[id] - Update a contact
export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const user = await getAuthUser(request)
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const tenantId = await getTenantId(user.uid)
    if (!tenantId) {
      return NextResponse.json({ error: 'No tenant found' }, { status: 404 })
    }

    const { id } = await params
    const body = await request.json()

    const existing = await prisma.contact.findFirst({
      where: { id, tenantId },
    })

    if (!existing) {
      return NextResponse.json({ error: 'Contact not found' }, { status: 404 })
    }

    // Check for duplicate document if changing
    if (body.document && body.document !== existing.document) {
      const duplicate = await prisma.contact.findFirst({
        where: { tenantId, document: body.document, NOT: { id } },
      })

      if (duplicate) {
        return NextResponse.json(
          { error: 'Another contact with this document already exists' },
          { status: 409 }
        )
      }
    }

    const updated = await prisma.contact.update({
      where: { id },
      data: {
        name: body.name ?? existing.name,
        type: body.type ?? existing.type,
        document: body.document ?? existing.document,
        email: body.email ?? existing.email,
        phone: body.phone ?? existing.phone,
        address: body.address ?? existing.address,
        notes: body.notes ?? existing.notes,
      },
    })

    return NextResponse.json({ contact: updated })
  } catch (error) {
    console.error('Error updating contact:', error)
    return NextResponse.json(
      { error: 'Failed to update contact' },
      { status: 500 }
    )
  }
}

// DELETE /api/contacts/[id] - Delete a contact
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const user = await getAuthUser(request)
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const tenantId = await getTenantId(user.uid)
    if (!tenantId) {
      return NextResponse.json({ error: 'No tenant found' }, { status: 404 })
    }

    const { id } = await params

    const existing = await prisma.contact.findFirst({
      where: { id, tenantId },
      include: { _count: { select: { caseParties: true } } },
    })

    if (!existing) {
      return NextResponse.json({ error: 'Contact not found' }, { status: 404 })
    }

    // Prevent deletion if contact is linked to cases
    if (existing._count.caseParties > 0) {
      return NextResponse.json(
        { error: 'Cannot delete contact that is linked to cases' },
        { status: 400 }
      )
    }

    await prisma.contact.delete({ where: { id } })

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error deleting contact:', error)
    return NextResponse.json(
      { error: 'Failed to delete contact' },
      { status: 500 }
    )
  }
}
