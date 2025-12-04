"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { useAuth } from "./auth-context";

// Types
export interface Tenant {
  tenant_id: string;
  tenant_name: string;
  company_name: string;
  company_description?: string;
  industry?: string;
  primary_currency: string;
  timezone: string;
  branding?: {
    logo_url?: string;
    primary_color?: string;
  };
}

interface TenantContextType {
  currentTenant: Tenant | null;
  availableTenants: Tenant[];
  isLoading: boolean;
  switchTenant: (tenantId: string) => Promise<void>;
  refreshTenant: () => Promise<void>;
}

// Context
const TenantContext = createContext<TenantContextType | undefined>(undefined);

// Provider
export function TenantProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  const [currentTenant, setCurrentTenant] = useState<Tenant | null>(null);
  const [availableTenants, setAvailableTenants] = useState<Tenant[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Load tenant data when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      loadTenantData();
    } else {
      setCurrentTenant(null);
      setAvailableTenants([]);
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  async function loadTenantData() {
    setIsLoading(true);
    try {
      // Get current tenant config
      const configResponse = await fetch("/api/tenant/config/general", {
        credentials: "include",
      });

      if (configResponse.ok) {
        const config = await configResponse.json();
        setCurrentTenant({
          tenant_id: config.tenant_id || "delta",
          tenant_name: config.company_name || "Delta",
          company_name: config.company_name || "Delta",
          company_description: config.company_description,
          industry: config.industry,
          primary_currency: config.primary_currency || "USD",
          timezone: config.timezone || "UTC",
          branding: config.branding,
        });
      }

      // For now, just use the current tenant as the only available one
      // In a multi-tenant setup, this would fetch the user's accessible tenants
      if (currentTenant) {
        setAvailableTenants([currentTenant]);
      }
    } catch (error) {
      console.error("Failed to load tenant data:", error);
    } finally {
      setIsLoading(false);
    }
  }

  async function switchTenant(tenantId: string) {
    setIsLoading(true);
    try {
      const response = await fetch("/api/tenant/switch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tenant_id: tenantId }),
        credentials: "include",
      });

      if (response.ok) {
        await loadTenantData();
      }
    } finally {
      setIsLoading(false);
    }
  }

  async function refreshTenant() {
    await loadTenantData();
  }

  return (
    <TenantContext.Provider
      value={{
        currentTenant,
        availableTenants,
        isLoading,
        switchTenant,
        refreshTenant,
      }}
    >
      {children}
    </TenantContext.Provider>
  );
}

// Hook
export function useTenant() {
  const context = useContext(TenantContext);
  if (context === undefined) {
    throw new Error("useTenant must be used within a TenantProvider");
  }
  return context;
}
