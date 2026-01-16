import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { adminAuth } from '@/lib/firebase-admin'

// Force dynamic rendering to avoid build-time Firebase initialization
export const dynamic = 'force-dynamic'

// Helper to get user from authorization header
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

// Helper to get tenant ID
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

// GET /api/cases/[id] - Get a single case with all related data
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

    const caseData = await prisma.case.findFirst({
      where: { id, tenantId },
      include: {
        parties: {
          include: { contact: true },
          orderBy: { createdAt: 'asc' },
        },
        movements: {
          orderBy: { date: 'desc' },
        },
        tasks: {
          include: { assignedTo: true },
          orderBy: { dueDate: 'asc' },
        },
        documents: {
          orderBy: { createdAt: 'desc' },
        },
        financialEntries: {
          orderBy: { date: 'desc' },
        },
      },
    })

    if (!caseData) {
      return NextResponse.json({ error: 'Case not found' }, { status: 404 })
    }

    // Transform data for frontend
    const transformed = {
      id: caseData.id,
      cnjNumber: caseData.cnjNumber,
      title: caseData.title,
      status: caseData.status,
      areaOfLaw: caseData.areaOfLaw,
      court: caseData.court,
      courtUnit: caseData.courtUnit,
      judge: caseData.judge,
      distributionDate: caseData.distributionDate,
      value: caseData.value?.toNumber() || 0,
      notes: caseData.notes,
      parties: caseData.parties.map((p) => ({
        id: p.id,
        name: p.contact?.name || 'Unknown',
        role: p.role,
        type: p.contact?.type,
        document: p.contact?.document,
        email: p.contact?.email,
        phone: p.contact?.phone,
      })),
      movements: caseData.movements.map((m) => ({
        id: m.id,
        date: m.date,
        description: m.description,
      })),
      tasks: caseData.tasks.map((t) => ({
        id: t.id,
        title: t.title,
        dueDate: t.dueDate,
        status: t.status,
        assignee: t.assignedTo?.name || null,
      })),
      documents: caseData.documents.map((d) => ({
        id: d.id,
        name: d.name,
        date: d.createdAt,
        type: d.fileType,
        url: d.fileUrl,
      })),
      financials: caseData.financialEntries.map((f) => ({
        id: f.id,
        description: f.description,
        value: f.amount.toNumber() * (f.type === 'expense' ? -1 : 1),
        date: f.date,
        type: f.type,
      })),
    }

    return NextResponse.json({ case: transformed })
  } catch (error) {
    console.error('Error fetching case:', error)
    return NextResponse.json(
      { error: 'Failed to fetch case' },
      { status: 500 }
    )
  }
}

// PUT /api/cases/[id] - Update a case
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

    // Verify case exists and belongs to tenant
    const existing = await prisma.case.findFirst({
      where: { id, tenantId },
    })

    if (!existing) {
      return NextResponse.json({ error: 'Case not found' }, { status: 404 })
    }

    // Update the case
    const updated = await prisma.case.update({
      where: { id },
      data: {
        cnjNumber: body.cnjNumber ?? existing.cnjNumber,
        title: body.title ?? existing.title,
        court: body.court ?? existing.court,
        courtUnit: body.courtUnit ?? existing.courtUnit,
        areaOfLaw: body.areaOfLaw ?? existing.areaOfLaw,
        status: body.status ?? existing.status,
        value: body.value !== undefined ? parseFloat(body.value) : existing.value,
        judge: body.judge ?? existing.judge,
        distributionDate: body.distributionDate
          ? new Date(body.distributionDate)
          : existing.distributionDate,
        notes: body.notes ?? existing.notes,
      },
    })

    return NextResponse.json({ case: updated })
  } catch (error) {
    console.error('Error updating case:', error)
    return NextResponse.json(
      { error: 'Failed to update case' },
      { status: 500 }
    )
  }
}

// DELETE /api/cases/[id] - Delete (archive) a case
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

    // Verify case exists and belongs to tenant
    const existing = await prisma.case.findFirst({
      where: { id, tenantId },
    })

    if (!existing) {
      return NextResponse.json({ error: 'Case not found' }, { status: 404 })
    }

    // Soft delete by setting status to archived
    await prisma.case.update({
      where: { id },
      data: { status: 'archived' },
    })

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error deleting case:', error)
    return NextResponse.json(
      { error: 'Failed to delete case' },
      { status: 500 }
    )
  }
}
