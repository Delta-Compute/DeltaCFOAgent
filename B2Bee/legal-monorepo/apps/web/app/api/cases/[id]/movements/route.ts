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

// GET /api/cases/[id]/movements - Get all movements for a case
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

    // Verify case exists and belongs to tenant
    const caseData = await prisma.case.findFirst({
      where: { id, tenantId },
    })

    if (!caseData) {
      return NextResponse.json({ error: 'Case not found' }, { status: 404 })
    }

    const movements = await prisma.caseMovement.findMany({
      where: { caseId: id },
      orderBy: { date: 'desc' },
    })

    return NextResponse.json({ movements })
  } catch (error) {
    console.error('Error fetching movements:', error)
    return NextResponse.json(
      { error: 'Failed to fetch movements' },
      { status: 500 }
    )
  }
}

// POST /api/cases/[id]/movements - Add a new movement
export async function POST(
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
    const caseData = await prisma.case.findFirst({
      where: { id, tenantId },
    })

    if (!caseData) {
      return NextResponse.json({ error: 'Case not found' }, { status: 404 })
    }

    // Validate required fields
    if (!body.description) {
      return NextResponse.json(
        { error: 'Description is required' },
        { status: 400 }
      )
    }

    const movement = await prisma.caseMovement.create({
      data: {
        caseId: id,
        description: body.description,
        date: body.date ? new Date(body.date) : new Date(),
        source: body.source || 'manual',
      },
    })

    // Update case's updatedAt
    await prisma.case.update({
      where: { id },
      data: { updatedAt: new Date() },
    })

    return NextResponse.json({ movement }, { status: 201 })
  } catch (error) {
    console.error('Error creating movement:', error)
    return NextResponse.json(
      { error: 'Failed to create movement' },
      { status: 500 }
    )
  }
}
