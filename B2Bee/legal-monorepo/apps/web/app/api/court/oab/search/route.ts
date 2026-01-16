import { NextRequest, NextResponse } from 'next/server'
import { courtService } from '@/lib/services/court-integration'
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

/**
 * POST /api/court/oab/search
 * Search for cases by OAB number
 *
 * Body:
 * {
 *   lawyerName: string  // Lawyer's full name
 *   oabNumber: string   // OAB registration number
 *   oabState: string    // State abbreviation (SP, RJ, etc.)
 * }
 */
export async function POST(request: NextRequest) {
  try {
    const user = await getAuthUser(request)
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { lawyerName, oabNumber, oabState } = body

    if (!oabNumber || !oabState) {
      return NextResponse.json(
        { error: 'OAB number and state are required' },
        { status: 400 }
      )
    }

    // Check if APIs are configured
    const config = courtService.isConfigured()
    if (!config.digesto && !config.jusbrasil) {
      return NextResponse.json(
        { error: 'Court APIs not configured. Please contact support.' },
        { status: 503 }
      )
    }

    // Search for cases
    const result = await courtService.searchCasesByOAB(
      lawyerName || '',
      oabNumber,
      oabState
    )

    if (!result.success) {
      return NextResponse.json(
        { error: result.error || 'Failed to search cases' },
        { status: 500 }
      )
    }

    return NextResponse.json({
      success: true,
      lawyer: result.lawyer,
      cases: result.cases,
      total: result.total,
    })
  } catch (error) {
    console.error('Error searching OAB cases:', error)
    return NextResponse.json(
      { error: 'Failed to search cases' },
      { status: 500 }
    )
  }
}

/**
 * GET /api/court/oab/search
 * Check API configuration status
 */
export async function GET(request: NextRequest) {
  try {
    const user = await getAuthUser(request)
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const config = courtService.isConfigured()

    return NextResponse.json({
      configured: config.digesto || config.jusbrasil,
      providers: {
        digesto: config.digesto,
        jusbrasil: config.jusbrasil,
      },
    })
  } catch (error) {
    console.error('Error checking court API config:', error)
    return NextResponse.json(
      { error: 'Failed to check configuration' },
      { status: 500 }
    )
  }
}
