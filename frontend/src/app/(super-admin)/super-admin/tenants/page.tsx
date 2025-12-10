'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { superAdmin, SuperAdminTenant, TenantGrowthResponse, ChurnRiskResponse } from '@/lib/api';
import { Search, Building2, TrendingUp, AlertTriangle, ChevronLeft, ChevronRight, Users } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

function formatDate(dateString: string | null): string {
  if (!dateString) return 'Never';
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function formatRelativeTime(dateString: string | null): string {
  if (!dateString) return 'Never';
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  return formatDate(dateString);
}

function getChurnRiskBadge(risk: 'low' | 'medium' | 'high') {
  const variants = {
    low: { label: 'Low Risk', className: 'bg-green-100 text-green-800' },
    medium: { label: 'Medium Risk', className: 'bg-amber-100 text-amber-800' },
    high: { label: 'High Risk', className: 'bg-red-100 text-red-800' },
  };
  const variant = variants[risk];
  return <Badge className={cn('font-medium', variant.className)}>{variant.label}</Badge>;
}

function getHealthScoreColor(score: number): string {
  if (score >= 80) return 'text-green-600';
  if (score >= 50) return 'text-amber-600';
  return 'text-red-600';
}

export default function SuperAdminTenantsPage() {
  const [tenants, setTenants] = useState<SuperAdminTenant[]>([]);
  const [growth, setGrowth] = useState<TenantGrowthResponse | null>(null);
  const [churnRisk, setChurnRisk] = useState<ChurnRiskResponse | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const perPage = 20;

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      try {
        const [tenantsRes, growthRes, churnRes] = await Promise.all([
          superAdmin.getTenants({ page, per_page: perPage, search: search || undefined }),
          superAdmin.getTenantGrowth(90),
          superAdmin.getChurnRisk(),
        ]);

        if (tenantsRes.success && tenantsRes.data) {
          setTenants(tenantsRes.data.data.tenants);
          setTotal(tenantsRes.data.data.total);
        }
        if (growthRes.success && growthRes.data) {
          setGrowth(growthRes.data.data);
        }
        if (churnRes.success && churnRes.data) {
          setChurnRisk(churnRes.data.data);
        }
      } catch (error) {
        console.error('Failed to load tenants:', error);
      } finally {
        setIsLoading(false);
      }
    }

    loadData();
  }, [page, search]);

  const totalPages = Math.ceil(total / perPage);

  // Prepare growth chart data
  const growthChartData = growth?.new_tenants_by_week
    .slice(-8)
    .map((d) => ({
      week: d.week,
      count: d.count,
    })) || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-zinc-900">Tenants</h1>
        <p className="text-sm text-zinc-500">Tenant health and growth analytics</p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-zinc-600">Total Tenants</CardTitle>
            <Building2 className="h-4 w-4 text-zinc-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{growth?.total_tenants || 0}</div>
            <p className="text-xs text-zinc-500">All time</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-zinc-600">Active (30d)</CardTitle>
            <TrendingUp className="h-4 w-4 text-zinc-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{growth?.active_tenants_30d || 0}</div>
            <p className="text-xs text-zinc-500">Had activity</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-zinc-600">High Risk</CardTitle>
            <AlertTriangle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {churnRisk?.risk_summary.high_risk || 0}
            </div>
            <p className="text-xs text-zinc-500">Need attention</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-zinc-600">At Risk</CardTitle>
            <AlertTriangle className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-amber-600">
              {churnRisk?.risk_summary.total_at_risk || 0}
            </div>
            <p className="text-xs text-zinc-500">Total at risk</p>
          </CardContent>
        </Card>
      </div>

      {/* Growth Chart */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">New Tenants by Week</CardTitle>
          <CardDescription>Last 8 weeks</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={growthChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" vertical={false} />
                <XAxis dataKey="week" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#fff',
                    border: '1px solid #e4e4e7',
                    borderRadius: '8px',
                  }}
                />
                <Bar dataKey="count" fill="#4F46E5" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Tenants Table */}
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle className="text-base">All Tenants</CardTitle>
              <CardDescription>{total} tenants total</CardDescription>
            </div>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
              <Input
                placeholder="Search by company name..."
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
                className="w-full pl-9 sm:w-64"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex h-64 items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
            </div>
          ) : tenants.length === 0 ? (
            <div className="flex h-64 flex-col items-center justify-center text-center">
              <Building2 className="mb-4 h-12 w-12 text-zinc-300" />
              <p className="text-sm text-zinc-500">No tenants found</p>
            </div>
          ) : (
            <>
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Company</TableHead>
                      <TableHead className="text-center">
                        <div className="flex items-center justify-center gap-1">
                          <Users className="h-3.5 w-3.5" />
                          Users
                        </div>
                      </TableHead>
                      <TableHead className="text-right">Txns (30d)</TableHead>
                      <TableHead className="text-center">Health</TableHead>
                      <TableHead>Risk</TableHead>
                      <TableHead>Last Active</TableHead>
                      <TableHead>Created</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {tenants.map((tenant) => (
                      <TableRow key={tenant.id}>
                        <TableCell>
                          <div>
                            <div className="font-medium">{tenant.company_name}</div>
                            {tenant.description && (
                              <div className="max-w-xs truncate text-xs text-zinc-500">
                                {tenant.description}
                              </div>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="text-center">{tenant.user_count}</TableCell>
                        <TableCell className="text-right">{tenant.transactions_30d}</TableCell>
                        <TableCell className="text-center">
                          <span className={cn('font-semibold', getHealthScoreColor(tenant.health_score))}>
                            {tenant.health_score}%
                          </span>
                        </TableCell>
                        <TableCell>{getChurnRiskBadge(tenant.churn_risk)}</TableCell>
                        <TableCell className="text-zinc-500">
                          {formatRelativeTime(tenant.last_activity)}
                        </TableCell>
                        <TableCell className="text-zinc-500">
                          {formatDate(tenant.created_at)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="mt-4 flex items-center justify-between">
                  <p className="text-sm text-zinc-500">
                    Showing {(page - 1) * perPage + 1} to {Math.min(page * perPage, total)} of {total}
                  </p>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(page - 1)}
                      disabled={page === 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <span className="text-sm text-zinc-600">
                      Page {page} of {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(page + 1)}
                      disabled={page === totalPages}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* At Risk Tenants */}
      {churnRisk && churnRisk.at_risk_tenants.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">At-Risk Tenants</CardTitle>
            <CardDescription>
              Tenants showing signs of potential churn
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {churnRisk.at_risk_tenants.slice(0, 5).map((tenant) => (
                <div
                  key={tenant.tenant_id}
                  className="flex items-start justify-between rounded-lg border p-4"
                >
                  <div>
                    <div className="font-medium">{tenant.company_name}</div>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {tenant.risk_factors.map((factor, i) => (
                        <span
                          key={i}
                          className="rounded bg-zinc-100 px-2 py-0.5 text-xs text-zinc-600"
                        >
                          {factor}
                        </span>
                      ))}
                    </div>
                  </div>
                  {getChurnRiskBadge(tenant.risk_level)}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
