"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Building2,
  Bell,
  Shield,
  Palette,
  Globe,
  Save,
  RefreshCw,
} from "lucide-react";
import { toast } from "sonner";

import { tenant, type TenantConfig } from "@/lib/api";

// Branding interface
interface BrandingConfig {
  primary_color?: string;
  logo_url?: string;
}
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/loading";
import { ErrorState } from "@/components/ui/empty-state";

// Timezone options
const timezones = [
  { value: "UTC", label: "UTC" },
  { value: "America/New_York", label: "Eastern Time (ET)" },
  { value: "America/Chicago", label: "Central Time (CT)" },
  { value: "America/Denver", label: "Mountain Time (MT)" },
  { value: "America/Los_Angeles", label: "Pacific Time (PT)" },
  { value: "America/Sao_Paulo", label: "Brasilia Time (BRT)" },
  { value: "Europe/London", label: "London (GMT)" },
  { value: "Europe/Paris", label: "Central European Time (CET)" },
  { value: "Asia/Tokyo", label: "Japan Standard Time (JST)" },
  { value: "Australia/Sydney", label: "Australian Eastern Time (AET)" },
];

// Currency options
const currencies = [
  { value: "USD", label: "US Dollar (USD)" },
  { value: "EUR", label: "Euro (EUR)" },
  { value: "GBP", label: "British Pound (GBP)" },
  { value: "BRL", label: "Brazilian Real (BRL)" },
  { value: "CAD", label: "Canadian Dollar (CAD)" },
  { value: "AUD", label: "Australian Dollar (AUD)" },
  { value: "JPY", label: "Japanese Yen (JPY)" },
  { value: "CHF", label: "Swiss Franc (CHF)" },
];

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("general");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // General settings
  const [generalConfig, setGeneralConfig] = useState<Partial<TenantConfig>>({
    company_name: "",
    company_description: "",
    primary_currency: "USD",
    timezone: "UTC",
  });

  // Branding settings
  const [brandingConfig, setBrandingConfig] = useState<BrandingConfig>({
    primary_color: "#4F46E5",
    logo_url: "",
  });

  // Load settings
  const loadSettings = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [generalResult, brandingResult] = await Promise.all([
        tenant.getConfig("general"),
        tenant.getConfig("branding"),
      ]);

      if (generalResult.success && generalResult.data) {
        setGeneralConfig({
          company_name: generalResult.data.company_name || "",
          company_description: generalResult.data.company_description || "",
          primary_currency: generalResult.data.primary_currency || "USD",
          timezone: generalResult.data.timezone || "UTC",
          industry: generalResult.data.industry || "",
        });
      }

      if (brandingResult.success && brandingResult.data) {
        const brandData = brandingResult.data as unknown as BrandingConfig;
        setBrandingConfig({
          primary_color: brandData.primary_color || "#4F46E5",
          logo_url: brandData.logo_url || "",
        });
      }
    } catch (err) {
      console.error("Failed to load settings:", err);
      setError(err instanceof Error ? err.message : "Failed to load settings");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  // Save general settings
  async function handleSaveGeneral() {
    setIsSaving(true);
    try {
      const result = await tenant.updateConfig("general", generalConfig);
      if (result.success) {
        toast.success("General settings saved");
      } else {
        toast.error(result.error?.message || "Failed to save settings");
      }
    } catch {
      toast.error("Failed to save settings");
    } finally {
      setIsSaving(false);
    }
  }

  // Save branding settings
  async function handleSaveBranding() {
    setIsSaving(true);
    try {
      const result = await tenant.updateConfig("branding", brandingConfig as Partial<TenantConfig>);
      if (result.success) {
        toast.success("Branding settings saved");
      } else {
        toast.error(result.error?.message || "Failed to save settings");
      }
    } catch {
      toast.error("Failed to save settings");
    } finally {
      setIsSaving(false);
    }
  }

  if (error) {
    return <ErrorState title={error} onRetry={loadSettings} />;
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold font-heading">Settings</h1>
          <p className="text-muted-foreground">
            Manage your account and organization settings
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={loadSettings} disabled={isLoading}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Settings Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="general" className="gap-2">
            <Building2 className="h-4 w-4" />
            General
          </TabsTrigger>
          <TabsTrigger value="branding" className="gap-2">
            <Palette className="h-4 w-4" />
            Branding
          </TabsTrigger>
          <TabsTrigger value="notifications" className="gap-2">
            <Bell className="h-4 w-4" />
            Notifications
          </TabsTrigger>
          <TabsTrigger value="security" className="gap-2">
            <Shield className="h-4 w-4" />
            Security
          </TabsTrigger>
        </TabsList>

        {/* General Settings */}
        <TabsContent value="general" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Company Information</CardTitle>
              <CardDescription>
                Basic information about your organization
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {isLoading ? (
                <div className="space-y-4">
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-24 w-full" />
                  <Skeleton className="h-10 w-full" />
                </div>
              ) : (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="company_name">Company Name</Label>
                    <Input
                      id="company_name"
                      value={generalConfig.company_name || ""}
                      onChange={(e) =>
                        setGeneralConfig({ ...generalConfig, company_name: e.target.value })
                      }
                      placeholder="Enter company name"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="company_description">Description</Label>
                    <Textarea
                      id="company_description"
                      value={generalConfig.company_description || ""}
                      onChange={(e) =>
                        setGeneralConfig({
                          ...generalConfig,
                          company_description: e.target.value,
                        })
                      }
                      placeholder="Describe your company"
                      rows={3}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="industry">Industry</Label>
                    <Input
                      id="industry"
                      value={generalConfig.industry || ""}
                      onChange={(e) =>
                        setGeneralConfig({ ...generalConfig, industry: e.target.value })
                      }
                      placeholder="e.g., Technology, Finance, Healthcare"
                    />
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Regional Settings</CardTitle>
              <CardDescription>
                Configure currency and timezone preferences
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {isLoading ? (
                <div className="space-y-4">
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-10 w-full" />
                </div>
              ) : (
                <>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="currency">Primary Currency</Label>
                      <Select
                        value={generalConfig.primary_currency || "USD"}
                        onValueChange={(value) =>
                          setGeneralConfig({ ...generalConfig, primary_currency: value })
                        }
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select currency" />
                        </SelectTrigger>
                        <SelectContent>
                          {currencies.map((c) => (
                            <SelectItem key={c.value} value={c.value}>
                              {c.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="timezone">Timezone</Label>
                      <Select
                        value={generalConfig.timezone || "UTC"}
                        onValueChange={(value) =>
                          setGeneralConfig({ ...generalConfig, timezone: value })
                        }
                      >
                        <SelectTrigger>
                          <Globe className="mr-2 h-4 w-4" />
                          <SelectValue placeholder="Select timezone" />
                        </SelectTrigger>
                        <SelectContent>
                          {timezones.map((tz) => (
                            <SelectItem key={tz.value} value={tz.value}>
                              {tz.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          <div className="flex justify-end">
            <Button onClick={handleSaveGeneral} disabled={isSaving || isLoading}>
              <Save className="mr-2 h-4 w-4" />
              {isSaving ? "Saving..." : "Save Changes"}
            </Button>
          </div>
        </TabsContent>

        {/* Branding Settings */}
        <TabsContent value="branding" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Brand Identity</CardTitle>
              <CardDescription>
                Customize the look and feel of your workspace
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {isLoading ? (
                <div className="space-y-4">
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-10 w-full" />
                </div>
              ) : (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="logo_url">Logo URL</Label>
                    <Input
                      id="logo_url"
                      value={brandingConfig.logo_url || ""}
                      onChange={(e) =>
                        setBrandingConfig({ ...brandingConfig, logo_url: e.target.value })
                      }
                      placeholder="https://example.com/logo.png"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="primary_color">Primary Color</Label>
                    <div className="flex gap-2">
                      <Input
                        id="primary_color"
                        type="color"
                        value={brandingConfig.primary_color || "#4F46E5"}
                        onChange={(e) =>
                          setBrandingConfig({ ...brandingConfig, primary_color: e.target.value })
                        }
                        className="w-16 h-10 p-1 cursor-pointer"
                      />
                      <Input
                        value={brandingConfig.primary_color || "#4F46E5"}
                        onChange={(e) =>
                          setBrandingConfig({ ...brandingConfig, primary_color: e.target.value })
                        }
                        placeholder="#4F46E5"
                        className="flex-1 font-mono"
                      />
                    </div>
                  </div>

                  {brandingConfig.primary_color && (
                    <div className="flex items-center gap-4 p-4 rounded-lg border">
                      <div
                        className="w-16 h-16 rounded-lg"
                        style={{ backgroundColor: brandingConfig.primary_color }}
                      />
                      <div>
                        <p className="font-medium">Color Preview</p>
                        <p className="text-sm text-muted-foreground">
                          This color will be used throughout the application
                        </p>
                      </div>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>

          <div className="flex justify-end">
            <Button onClick={handleSaveBranding} disabled={isSaving || isLoading}>
              <Save className="mr-2 h-4 w-4" />
              {isSaving ? "Saving..." : "Save Changes"}
            </Button>
          </div>
        </TabsContent>

        {/* Notifications Settings */}
        <TabsContent value="notifications" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Notification Preferences</CardTitle>
              <CardDescription>
                Manage how you receive notifications
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                Notification settings coming soon...
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Security Settings */}
        <TabsContent value="security" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Security Settings</CardTitle>
              <CardDescription>
                Manage your account security preferences
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                Security settings coming soon...
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
