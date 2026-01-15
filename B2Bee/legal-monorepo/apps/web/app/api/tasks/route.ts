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

// GET /api/tasks - List all tasks
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
    const caseId = searchParams.get('caseId')
    const assigneeId = searchParams.get('assigneeId')
    const dueSoon = searchParams.get('dueSoon') === 'true'
    const page = parseInt(searchParams.get('page') || '1')
    const limit = parseInt(searchParams.get('limit') || '20')

    const where: Record<string, unknown> = { tenantId }

    if (status && status !== 'all') {
      where.status = status
    }

    if (caseId) {
      where.caseId = caseId
    }

    if (assigneeId) {
      where.assignedToId = assigneeId
    }

    if (dueSoon) {
      const nextWeek = new Date()
      nextWeek.setDate(nextWeek.getDate() + 7)
      where.dueDate = {
        lte: nextWeek,
        gte: new Date(),
      }
      where.status = { not: 'completed' }
    }

    const [tasks, total] = await Promise.all([
      prisma.task.findMany({
        where,
        include: {
          case: {
            select: {
              id: true,
              cnjNumber: true,
              title: true,
            },
          },
          assignedTo: {
            select: {
              id: true,
              name: true,
            },
          },
          createdBy: {
            select: {
              id: true,
              name: true,
            },
          },
        },
        orderBy: [{ dueDate: 'asc' }, { priority: 'desc' }],
        skip: (page - 1) * limit,
        take: limit,
      }),
      prisma.task.count({ where }),
    ])

    const transformed = tasks.map((t) => ({
      id: t.id,
      title: t.title,
      description: t.description,
      status: t.status,
      priority: t.priority,
      dueDate: t.dueDate,
      completedAt: t.completedAt,
      case: t.case
        ? {
            id: t.case.id,
            cnjNumber: t.case.cnjNumber,
            title: t.case.title,
          }
        : null,
      assignedTo: t.assignedTo
        ? {
            id: t.assignedTo.id,
            name: t.assignedTo.name,
          }
        : null,
      createdBy: t.createdBy
        ? {
            id: t.createdBy.id,
            name: t.createdBy.name,
          }
        : null,
    }))

    // Get counts by status
    const [pendingCount, inProgressCount, completedCount] = await Promise.all([
      prisma.task.count({ where: { tenantId, status: 'pending' } }),
      prisma.task.count({ where: { tenantId, status: 'in_progress' } }),
      prisma.task.count({ where: { tenantId, status: 'completed' } }),
    ])

    return NextResponse.json({
      tasks: transformed,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
      },
      counts: {
        pending: pendingCount,
        in_progress: inProgressCount,
        completed: completedCount,
        total,
      },
    })
  } catch (error) {
    console.error('Error fetching tasks:', error)
    return NextResponse.json(
      { error: 'Failed to fetch tasks' },
      { status: 500 }
    )
  }
}

// POST /api/tasks - Create a new task
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

    // Get the user's database ID
    const dbUser = await prisma.user.findUnique({
      where: { firebaseUid: user.uid },
    })

    const body = await request.json()

    if (!body.title) {
      return NextResponse.json(
        { error: 'Title is required' },
        { status: 400 }
      )
    }

    const task = await prisma.task.create({
      data: {
        tenantId,
        title: body.title,
        description: body.description || null,
        status: body.status || 'pending',
        priority: body.priority || 'medium',
        dueDate: body.dueDate ? new Date(body.dueDate) : null,
        caseId: body.caseId || null,
        assignedToId: body.assignedToId || null,
        createdById: dbUser?.id || null,
      },
      include: {
        case: {
          select: { id: true, cnjNumber: true, title: true },
        },
        assignedTo: {
          select: { id: true, name: true },
        },
      },
    })

    return NextResponse.json({ task }, { status: 201 })
  } catch (error) {
    console.error('Error creating task:', error)
    return NextResponse.json(
      { error: 'Failed to create task' },
      { status: 500 }
    )
  }
}
