"use client";

import { ReactNode } from "react";
import { AuthProvider } from "@/context/auth-context";
import { TenantProvider } from "@/context/tenant-context";
import { TooltipProvider } from "@/components/ui/tooltip";

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  return (
    <AuthProvider>
      <TenantProvider>
        <TooltipProvider delayDuration={300}>
          {children}
        </TooltipProvider>
      </TenantProvider>
    </AuthProvider>
  );
}
