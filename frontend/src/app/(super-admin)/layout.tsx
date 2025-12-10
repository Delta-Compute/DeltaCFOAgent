'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/auth-context';
import { SuperAdminNav } from '@/components/super-admin/super-admin-nav';
import { LoadingPage } from '@/components/ui/loading';
import { AlertCircle } from 'lucide-react';

export default function SuperAdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const [isAuthorized, setIsAuthorized] = useState(false);
  const [checkingAuth, setCheckingAuth] = useState(true);

  useEffect(() => {
    if (isLoading) return;

    if (!user) {
      router.push('/login');
      return;
    }

    // Check if user is super_admin
    if (user.user_type !== 'super_admin') {
      setIsAuthorized(false);
      setCheckingAuth(false);
      return;
    }

    setIsAuthorized(true);
    setCheckingAuth(false);
  }, [user, isLoading, router]);

  // Show loading while checking auth
  if (isLoading || checkingAuth) {
    return <LoadingPage />;
  }

  // Show access denied if not super_admin
  if (!isAuthorized) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-zinc-50">
        <div className="mx-auto max-w-md rounded-lg border border-red-200 bg-white p-8 text-center shadow-sm">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
            <AlertCircle className="h-6 w-6 text-red-600" />
          </div>
          <h1 className="mb-2 text-xl font-semibold text-zinc-900">
            Access Denied
          </h1>
          <p className="mb-6 text-sm text-zinc-600">
            This area is restricted to Super Admin users only. If you believe
            this is an error, please contact your system administrator.
          </p>
          <button
            onClick={() => router.push('/dashboard')}
            className="inline-flex items-center justify-center rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-800"
          >
            Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-50">
      <SuperAdminNav />
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        {children}
      </main>
    </div>
  );
}
