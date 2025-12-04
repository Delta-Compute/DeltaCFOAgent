"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Users,
  Plus,
  RefreshCw,
  Search,
  MoreHorizontal,
  Eye,
  Edit,
  Trash2,
  PieChart,
  DollarSign,
  Percent,
} from "lucide-react";
import { toast } from "sonner";

import { shareholders, type Shareholder } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { DataTable, type Column } from "@/components/dashboard/data-table";
import { StatsCard, StatsGrid } from "@/components/dashboard/stats-card";
import { ErrorState, EmptyState } from "@/components/ui/empty-state";

// Stats interface
interface ShareholderStats {
  totalShareholders: number;
  totalOwnership: number;
  totalInvested: number;
  shareClasses: string[];
}

// Ownership progress bar
function OwnershipBar({ percentage }: { percentage: number }) {
  return (
    <div className="flex items-center gap-2">
      <div className="w-24 h-2 bg-muted rounded-full overflow-hidden">
        <div
          className="h-full bg-primary rounded-full transition-all"
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
      <span className="text-sm font-medium">{percentage.toFixed(1)}%</span>
    </div>
  );
}

// Pie chart placeholder (simplified visual)
function OwnershipChart({ shareholdersList }: { shareholdersList: Shareholder[] }) {
  const colors = [
    "bg-blue-500",
    "bg-green-500",
    "bg-yellow-500",
    "bg-purple-500",
    "bg-pink-500",
    "bg-orange-500",
    "bg-cyan-500",
    "bg-indigo-500",
  ];

  const sortedShareholders = [...shareholdersList]
    .sort((a, b) => b.ownership_percentage - a.ownership_percentage)
    .slice(0, 8);

  const totalPercentage = sortedShareholders.reduce(
    (sum, s) => sum + s.ownership_percentage,
    0
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <PieChart className="h-5 w-5" />
          Ownership Distribution
        </CardTitle>
        <CardDescription>Visual breakdown of ownership stakes</CardDescription>
      </CardHeader>
      <CardContent>
        {shareholdersList.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            No shareholders to display
          </div>
        ) : (
          <div className="space-y-4">
            {/* Stacked bar representation */}
            <div className="h-8 rounded-lg overflow-hidden flex">
              {sortedShareholders.map((s, i) => (
                <div
                  key={s.id}
                  className={`${colors[i % colors.length]} transition-all`}
                  style={{ width: `${(s.ownership_percentage / totalPercentage) * 100}%` }}
                  title={`${s.name}: ${s.ownership_percentage}%`}
                />
              ))}
            </div>

            {/* Legend */}
            <div className="grid gap-2 grid-cols-2">
              {sortedShareholders.map((s, i) => (
                <div key={s.id} className="flex items-center gap-2 text-sm">
                  <div className={`w-3 h-3 rounded-full ${colors[i % colors.length]}`} />
                  <span className="truncate">{s.name}</span>
                  <span className="text-muted-foreground ml-auto">
                    {s.ownership_percentage.toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function ShareholdersPage() {
  // State
  const [shareholdersList, setShareholdersList] = useState<Shareholder[]>([]);
  const [stats, setStats] = useState<ShareholderStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  // Load shareholders
  const loadShareholders = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await shareholders.list();

      if (result.success && result.data) {
        // Filter by search
        let filtered = result.data;
        if (search) {
          const searchLower = search.toLowerCase();
          filtered = result.data.filter(
            (s) =>
              s.name.toLowerCase().includes(searchLower) ||
              s.email?.toLowerCase().includes(searchLower) ||
              s.share_class?.toLowerCase().includes(searchLower)
          );
        }

        setShareholdersList(filtered);

        // Calculate stats from all data
        const totalOwnership = result.data.reduce(
          (sum, s) => sum + s.ownership_percentage,
          0
        );
        const totalInvested = result.data.reduce(
          (sum, s) => sum + s.total_invested,
          0
        );
        const shareClasses = [...new Set(result.data.map((s) => s.share_class).filter(Boolean))] as string[];

        setStats({
          totalShareholders: result.data.length,
          totalOwnership,
          totalInvested,
          shareClasses,
        });
      } else {
        throw new Error(result.error?.message || "Failed to load shareholders");
      }
    } catch (err) {
      console.error("Failed to load shareholders:", err);
      setError(err instanceof Error ? err.message : "Failed to load shareholders");
    } finally {
      setIsLoading(false);
    }
  }, [search]);

  useEffect(() => {
    loadShareholders();
  }, [loadShareholders]);

  // Delete shareholder
  async function handleDelete(shareholder: Shareholder) {
    if (!confirm(`Are you sure you want to remove ${shareholder.name}?`)) {
      return;
    }

    try {
      const result = await shareholders.delete(shareholder.id);
      if (result.success) {
        toast.success("Shareholder removed");
        loadShareholders();
      } else {
        toast.error(result.error?.message || "Failed to remove shareholder");
      }
    } catch {
      toast.error("Failed to remove shareholder");
    }
  }

  // Table columns
  const columns: Column<Shareholder>[] = [
    {
      key: "name",
      header: "Shareholder",
      render: (item) => (
        <div>
          <div className="font-medium">{item.name}</div>
          {item.email && (
            <div className="text-xs text-muted-foreground">{item.email}</div>
          )}
        </div>
      ),
    },
    {
      key: "share_class",
      header: "Share Class",
      width: "120px",
      render: (item) =>
        item.share_class ? (
          <Badge variant="outline">{item.share_class}</Badge>
        ) : (
          <span className="text-muted-foreground">-</span>
        ),
    },
    {
      key: "ownership_percentage",
      header: "Ownership",
      width: "180px",
      render: (item) => <OwnershipBar percentage={item.ownership_percentage} />,
    },
    {
      key: "total_invested",
      header: "Total Invested",
      align: "right",
      render: (item) => (
        <span className="font-medium">
          {formatCurrency(item.total_invested, item.currency)}
        </span>
      ),
    },
    {
      key: "investment_date",
      header: "Investment Date",
      width: "120px",
      render: (item) =>
        item.investment_date ? (
          <span className="text-sm">{formatDate(item.investment_date)}</span>
        ) : (
          <span className="text-muted-foreground">-</span>
        ),
    },
    {
      key: "actions",
      header: "",
      width: "50px",
      render: (item) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem>
              <Eye className="mr-2 h-4 w-4" />
              View Details
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Edit className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="text-destructive"
              onClick={() => handleDelete(item)}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Remove
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  if (error) {
    return <ErrorState title={error} onRetry={loadShareholders} />;
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold font-heading">Shareholders</h1>
          <p className="text-muted-foreground">
            Manage company ownership and equity
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={loadShareholders}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Add Shareholder
          </Button>
        </div>
      </div>

      {/* Stats */}
      <StatsGrid>
        <StatsCard
          title="Total Shareholders"
          value={stats?.totalShareholders.toLocaleString() || "0"}
          icon={Users}
          isLoading={isLoading}
        />
        <StatsCard
          title="Total Ownership"
          value={`${stats?.totalOwnership.toFixed(1) || "0"}%`}
          icon={Percent}
          isLoading={isLoading}
        />
        <StatsCard
          title="Total Invested"
          value={formatCurrency(stats?.totalInvested || 0)}
          icon={DollarSign}
          isLoading={isLoading}
        />
        <StatsCard
          title="Share Classes"
          value={stats?.shareClasses.length.toString() || "0"}
          icon={PieChart}
          isLoading={isLoading}
        />
      </StatsGrid>

      {/* Chart and Table */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Chart */}
        <div className="lg:col-span-1">
          <OwnershipChart shareholdersList={shareholdersList} />
        </div>

        {/* Table */}
        <div className="lg:col-span-2 space-y-4">
          {/* Search */}
          <Card>
            <CardContent className="pt-6">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search shareholders..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </CardContent>
          </Card>

          {/* Table */}
          <DataTable
            columns={columns}
            data={shareholdersList}
            keyField="id"
            isLoading={isLoading}
            emptyMessage="No shareholders found"
          />
        </div>
      </div>
    </div>
  );
}
