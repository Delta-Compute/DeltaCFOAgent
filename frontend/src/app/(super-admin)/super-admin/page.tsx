'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { superAdmin, UserActivityResponse, FeatureUsageResponse, ErrorTrendsResponse, HealthOverviewResponse } from '@/lib/api';
import { Users, Building2, TrendingUp, AlertCircle, Activity, Clock } from 'lucide-react';
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

interface KPICardProps {
  title: string;
  value: string | number;
  description: string;
  icon: React.ElementType;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  status?: 'healthy' | 'warning' | 'critical';
}

function mapHealthStatus(status: string | undefined): 'healthy' | 'warning' | 'critical' {
  if (status === 'degraded') return 'warning';
  if (status === 'critical') return 'critical';
  return 'healthy';
}

function KPICard({ title, value, description, icon: Icon, trend, status }: KPICardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-zinc-600">{title}</CardTitle>
        <div
          className={cn(
            'rounded-full p-2',
            status === 'healthy' && 'bg-green-100',
            status === 'warning' && 'bg-amber-100',
            status === 'critical' && 'bg-red-100',
            !status && 'bg-zinc-100'
          )}
        >
          <Icon
            className={cn(
              'h-4 w-4',
              status === 'healthy' && 'text-green-600',
              status === 'warning' && 'text-amber-600',
              status === 'critical' && 'text-red-600',
              !status && 'text-zinc-600'
            )}
          />
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <div className="flex items-center gap-2">
          <p className="text-xs text-zinc-500">{description}</p>
          {trend && (
            <span
              className={cn(
                'text-xs font-medium',
                trend.isPositive ? 'text-green-600' : 'text-red-600'
              )}
            >
              {trend.isPositive ? '+' : ''}{trend.value}%
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default function SuperAdminOverviewPage() {
  const [userActivity, setUserActivity] = useState<UserActivityResponse | null>(null);
  const [featureUsage, setFeatureUsage] = useState<FeatureUsageResponse | null>(null);
  const [errorTrends, setErrorTrends] = useState<ErrorTrendsResponse | null>(null);
  const [health, setHealth] = useState<HealthOverviewResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [activityRes, featuresRes, errorsRes, healthRes] = await Promise.all([
          superAdmin.getUserActivity(30),
          superAdmin.getFeatureUsage(30),
          superAdmin.getErrorTrends(7),
          superAdmin.getHealthOverview(),
        ]);

        if (activityRes.success && activityRes.data) {
          setUserActivity(activityRes.data.data);
        }
        if (featuresRes.success && featuresRes.data) {
          setFeatureUsage(featuresRes.data.data);
        }
        if (errorsRes.success && errorsRes.data) {
          setErrorTrends(errorsRes.data.data);
        }
        if (healthRes.success && healthRes.data) {
          setHealth(healthRes.data.data);
        }
      } catch (error) {
        console.error('Failed to load overview data:', error);
      } finally {
        setIsLoading(false);
      }
    }

    loadData();
  }, []);

  // Prepare chart data
  const dailyActiveUsersData = userActivity?.daily_active_users
    .slice(0, 14)
    .reverse()
    .map((d) => ({
      date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      users: d.count,
    })) || [];

  const topFeaturesData = featureUsage?.features
    .slice(0, 8)
    .map((f) => ({
      name: f.feature.replace(/_/g, ' '),
      uses: f.total_uses,
      adoption: f.adoption_rate,
    })) || [];

  const dailyErrorsData = errorTrends?.daily_errors
    .slice(0, 7)
    .reverse()
    .map((d) => ({
      date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      errors: d.count,
    })) || [];

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Overview</h1>
          <p className="text-sm text-zinc-500">Product analytics and system health</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader className="pb-2">
                <div className="h-4 w-24 rounded bg-zinc-200" />
              </CardHeader>
              <CardContent>
                <div className="h-8 w-16 rounded bg-zinc-200" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-zinc-900">Overview</h1>
        <p className="text-sm text-zinc-500">Product analytics and system health</p>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KPICard
          title="Total Users"
          value={userActivity?.total_users?.toLocaleString() || '0'}
          description="Registered accounts"
          icon={Users}
        />
        <KPICard
          title="Weekly Active"
          value={userActivity?.weekly_active_users?.toLocaleString() || '0'}
          description="Last 7 days"
          icon={Activity}
        />
        <KPICard
          title="Monthly Active"
          value={userActivity?.monthly_active_users?.toLocaleString() || '0'}
          description="Last 30 days"
          icon={TrendingUp}
        />
        <KPICard
          title="System Status"
          value={health?.status === 'healthy' ? 'Healthy' : health?.status || 'Unknown'}
          description={`${health?.active_users_24h || 0} active in 24h`}
          icon={health?.status === 'healthy' ? Activity : AlertCircle}
          status={mapHealthStatus(health?.status)}
        />
      </div>

      {/* Charts Row */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Daily Active Users Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Daily Active Users</CardTitle>
            <CardDescription>Last 14 days</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={dailyActiveUsersData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 12 }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 12 }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#fff',
                      border: '1px solid #e4e4e7',
                      borderRadius: '8px',
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="users"
                    stroke="#4F46E5"
                    strokeWidth={2}
                    dot={{ fill: '#4F46E5', strokeWidth: 0, r: 3 }}
                    activeDot={{ r: 5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Feature Adoption Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Feature Usage</CardTitle>
            <CardDescription>Top features by usage (30 days)</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={topFeaturesData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                  <YAxis
                    type="category"
                    dataKey="name"
                    tick={{ fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                    width={100}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#fff',
                      border: '1px solid #e4e4e7',
                      borderRadius: '8px',
                    }}
                    formatter={(value: number) => [value.toLocaleString(), 'Uses']}
                  />
                  <Bar dataKey="uses" fill="#4F46E5" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Error Trends and Quick Stats */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Error Trends */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Error Trends</CardTitle>
            <CardDescription>Last 7 days ({errorTrends?.total_errors || 0} total)</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[200px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={dailyErrorsData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" vertical={false} />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 12 }}
                    tickLine={false}
                    axisLine={false}
                  />
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

        {/* Quick Stats */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Quick Stats</CardTitle>
            <CardDescription>System overview</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-zinc-400" />
                <span className="text-sm text-zinc-600">Errors (24h)</span>
              </div>
              <span className="font-semibold">{health?.recent_errors || 0}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-zinc-400" />
                <span className="text-sm text-zinc-600">Active Users (24h)</span>
              </div>
              <span className="font-semibold">{health?.active_users_24h || 0}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Building2 className="h-4 w-4 text-zinc-400" />
                <span className="text-sm text-zinc-600">Features Tracked</span>
              </div>
              <span className="font-semibold">{featureUsage?.features.length || 0}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Users className="h-4 w-4 text-zinc-400" />
                <span className="text-sm text-zinc-600">Active Users (30d)</span>
              </div>
              <span className="font-semibold">{featureUsage?.total_active_users || 0}</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
