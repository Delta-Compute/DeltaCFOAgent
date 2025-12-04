"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  TrendingUp,
  TrendingDown,
  Receipt,
  FileText,
  Users,
  ArrowRight,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { useTenant } from "@/context/tenant-context";
import { homepage, type HomepageContent, type HomepageKpis } from "@/lib/api";
import { formatCurrency, formatNumber } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingPage, StatsSkeleton } from "@/components/ui/loading";
import { ErrorState } from "@/components/ui/empty-state";

// KPI Card Component
function KpiCard({
  title,
  value,
  change,
  format,
  icon: Icon,
}: {
  title: string;
  value: number;
  change?: number;
  format: "currency" | "number" | "percent";
  icon: React.ElementType;
}) {
  const formattedValue =
    format === "currency"
      ? formatCurrency(value)
      : format === "percent"
      ? `${value.toFixed(1)}%`
      : formatNumber(value);

  const isPositive = change && change >= 0;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold font-heading">{formattedValue}</div>
        {change !== undefined && (
          <div className="flex items-center gap-1 mt-1">
            {isPositive ? (
              <TrendingUp className="h-3 w-3 text-green-600" />
            ) : (
              <TrendingDown className="h-3 w-3 text-red-600" />
            )}
            <span
              className={`text-xs ${
                isPositive ? "text-green-600" : "text-red-600"
              }`}
            >
              {isPositive ? "+" : ""}
              {change.toFixed(1)}% from last month
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Quick Action Card
function QuickActionCard({
  title,
  description,
  href,
  icon: Icon,
}: {
  title: string;
  description: string;
  href: string;
  icon: React.ElementType;
}) {
  return (
    <Link href={href}>
      <Card className="card-interactive h-full">
        <CardContent className="flex items-start gap-4 p-6">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
            <Icon className="h-5 w-5 text-primary" />
          </div>
          <div className="flex-1">
            <h3 className="font-medium">{title}</h3>
            <p className="text-sm text-muted-foreground mt-1">{description}</p>
          </div>
          <ArrowRight className="h-4 w-4 text-muted-foreground" />
        </CardContent>
      </Card>
    </Link>
  );
}

export default function DashboardHomePage() {
  const { currentTenant } = useTenant();
  const [content, setContent] = useState<HomepageContent | null>(null);
  const [kpis, setKpis] = useState<HomepageKpis | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load homepage data
  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setIsLoading(true);
    setError(null);

    try {
      // Load content and KPIs in parallel
      const [contentResult, kpisResult] = await Promise.all([
        homepage.getContent(),
        homepage.getKpis(),
      ]);

      if (contentResult.success && contentResult.data) {
        setContent(contentResult.data);
      }

      if (kpisResult.success && kpisResult.data) {
        setKpis(kpisResult.data);
      }
    } catch (err) {
      console.error("Failed to load homepage data:", err);
      setError("Failed to load dashboard data");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleRegenerate() {
    setIsRegenerating(true);
    try {
      const result = await homepage.regenerate();
      if (result.success && result.data) {
        setContent(result.data);
      }
    } catch (err) {
      console.error("Failed to regenerate content:", err);
    } finally {
      setIsRegenerating(false);
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-8">
        <StatsSkeleton />
        <LoadingPage message="Loading dashboard..." />
      </div>
    );
  }

  if (error) {
    return <ErrorState title={error} onRetry={loadData} />;
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold font-heading">
            {content?.company_name || currentTenant?.company_name || "Dashboard"}
          </h1>
          {content?.company_description && (
            <p className="text-muted-foreground mt-1">
              {content.company_description}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {content?.cached_at && (
            <Badge variant="secondary" className="text-xs">
              Updated {new Date(content.cached_at).toLocaleDateString()}
            </Badge>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={handleRegenerate}
            disabled={isRegenerating}
            className="gap-2"
          >
            {isRegenerating ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            Refresh Insights
          </Button>
        </div>
      </div>

      {/* KPIs Grid */}
      <div className="stats-grid">
        <KpiCard
          title="Total Revenue"
          value={kpis?.total_revenue || 0}
          change={5.2}
          format="currency"
          icon={TrendingUp}
        />
        <KpiCard
          title="Total Expenses"
          value={kpis?.total_expenses || 0}
          change={-2.3}
          format="currency"
          icon={TrendingDown}
        />
        <KpiCard
          title="Net Income"
          value={kpis?.net_income || 0}
          change={8.1}
          format="currency"
          icon={TrendingUp}
        />
        <KpiCard
          title="Transactions"
          value={kpis?.transaction_count || 0}
          format="number"
          icon={Receipt}
        />
      </div>

      {/* AI Insights */}
      {content?.insights && content.insights.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              AI Insights
            </CardTitle>
            <CardDescription>
              Key observations about your financial data
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3">
              {content.insights.map((insight, index) => (
                <li key={index} className="flex items-start gap-3">
                  <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-medium text-primary">
                    {index + 1}
                  </div>
                  <p className="text-sm text-muted-foreground">{insight}</p>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Quick Actions */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <QuickActionCard
            title="View Transactions"
            description="Browse and manage all your financial transactions"
            href="/dashboard"
            icon={Receipt}
          />
          <QuickActionCard
            title="Match Revenue"
            description="Match invoices with incoming payments"
            href="/revenue"
            icon={FileText}
          />
          <QuickActionCard
            title="Manage Workforce"
            description="View employees and process payroll"
            href="/workforce"
            icon={Users}
          />
        </div>
      </div>
    </div>
  );
}
