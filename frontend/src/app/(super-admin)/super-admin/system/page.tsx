'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { superAdmin, APIPerformanceResponse, DatabaseStatsResponse, HealthOverviewResponse } from '@/lib/api';
import { Activity, Database, Clock, Zap, Server, HardDrive, AlertTriangle, CheckCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts';

function formatMs(ms: number): string {
  if (ms < 1) return '<1ms';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function getPerformanceBadge(avgMs: number) {
  if (avgMs < 100) {
    return <Badge className="bg-green-100 text-green-800">Fast</Badge>;
  }
  if (avgMs < 500) {
    return <Badge className="bg-amber-100 text-amber-800">Moderate</Badge>;
  }
  return <Badge className="bg-red-100 text-red-800">Slow</Badge>;
}

function getStatusBadge(status: string) {
  const variants: Record<string, { className: string; icon: React.ReactNode }> = {
    healthy: {
      className: 'bg-green-100 text-green-800',
      icon: <CheckCircle className="h-3 w-3 mr-1" />,
    },
    degraded: {
      className: 'bg-amber-100 text-amber-800',
      icon: <AlertTriangle className="h-3 w-3 mr-1" />,
    },
    critical: {
      className: 'bg-red-100 text-red-800',
      icon: <AlertTriangle className="h-3 w-3 mr-1" />,
    },
  };
  const variant = variants[status] || variants.healthy;
  return (
    <Badge className={cn('flex items-center font-medium', variant.className)}>
      {variant.icon}
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  );
}

export default function SuperAdminSystemPage() {
  const [apiPerformance, setApiPerformance] = useState<APIPerformanceResponse | null>(null);
  const [dbStats, setDbStats] = useState<DatabaseStatsResponse | null>(null);
  const [health, setHealth] = useState<HealthOverviewResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [perfRes, dbRes, healthRes] = await Promise.all([
          superAdmin.getAPIPerformance(7),
          superAdmin.getDatabaseStats(),
          superAdmin.getHealthOverview(),
        ]);

        if (perfRes.success && perfRes.data) {
          setApiPerformance(perfRes.data.data);
        }
        if (dbRes.success && dbRes.data) {
          setDbStats(dbRes.data.data);
        }
        if (healthRes.success && healthRes.data) {
          setHealth(healthRes.data.data);
        }
      } catch (error) {
        console.error('Failed to load system data:', error);
      } finally {
        setIsLoading(false);
      }
    }

    loadData();
  }, []);

  // Prepare response time chart data
  const responseTimeData = apiPerformance?.response_times_by_hour
    ?.slice(-24)
    .map((d) => ({
      hour: new Date(d.hour).toLocaleString('en-US', { hour: 'numeric', hour12: true }),
      avg: Math.round(d.avg_ms),
      p95: Math.round(d.p95_ms),
    })) || [];

  // Prepare endpoints chart data
  const endpointsData = apiPerformance?.by_endpoint
    ?.slice(0, 10)
    .map((e) => ({
      endpoint: e.endpoint.length > 30 ? e.endpoint.substring(0, 30) + '...' : e.endpoint,
      fullEndpoint: e.endpoint,
      calls: e.count,
      avgMs: Math.round(e.avg_ms),
    })) || [];

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">System</h1>
          <p className="text-sm text-zinc-500">API performance and database health</p>
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
        <h1 className="text-2xl font-bold text-zinc-900">System</h1>
        <p className="text-sm text-zinc-500">API performance and database health</p>
      </div>

      {/* Status Banner */}
      <Card className={cn(
        'border-l-4',
        health?.status === 'healthy' && 'border-l-green-500',
        health?.status === 'degraded' && 'border-l-amber-500',
        health?.status === 'critical' && 'border-l-red-500'
      )}>
        <CardContent className="flex items-center justify-between py-4">
          <div className="flex items-center gap-4">
            <Server className={cn(
              'h-8 w-8',
              health?.status === 'healthy' && 'text-green-500',
              health?.status === 'degraded' && 'text-amber-500',
              health?.status === 'critical' && 'text-red-500'
            )} />
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-zinc-900">System Status</span>
                {getStatusBadge(health?.status || 'healthy')}
              </div>
              <p className="text-sm text-zinc-500">
                {health?.active_users_24h || 0} active users in last 24h |{' '}
                {health?.recent_errors || 0} errors in last 24h
              </p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-zinc-900">
              {formatMs(apiPerformance?.overall_avg_ms || 0)}
            </div>
            <p className="text-xs text-zinc-500">Avg response time</p>
          </div>
        </CardContent>
      </Card>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-zinc-600">Total Requests</CardTitle>
            <Activity className="h-4 w-4 text-zinc-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {apiPerformance?.total_requests?.toLocaleString() || 0}
            </div>
            <p className="text-xs text-zinc-500">Last 7 days</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-zinc-600">P95 Response</CardTitle>
            <Zap className="h-4 w-4 text-zinc-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatMs(apiPerformance?.p95_ms || 0)}
            </div>
            <p className="text-xs text-zinc-500">95th percentile</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-zinc-600">Database Size</CardTitle>
            <Database className="h-4 w-4 text-zinc-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatBytes(dbStats?.database_size_bytes || 0)}
            </div>
            <p className="text-xs text-zinc-500">Total size</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-zinc-600">Connections</CardTitle>
            <HardDrive className="h-4 w-4 text-zinc-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {dbStats?.active_connections || 0}
            </div>
            <p className="text-xs text-zinc-500">Active connections</p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Response Time Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Response Times</CardTitle>
            <CardDescription>Average and P95 response times (last 24 hours)</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={responseTimeData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
                  <XAxis dataKey="hour" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                  <YAxis
                    tick={{ fontSize: 12 }}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v) => `${v}ms`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#fff',
                      border: '1px solid #e4e4e7',
                      borderRadius: '8px',
                    }}
                    formatter={(value: number) => [`${value}ms`]}
                  />
                  <Line
                    type="monotone"
                    dataKey="avg"
                    name="Average"
                    stroke="#4F46E5"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="p95"
                    name="P95"
                    stroke="#F59E0B"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Top Endpoints Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Top Endpoints by Traffic</CardTitle>
            <CardDescription>Most requested endpoints</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={endpointsData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                  <YAxis
                    type="category"
                    dataKey="endpoint"
                    tick={{ fontSize: 10 }}
                    tickLine={false}
                    axisLine={false}
                    width={120}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#fff',
                      border: '1px solid #e4e4e7',
                      borderRadius: '8px',
                    }}
                    formatter={(value: number) => [`${value.toLocaleString()} calls`, 'Requests']}
                  />
                  <Bar dataKey="calls" fill="#4F46E5" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Slow Endpoints Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Slow Endpoints</CardTitle>
          <CardDescription>Endpoints with highest average response times</CardDescription>
        </CardHeader>
        <CardContent>
          {apiPerformance?.slow_endpoints && apiPerformance.slow_endpoints.length > 0 ? (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Endpoint</TableHead>
                    <TableHead className="text-right">Calls</TableHead>
                    <TableHead className="text-right">Avg Time</TableHead>
                    <TableHead className="text-right">P95 Time</TableHead>
                    <TableHead className="text-right">Max Time</TableHead>
                    <TableHead>Performance</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {apiPerformance.slow_endpoints.slice(0, 10).map((endpoint) => (
                    <TableRow key={endpoint.endpoint}>
                      <TableCell className="font-mono text-sm">
                        {endpoint.endpoint}
                      </TableCell>
                      <TableCell className="text-right">
                        {endpoint.count.toLocaleString()}
                      </TableCell>
                      <TableCell className="text-right font-medium">
                        {formatMs(endpoint.avg_ms)}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatMs(endpoint.p95_ms)}
                      </TableCell>
                      <TableCell className="text-right text-zinc-500">
                        {formatMs(endpoint.max_ms)}
                      </TableCell>
                      <TableCell>
                        {getPerformanceBadge(endpoint.avg_ms)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="flex h-32 items-center justify-center text-sm text-zinc-500">
              No slow endpoint data available
            </div>
          )}
        </CardContent>
      </Card>

      {/* Database Stats */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Database Statistics</CardTitle>
          <CardDescription>Table sizes and row counts</CardDescription>
        </CardHeader>
        <CardContent>
          {dbStats?.table_stats && dbStats.table_stats.length > 0 ? (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Table</TableHead>
                    <TableHead className="text-right">Row Count</TableHead>
                    <TableHead className="text-right">Size</TableHead>
                    <TableHead className="text-right">Index Size</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {dbStats.table_stats
                    .sort((a, b) => b.size_bytes - a.size_bytes)
                    .map((table) => (
                      <TableRow key={table.table_name}>
                        <TableCell className="font-mono text-sm">
                          {table.table_name}
                        </TableCell>
                        <TableCell className="text-right">
                          {table.row_count.toLocaleString()}
                        </TableCell>
                        <TableCell className="text-right">
                          {formatBytes(table.size_bytes)}
                        </TableCell>
                        <TableCell className="text-right text-zinc-500">
                          {formatBytes(table.index_size_bytes)}
                        </TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="flex h-32 items-center justify-center text-sm text-zinc-500">
              No database statistics available
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
