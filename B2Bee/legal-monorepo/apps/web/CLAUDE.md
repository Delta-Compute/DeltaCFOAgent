# Legal Web Application

## This Session Owns
- Legal web application (`apps/web/`)
- Authentication UI (login, register, forgot-password)
- Dashboard and protected routes
- API routes for auth verification
- Prisma schema for Legal-specific models

## Redirect To
- B2Bee Global -> Stripe billing, legal.b2bee.tech landing page
- Other B2Bee apps -> Cross-product features

## Tech Stack
- Next.js 14 (App Router)
- React 18
- TypeScript
- TailwindCSS
- Prisma + PostgreSQL
- Firebase Authentication (client + admin SDK)

## Development

```bash
# From monorepo root
npm run dev

# Or directly
cd apps/web && npm run dev
```

Runs on port 3006.

## Authentication Flow

1. User signs in via Firebase (email/password or Google)
2. Client gets Firebase ID token
3. Protected routes check `useAuth()` hook
4. API routes verify token via Firebase Admin SDK
5. User record created/updated in PostgreSQL

## File Structure

```
app/
├── (auth)/           # Public auth pages
│   ├── login/
│   ├── register/
│   └── forgot-password/
├── (dashboard)/      # Protected pages
│   └── dashboard/
├── api/
│   └── auth/verify/  # Token verification endpoint
├── layout.tsx        # Root layout with AuthProvider
├── page.tsx          # Redirect based on auth state
└── globals.css       # Tailwind styles

lib/
├── firebase.ts       # Firebase client config
├── firebase-admin.ts # Firebase admin SDK
├── auth-context.tsx  # React auth context
└── prisma.ts         # Prisma client

hooks/
└── useAuth.ts        # Auth hook re-export
```

## Environment Variables

Copy `.env.example` to `.env` and fill in:
- `DATABASE_URL` - PostgreSQL connection string
- `NEXT_PUBLIC_FIREBASE_*` - Firebase client config
- `FIREBASE_SERVICE_ACCOUNT_KEY` - Firebase admin credentials

## Database

Prisma schema includes:
- `User` - Firebase UID linked user accounts
- `Tenant` - Multi-tenant organizations
- `TenantUser` - User-tenant relationships

Run migrations:
```bash
npm run db:push      # Push schema changes
npm run db:studio    # Browse data
```
