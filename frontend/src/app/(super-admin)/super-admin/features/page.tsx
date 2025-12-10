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
import { superAdmin, FeatureUsageResponse, FeatureTrendsResponse } from '@/lib/api';
import { Layers, TrendingUp, Users, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  Legend,
} from 'recharts';

function getAdoptionBadge(rate: number) {
  if (rate >= 50) {
    return <Badge className="bg-green-100 text-green-800">High</Badge>;
  }
  if (rate >= 20) {
    return <Badge className="bg-amber-100 text-amber-800">Medium</Badge>;
  }
  return <Badge className="bg-red-100 text-red-800">Low</Badge>;
}

function formatFeatureName(name: string): string {
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

const COLORS = ['#4F46E5', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];

export default function SuperAdminFeaturesPage() {
  const [featureUsage, setFeatureUsage] = useState<FeatureUsageResponse | null>(null);
  const [trends, setTrends] = useState<FeatureTrendsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [usageRes, trendsRes] = await Promise.all([
          superAdmin.getFeatureUsage(30),
          superAdmin.getFeatureTrends(14),
        ]);

        if (usageRes.success && usageRes.data) {
          setFeatureUsage(usageRes.data.data);
        }
        if (trendsRes.success && trendsRes.data) {
          setTrends(trendsRes.data.data);
        }
      } catch (error) {
        console.error('Failed to load feature data:', error);
      } finally {
        setIsLoading(false);
      }
    }

    loadData();
  }, []);

  // Prepare chart data
  const topFeaturesData = featureUsage?.features
    .slice(0, 10)
    .map((f) => ({
      name: formatFeatureName(f.feature),
      uses: f.total_uses,
      users: f.unique_users,
    })) || [];

  // Prepare trend chart data
  const topFeatureNames = featureUsage?.features.slice(0, 5).map((f) => f.feature) || [];
  const trendChartData = trends?.trends
    .slice(-14)
    .map((day) => {
      const data: Record<string, unknown> = {
        date: new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      };
      topFeatureNames.forEach((feature) => {
        data[formatFeatureName(feature)] = day.feature_counts[feature] || 0;
      });
      return data;
    }) || [];

  // Calculate summary stats
  const totalUses = featureUsage?.features.reduce((sum, f) => sum + f.total_uses, 0) || 0;
  const avgAdoption = featureUsage?.features.length
    ? featureUsage.features.reduce((sum, f) => sum + f.adoption_rate, 0) / featureUsage.features.length
    : 0;
  const lowAdoptionCount = featureUsage?.features.filter((f) => f.adoption_rate < 20).length || 0;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Features</h1>
          <p className="text-sm text-zinc-500">Feature usage and adoption analytics</p>
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
        <h1 className="text-2xl font-bold text-zinc-900">Features</h1>
        <p className="text-sm text-zinc-500">Feature usage and adoption analytics</p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-zinc-600">Total Uses</CardTitle>
            <Activity className="h-4 w-4 text-zinc-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalUses.toLocaleString()}</div>
            <p className="text-xs text-zinc-500">Last 30 days</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-zinc-600">Features Tracked</CardTitle>
            <Layers className="h-4 w-4 text-zinc-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{featureUsage?.features.length || 0}</div>
            <p className="text-xs text-zinc-500">Unique features</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-zinc-600">Avg Adoption</CardTitle>
            <TrendingUp className="h-4 w-4 text-zinc-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{avgAdoption.toFixed(1)}%</div>
            <p className="text-xs text-zinc-500">Of active users</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-zinc-600">Low Adoption</CardTitle>
            <Users className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-amber-600">{lowAdoptionCount}</div>
            <p className="text-xs text-zinc-500">Features under 20%</p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Feature Usage Bar Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Top Features by Usage</CardTitle>
            <CardDescription>Total uses in last 30 days</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[350px]">
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
                    width={120}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#fff',
                      border: '1px solid #e4e4e7',
                      borderRadius: '8px',
                    }}
                  />
                  <Bar dataKey="uses" fill="#4F46E5" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Feature Trends Line Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Feature Trends</CardTitle>
            <CardDescription>Top 5 features over time</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[350px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#fff',
                      border: '1px solid #e4e4e7',
                      borderRadius: '8px',
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  {topFeatureNames.map((feature, index) => (
                    <Line
                      key={feature}
                      type="monotone"
                      dataKey={formatFeatureName(feature)}
                      stroke={COLORS[index % COLORS.length]}
                      strokeWidth={2}
                      dot={false}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Features Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">All Features</CardTitle>
          <CardDescription>Complete feature usage breakdown</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Feature</TableHead>
                  <TableHead className="text-right">Total Uses</TableHead>
                  <TableHead className="text-right">Unique Users</TableHead>
                  <TableHead className="text-right">Adoption Rate</TableHead>
                  <TableHead>Adoption Level</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {featureUsage?.features.map((feature) => (
                  <TableRow key={feature.feature}>
                    <TableCell className="font-medium">
                      {formatFeatureName(feature.feature)}
                    </TableCell>
                    <TableCell className="text-right">{feature.total_uses.toLocaleString()}</TableCell>
                    <TableCell className="text-right">{feature.unique_users}</TableCell>
                    <TableCell className="text-right">
                      <span
                        className={cn(
                          'font-medium',
                          feature.adoption_rate >= 50 && 'text-green-600',
                          feature.adoption_rate >= 20 && feature.adoption_rate < 50 && 'text-amber-600',
                          feature.adoption_rate < 20 && 'text-red-600'
                        )}
                      >
                        {feature.adoption_rate.toFixed(1)}%
                      </span>
                    </TableCell>
                    <TableCell>{getAdoptionBadge(feature.adoption_rate)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
