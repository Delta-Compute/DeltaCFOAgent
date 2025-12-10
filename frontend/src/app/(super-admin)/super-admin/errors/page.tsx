'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { superAdmin, ErrorTrendsResponse, RecentErrorsResponse, RecentError } from '@/lib/api';
import { AlertCircle, ChevronDown, ChevronRight, AlertTriangle, Bug, Clock, ChevronLeft } from 'lucide-react';
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

function formatDateTime(dateString: string): string {
  return new Date(dateString).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

function getErrorTypeBadge(errorType: string) {
  const variants: Record<string, { label: string; className: string }> = {
    api_error: { label: 'API Error', className: 'bg-red-100 text-red-800' },
    validation_error: { label: 'Validation', className: 'bg-amber-100 text-amber-800' },
    auth_error: { label: 'Auth Error', className: 'bg-purple-100 text-purple-800' },
    database_error: { label: 'Database', className: 'bg-blue-100 text-blue-800' },
    network_error: { label: 'Network', className: 'bg-orange-100 text-orange-800' },
    unknown: { label: 'Unknown', className: 'bg-zinc-100 text-zinc-800' },
  };
  const variant = variants[errorType] || variants.unknown;
  return <Badge className={cn('font-medium', variant.className)}>{variant.label}</Badge>;
}

interface ErrorRowProps {
  error: RecentError;
}

function ErrorRow({ error }: ErrorRowProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="border-b last:border-b-0">
      <div
        className="flex cursor-pointer items-center gap-4 px-4 py-3 hover:bg-zinc-50"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <button className="flex-shrink-0 text-zinc-400">
          {isExpanded ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-zinc-900 truncate">{error.message}</span>
          </div>
          <div className="mt-1 flex items-center gap-3 text-xs text-zinc-500">
            <span>{error.endpoint || 'Unknown endpoint'}</span>
            <span>User: {error.user_email || 'Anonymous'}</span>
            <span>Tenant: {error.tenant_id || 'N/A'}</span>
          </div>
        </div>
        <div className="flex-shrink-0">{getErrorTypeBadge(error.error_type)}</div>
        <div className="flex-shrink-0 text-sm text-zinc-500 w-20 text-right">
          {formatRelativeTime(error.timestamp)}
        </div>
      </div>
      {isExpanded && error.stack_trace && (
        <div className="bg-zinc-900 px-4 py-3 mx-4 mb-3 rounded-md overflow-x-auto">
          <pre className="text-xs text-zinc-300 whitespace-pre-wrap font-mono">
            {error.stack_trace}
          </pre>
        </div>
      )}
    </div>
  );
}

export default function SuperAdminErrorsPage() {
  const [errorTrends, setErrorTrends] = useState<ErrorTrendsResponse | null>(null);
  const [recentErrors, setRecentErrors] = useState<RecentErrorsResponse | null>(null);
  const [errorTypeFilter, setErrorTypeFilter] = useState<string>('all');
  const [page, setPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const perPage = 20;

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      try {
        const [trendsRes, errorsRes] = await Promise.all([
          superAdmin.getErrorTrends(14),
          superAdmin.getRecentErrors({
            page,
            per_page: perPage,
            error_type: errorTypeFilter !== 'all' ? errorTypeFilter : undefined,
          }),
        ]);

        if (trendsRes.success && trendsRes.data) {
          setErrorTrends(trendsRes.data.data);
        }
        if (errorsRes.success && errorsRes.data) {
          setRecentErrors(errorsRes.data.data);
        }
      } catch (error) {
        console.error('Failed to load error data:', error);
      } finally {
        setIsLoading(false);
      }
    }

    loadData();
  }, [page, errorTypeFilter]);

  // Prepare chart data
  const dailyErrorsData = errorTrends?.daily_errors
    .slice(-14)
    .map((d) => ({
      date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      errors: d.count,
    })) || [];

  // Get unique error types for filter
  const errorTypes = errorTrends?.by_type
    ? Object.keys(errorTrends.by_type).sort()
    : [];

  const totalPages = recentErrors ? Math.ceil(recentErrors.total / perPage) : 1;

  if (isLoading && !errorTrends) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Errors</h1>
          <p className="text-sm text-zinc-500">Error monitoring and diagnostics</p>
        </div>
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-zinc-900">Errors</h1>
        <p className="text-sm text-zinc-500">Error monitoring and diagnostics</p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-zinc-600">Total Errors (14d)</CardTitle>
            <AlertCircle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {errorTrends?.total_errors?.toLocaleString() || 0}
            </div>
            <p className="text-xs text-zinc-500">Last 14 days</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-zinc-600">Errors Today</CardTitle>
            <Bug className="h-4 w-4 text-zinc-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {errorTrends?.daily_errors?.[errorTrends.daily_errors.length - 1]?.count || 0}
            </div>
            <p className="text-xs text-zinc-500">Since midnight</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-zinc-600">Error Types</CardTitle>
            <AlertTriangle className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{errorTypes.length}</div>
            <p className="text-xs text-zinc-500">Unique types</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-zinc-600">Avg/Day</CardTitle>
            <Clock className="h-4 w-4 text-zinc-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {errorTrends?.daily_errors?.length
                ? Math.round(errorTrends.total_errors / errorTrends.daily_errors.length)
                : 0}
            </div>
            <p className="text-xs text-zinc-500">Average per day</p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Error Frequency Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Error Frequency</CardTitle>
            <CardDescription>Daily error count (last 14 days)</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[250px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={dailyErrorsData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" vertical={false} />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#fff',
                      border: '1px solid #e4e4e7',
                      borderRadius: '8px',
                    }}
                  />
                  <Bar dataKey="errors" fill="#DC2626" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Errors by Type */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Errors by Type</CardTitle>
            <CardDescription>Distribution of error types</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {errorTrends?.by_type &&
                Object.entries(errorTrends.by_type)
                  .sort(([, a], [, b]) => b - a)
                  .map(([type, count]) => {
                    const percentage = errorTrends.total_errors
                      ? Math.round((count / errorTrends.total_errors) * 100)
                      : 0;
                    return (
                      <div key={type} className="flex items-center gap-3">
                        <div className="w-24 flex-shrink-0">
                          {getErrorTypeBadge(type)}
                        </div>
                        <div className="flex-1">
                          <div className="h-2 rounded-full bg-zinc-100 overflow-hidden">
                            <div
                              className="h-full bg-red-500 rounded-full"
                              style={{ width: `${percentage}%` }}
                            />
                          </div>
                        </div>
                        <div className="w-16 text-right text-sm text-zinc-600">
                          {count.toLocaleString()} ({percentage}%)
                        </div>
                      </div>
                    );
                  })}
              {(!errorTrends?.by_type || Object.keys(errorTrends.by_type).length === 0) && (
                <div className="flex h-32 items-center justify-center text-sm text-zinc-500">
                  No error data available
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Errors List */}
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle className="text-base">Recent Errors</CardTitle>
              <CardDescription>
                {recentErrors?.total || 0} errors total
              </CardDescription>
            </div>
            <Select
              value={errorTypeFilter}
              onValueChange={(v) => {
                setErrorTypeFilter(v);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-full sm:w-44">
                <SelectValue placeholder="Filter by type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                {errorTypes.map((type) => (
                  <SelectItem key={type} value={type}>
                    {type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex h-64 items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
            </div>
          ) : !recentErrors?.errors?.length ? (
            <div className="flex h-64 flex-col items-center justify-center text-center">
              <AlertCircle className="mb-4 h-12 w-12 text-zinc-300" />
              <p className="text-sm text-zinc-500">No errors found</p>
            </div>
          ) : (
            <>
              <div className="rounded-md border">
                {recentErrors.errors.map((error, index) => (
                  <ErrorRow key={error.id || index} error={error} />
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="mt-4 flex items-center justify-between">
                  <p className="text-sm text-zinc-500">
                    Showing {(page - 1) * perPage + 1} to{' '}
                    {Math.min(page * perPage, recentErrors.total)} of {recentErrors.total}
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
    </div>
  );
}
