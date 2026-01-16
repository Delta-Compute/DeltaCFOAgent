import { initializeApp, getApps, cert, App } from 'firebase-admin/app'
import { getAuth, Auth } from 'firebase-admin/auth'

let app: App | undefined
let authInstance: Auth | undefined
let initializationError: Error | null = null

function getFirebaseAdmin() {
  if (initializationError) {
    throw initializationError
  }

  if (!app) {
    const apps = getApps()

    if (apps.length === 0) {
      const serviceAccountKey = process.env.FIREBASE_SERVICE_ACCOUNT_KEY

      if (serviceAccountKey) {
        try {
          const serviceAccount = JSON.parse(serviceAccountKey)
          if (!serviceAccount.project_id) {
            throw new Error('Service account is missing project_id')
          }
          app = initializeApp({
            credential: cert(serviceAccount),
          })
        } catch (error) {
          console.error('Failed to parse FIREBASE_SERVICE_ACCOUNT_KEY:', error)
          initializationError = new Error('Invalid Firebase service account configuration')
          throw initializationError
        }
      } else {
        // Fall back to Application Default Credentials (for Cloud Run)
        try {
          app = initializeApp()
        } catch (error) {
          console.error('Failed to initialize Firebase with default credentials:', error)
          initializationError = new Error('Failed to initialize Firebase Admin')
          throw initializationError
        }
      }
    } else {
      app = apps[0]
    }
  }

  if (!authInstance && app) {
    authInstance = getAuth(app)
  }

  return { app, auth: authInstance! }
}

// Lazy getter for adminAuth - only initializes when first accessed
let _adminAuth: Auth | null = null

function getAdminAuth(): Auth {
  if (!_adminAuth) {
    const { auth } = getFirebaseAdmin()
    _adminAuth = auth
  }
  return _adminAuth
}

// Export a proxy object that lazily initializes
const adminAuth = new Proxy({} as Auth, {
  get(target, prop) {
    const auth = getAdminAuth()
    const value = (auth as unknown as Record<string | symbol, unknown>)[prop]
    if (typeof value === 'function') {
      return value.bind(auth)
    }
    return value
  }
})

export { getFirebaseAdmin, adminAuth }
