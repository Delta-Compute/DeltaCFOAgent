"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/auth-context";
import { useTenant } from "@/context/tenant-context";
import { DashboardNav } from "@/components/dashboard/dashboard-nav";
import { Loader2 } from "lucide-react";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { currentTenant, isLoading: tenantLoading } = useTenant();

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  // Redirect to onboarding if no tenant
  useEffect(() => {
    if (!tenantLoading && isAuthenticated && !currentTenant) {
      // In production, redirect to onboarding
      // For now, we'll just show the content
      // router.push("/onboarding");
    }
  }, [tenantLoading, isAuthenticated, currentTenant, router]);

  // Show loading state while checking auth
  if (authLoading || tenantLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  // For development, allow access even without auth
  // In production, this would show a loading state until redirect happens
  // if (!isAuthenticated) {
  //   return null;
  // }

  return (
    <div className="min-h-screen bg-background">
      <DashboardNav />
      <main className="container-main py-8">{children}</main>
    </div>
  );
}
