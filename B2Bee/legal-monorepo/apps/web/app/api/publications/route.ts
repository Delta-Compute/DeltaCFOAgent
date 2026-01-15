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

// GET /api/publications - List all publications
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
    const status = searchParams.get('status')
    const search = searchParams.get('search')
    const page = parseInt(searchParams.get('page') || '1')
    const limit = parseInt(searchParams.get('limit') || '20')

    const where: Record<string, unknown> = { tenantId }

    if (status && status !== 'all') {
      where.status = status
    }

    if (search) {
      where.OR = [
        { caseNumber: { contains: search } },
        { content: { contains: search, mode: 'insensitive' } },
      ]
    }

    const [publications, total] = await Promise.all([
      prisma.publication.findMany({
        where,
        include: {
          case: {
            select: {
              id: true,
              cnjNumber: true,
              title: true,
            },
          },
        },
        orderBy: { publicationDate: 'desc' },
        skip: (page - 1) * limit,
        take: limit,
      }),
      prisma.publication.count({ where }),
    ])

    const transformed = publications.map((p) => ({
      id: p.id,
      caseNumber: p.caseNumber,
      source: p.source,
      publicationDate: p.publicationDate,
      content: p.content,
      status: p.status,
      deadline: p.deadline,
      case: p.case
        ? {
            id: p.case.id,
            cnjNumber: p.case.cnjNumber,
            title: p.case.title,
          }
        : null,
    }))

    // Count by status for filters
    const [newCount, viewedCount, handledCount] = await Promise.all([
      prisma.publication.count({ where: { tenantId, status: 'new' } }),
      prisma.publication.count({ where: { tenantId, status: 'viewed' } }),
      prisma.publication.count({ where: { tenantId, status: 'handled' } }),
    ])

    return NextResponse.json({
      publications: transformed,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
      },
      counts: {
        new: newCount,
        viewed: viewedCount,
        handled: handledCount,
        total,
      },
    })
  } catch (error) {
    console.error('Error fetching publications:', error)
    return NextResponse.json(
      { error: 'Failed to fetch publications' },
      { status: 500 }
    )
  }
}

// POST /api/publications - Create a new publication (for manual entry or import)
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

    if (!body.content) {
      return NextResponse.json(
        { error: 'Content is required' },
        { status: 400 }
      )
    }

    // Try to link to existing case by CNJ number
    let caseId = body.caseId
    if (!caseId && body.caseNumber) {
      const existingCase = await prisma.case.findFirst({
        where: { tenantId, cnjNumber: body.caseNumber },
      })
      if (existingCase) {
        caseId = existingCase.id
      }
    }

    const publication = await prisma.publication.create({
      data: {
        tenantId,
        caseId,
        caseNumber: body.caseNumber || null,
        source: body.source || 'manual',
        publicationDate: body.publicationDate
          ? new Date(body.publicationDate)
          : new Date(),
        content: body.content,
        status: 'new',
        deadline: body.deadline ? new Date(body.deadline) : null,
      },
    })

    return NextResponse.json({ publication }, { status: 201 })
  } catch (error) {
    console.error('Error creating publication:', error)
    return NextResponse.json(
      { error: 'Failed to create publication' },
      { status: 500 }
    )
  }
}
