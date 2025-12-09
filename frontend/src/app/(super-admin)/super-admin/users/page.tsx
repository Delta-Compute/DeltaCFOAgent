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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { superAdmin, SuperAdminUser, UserActivityResponse, UserSessionsResponse } from '@/lib/api';
import { Search, Users, Activity, Clock, ChevronLeft, ChevronRight, UserPlus } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { InviteUserModal } from '@/components/super-admin/invite-user-modal';

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

function getUserTypeBadge(userType: string) {
  const variants: Record<string, { label: string; className: string }> = {
    super_admin: { label: 'Super Admin', className: 'bg-amber-100 text-amber-800' },
    fractional_cfo: { label: 'CFO', className: 'bg-indigo-100 text-indigo-800' },
    tenant_admin: { label: 'Admin', className: 'bg-green-100 text-green-800' },
    cfo_assistant: { label: 'Assistant', className: 'bg-blue-100 text-blue-800' },
    employee: { label: 'Employee', className: 'bg-zinc-100 text-zinc-800' },
  };
  const variant = variants[userType] || { label: userType, className: 'bg-zinc-100 text-zinc-800' };
  return <Badge className={cn('font-medium', variant.className)}>{variant.label}</Badge>;
}

export default function SuperAdminUsersPage() {
  const [users, setUsers] = useState<SuperAdminUser[]>([]);
  const [activity, setActivity] = useState<UserActivityResponse | null>(null);
  const [sessions, setSessions] = useState<UserSessionsResponse | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [userTypeFilter, setUserTypeFilter] = useState<string>('all');
  const [isLoading, setIsLoading] = useState(true);
  const [inviteModalOpen, setInviteModalOpen] = useState(false);
  const perPage = 20;

  const loadData = async () => {
    setIsLoading(true);
    try {
      const params: { page: number; per_page: number; search?: string; user_type?: string } = {
        page,
        per_page: perPage,
      };
      if (search) params.search = search;
      if (userTypeFilter !== 'all') params.user_type = userTypeFilter;

      const [usersRes, activityRes, sessionsRes] = await Promise.all([
        superAdmin.getUsers(params),
        superAdmin.getUserActivity(30),
        superAdmin.getUserSessions(30),
      ]);

      if (usersRes.success && usersRes.data) {
        setUsers(usersRes.data.data.users);
        setTotal(usersRes.data.data.total);
      }
      if (activityRes.success && activityRes.data) {
        setActivity(activityRes.data.data);
      }
      if (sessionsRes.success && sessionsRes.data) {
        setSessions(sessionsRes.data.data);
      }
    } catch (error) {
      console.error('Failed to load users:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [page, search, userTypeFilter]);

  const totalPages = Math.ceil(total / perPage);

  // Prepare session chart data
  const sessionChartData = sessions?.sessions_by_day
    .slice(0, 14)
    .reverse()
    .map((d) => ({
      date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      sessions: d.count,
    })) || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Users</h1>
          <p className="text-sm text-zinc-500">User engagement and activity analytics</p>
        </div>
        <Button onClick={() => setInviteModalOpen(true)}>
          <UserPlus className="mr-2 h-4 w-4" />
          Invite User
        </Button>
      </div>

      {/* Invite Modal */}
      <InviteUserModal
        open={inviteModalOpen}
        onOpenChange={setInviteModalOpen}
        onSuccess={loadData}
      />

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-zinc-600">Total Users</CardTitle>
            <Users className="h-4 w-4 text-zinc-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{activity?.total_users?.toLocaleString() || 0}</div>
            <p className="text-xs text-zinc-500">Registered accounts</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-zinc-600">Weekly Active</CardTitle>
            <Activity className="h-4 w-4 text-zinc-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{activity?.weekly_active_users?.toLocaleString() || 0}</div>
            <p className="text-xs text-zinc-500">Last 7 days</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-zinc-600">Avg Session</CardTitle>
            <Clock className="h-4 w-4 text-zinc-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{sessions?.average_duration_minutes?.toFixed(0) || 0}m</div>
            <p className="text-xs text-zinc-500">Average duration</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-zinc-600">Total Sessions</CardTitle>
            <Activity className="h-4 w-4 text-zinc-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{sessions?.total_sessions?.toLocaleString() || 0}</div>
            <p className="text-xs text-zinc-500">Last 30 days</p>
          </CardContent>
        </Card>
      </div>

      {/* Sessions Chart */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Sessions Over Time</CardTitle>
          <CardDescription>Daily session count (last 14 days)</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={sessionChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#fff',
                    border: '1px solid #e4e4e7',
                    borderRadius: '8px',
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="sessions"
                  stroke="#4F46E5"
                  strokeWidth={2}
                  dot={{ fill: '#4F46E5', strokeWidth: 0, r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Users Table */}
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle className="text-base">All Users</CardTitle>
              <CardDescription>{total} users total</CardDescription>
            </div>
            <div className="flex flex-col gap-2 sm:flex-row">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
                <Input
                  placeholder="Search by email..."
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setPage(1);
                  }}
                  className="w-full pl-9 sm:w-64"
                />
              </div>
              <Select value={userTypeFilter} onValueChange={(v) => { setUserTypeFilter(v); setPage(1); }}>
                <SelectTrigger className="w-full sm:w-40">
                  <SelectValue placeholder="User type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  <SelectItem value="super_admin">Super Admin</SelectItem>
                  <SelectItem value="fractional_cfo">Fractional CFO</SelectItem>
                  <SelectItem value="tenant_admin">Tenant Admin</SelectItem>
                  <SelectItem value="cfo_assistant">CFO Assistant</SelectItem>
                  <SelectItem value="employee">Employee</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex h-64 items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
            </div>
          ) : users.length === 0 ? (
            <div className="flex h-64 flex-col items-center justify-center text-center">
              <Users className="mb-4 h-12 w-12 text-zinc-300" />
              <p className="text-sm text-zinc-500">No users found</p>
            </div>
          ) : (
            <>
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Email</TableHead>
                      <TableHead>Name</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead className="text-right">Sessions (7d)</TableHead>
                      <TableHead className="text-right">Actions (7d)</TableHead>
                      <TableHead>Last Active</TableHead>
                      <TableHead>Created</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {users.map((user) => (
                      <TableRow key={user.id}>
                        <TableCell className="font-medium">{user.email}</TableCell>
                        <TableCell>{user.display_name || '-'}</TableCell>
                        <TableCell>{getUserTypeBadge(user.user_type)}</TableCell>
                        <TableCell className="text-right">{user.sessions_7d}</TableCell>
                        <TableCell className="text-right">{user.actions_7d}</TableCell>
                        <TableCell className="text-zinc-500">
                          {formatRelativeTime(user.last_login_at)}
                        </TableCell>
                        <TableCell className="text-zinc-500">
                          {formatDate(user.created_at)}
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
    </div>
  );
}
