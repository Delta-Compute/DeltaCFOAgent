import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { adminAuth } from '@/lib/firebase-admin'

// Force dynamic rendering to avoid build-time Firebase initialization
export const dynamic = 'force-dynamic'

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

// GET /api/publications/[id] - Get a single publication
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

    const publication = await prisma.publication.findFirst({
      where: { id, tenantId },
      include: {
        case: {
          select: {
            id: true,
            cnjNumber: true,
            title: true,
            status: true,
            court: true,
          },
        },
      },
    })

    if (!publication) {
      return NextResponse.json({ error: 'Publication not found' }, { status: 404 })
    }

    // Mark as viewed if new
    if (publication.status === 'new') {
      await prisma.publication.update({
        where: { id },
        data: { status: 'viewed' },
      })
    }

    return NextResponse.json({
      publication: {
        ...publication,
        status: publication.status === 'new' ? 'viewed' : publication.status,
      },
    })
  } catch (error) {
    console.error('Error fetching publication:', error)
    return NextResponse.json(
      { error: 'Failed to fetch publication' },
      { status: 500 }
    )
  }
}

// PUT /api/publications/[id] - Update a publication (status, link to case, etc.)
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

    const existing = await prisma.publication.findFirst({
      where: { id, tenantId },
    })

    if (!existing) {
      return NextResponse.json({ error: 'Publication not found' }, { status: 404 })
    }

    const updated = await prisma.publication.update({
      where: { id },
      data: {
        status: body.status ?? existing.status,
        caseId: body.caseId ?? existing.caseId,
        deadline: body.deadline ? new Date(body.deadline) : existing.deadline,
      },
    })

    return NextResponse.json({ publication: updated })
  } catch (error) {
    console.error('Error updating publication:', error)
    return NextResponse.json(
      { error: 'Failed to update publication' },
      { status: 500 }
    )
  }
}

// DELETE /api/publications/[id] - Delete a publication
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

    const existing = await prisma.publication.findFirst({
      where: { id, tenantId },
    })

    if (!existing) {
      return NextResponse.json({ error: 'Publication not found' }, { status: 404 })
    }

    await prisma.publication.delete({ where: { id } })

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error deleting publication:', error)
    return NextResponse.json(
      { error: 'Failed to delete publication' },
      { status: 500 }
    )
  }
}
