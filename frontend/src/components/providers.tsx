"use client";

import { ReactNode } from "react";
import { AuthProvider } from "@/context/auth-context";
import { TenantProvider } from "@/context/tenant-context";
import { AnalyticsProvider } from "@/context/analytics-context";
import { TooltipProvider } from "@/components/ui/tooltip";
import { PageTracker } from "@/components/analytics/page-tracker";

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  return (
    <AuthProvider>
      <TenantProvider>
        <AnalyticsProvider>
          <TooltipProvider delayDuration={300}>
            <PageTracker />
            {children}
          </TooltipProvider>
        </AnalyticsProvider>
      </TenantProvider>
    </AuthProvider>
  );
}
