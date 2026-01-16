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

// GET /api/cases - List all cases for the tenant
export async function GET(request: NextRequest) {
  try {
    const user = await getAuthUser(request)
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // Get user's tenant
    const dbUser = await prisma.user.findUnique({
      where: { firebaseUid: user.uid },
      include: { tenantUsers: true },
    })

    if (!dbUser || dbUser.tenantUsers.length === 0) {
      return NextResponse.json({ error: 'No tenant found' }, { status: 404 })
    }

    const tenantId = dbUser.tenantUsers[0].tenantId

    // Parse query params
    const { searchParams } = new URL(request.url)
    const status = searchParams.get('status')
    const areaOfLaw = searchParams.get('areaOfLaw')
    const search = searchParams.get('search')
    const page = parseInt(searchParams.get('page') || '1')
    const limit = parseInt(searchParams.get('limit') || '20')

    // Build where clause
    const where: Record<string, unknown> = { tenantId }

    if (status && status !== 'all') {
      where.status = status
    }

    if (areaOfLaw && areaOfLaw !== 'all') {
      where.areaOfLaw = areaOfLaw
    }

    if (search) {
      where.OR = [
        { cnjNumber: { contains: search } },
        { title: { contains: search, mode: 'insensitive' } },
      ]
    }

    // Get cases with pagination
    const [cases, total] = await Promise.all([
      prisma.case.findMany({
        where,
        include: {
          parties: {
            where: { role: 'client' },
            include: { contact: true },
            take: 1,
          },
          movements: {
            orderBy: { date: 'desc' },
            take: 1,
          },
        },
        orderBy: { updatedAt: 'desc' },
        skip: (page - 1) * limit,
        take: limit,
      }),
      prisma.case.count({ where }),
    ])

    // Transform data for frontend
    const transformedCases = cases.map((c) => ({
      id: c.id,
      cnjNumber: c.cnjNumber,
      title: c.title,
      client: c.parties[0]?.contact?.name || 'Sem cliente',
      court: c.court,
      courtUnit: c.courtUnit,
      areaOfLaw: c.areaOfLaw,
      status: c.status,
      value: c.value?.toNumber() || 0,
      lastMovementAt: c.movements[0]?.date || c.updatedAt,
    }))

    return NextResponse.json({
      cases: transformedCases,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
      },
    })
  } catch (error) {
    console.error('Error fetching cases:', error)
    return NextResponse.json(
      { error: 'Failed to fetch cases' },
      { status: 500 }
    )
  }
}

// POST /api/cases - Create a new case
export async function POST(request: NextRequest) {
  try {
    const user = await getAuthUser(request)
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // Get user's tenant
    const dbUser = await prisma.user.findUnique({
      where: { firebaseUid: user.uid },
      include: { tenantUsers: true },
    })

    if (!dbUser || dbUser.tenantUsers.length === 0) {
      return NextResponse.json({ error: 'No tenant found' }, { status: 404 })
    }

    const tenantId = dbUser.tenantUsers[0].tenantId

    const body = await request.json()

    // Validate required fields
    if (!body.cnjNumber || !body.title) {
      return NextResponse.json(
        { error: 'CNJ number and title are required' },
        { status: 400 }
      )
    }

    // Check for duplicate CNJ number
    const existing = await prisma.case.findFirst({
      where: { tenantId, cnjNumber: body.cnjNumber },
    })

    if (existing) {
      return NextResponse.json(
        { error: 'Case with this CNJ number already exists' },
        { status: 409 }
      )
    }

    // Create the case
    const newCase = await prisma.case.create({
      data: {
        tenantId,
        cnjNumber: body.cnjNumber,
        title: body.title,
        court: body.court || null,
        courtUnit: body.courtUnit || null,
        areaOfLaw: body.areaOfLaw || null,
        status: body.status || 'active',
        value: body.value ? parseFloat(body.value) : null,
        judge: body.judge || null,
        distributionDate: body.distributionDate ? new Date(body.distributionDate) : null,
        notes: body.notes || null,
      },
    })

    return NextResponse.json({ case: newCase }, { status: 201 })
  } catch (error) {
    console.error('Error creating case:', error)
    return NextResponse.json(
      { error: 'Failed to create case' },
      { status: 500 }
    )
  }
}
