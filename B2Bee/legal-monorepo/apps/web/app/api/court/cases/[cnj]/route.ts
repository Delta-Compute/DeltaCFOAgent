import { NextRequest, NextResponse } from 'next/server'
import { courtService } from '@/lib/services/court-integration'
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

/**
 * GET /api/court/cases/[cnj]
 * Get detailed information about a specific case by CNJ number
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ cnj: string }> }
) {
  try {
    const user = await getAuthUser(request)
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { cnj } = await params

    if (!cnj) {
      return NextResponse.json(
        { error: 'CNJ number is required' },
        { status: 400 }
      )
    }

    // Decode the CNJ number (may be URL encoded)
    const decodedCnj = decodeURIComponent(cnj)

    const caseDetails = await courtService.getCaseDetails(decodedCnj)

    if (!caseDetails) {
      return NextResponse.json(
        { error: 'Case not found' },
        { status: 404 }
      )
    }

    return NextResponse.json({
      success: true,
      case: caseDetails,
    })
  } catch (error) {
    console.error('Error fetching case details:', error)
    return NextResponse.json(
      { error: 'Failed to fetch case details' },
      { status: 500 }
    )
  }
}
