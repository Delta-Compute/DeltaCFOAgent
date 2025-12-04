"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Receipt,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Filter,
  Download,
  RefreshCw,
  Search,
  Calendar,
  Building2,
  Tag,
  MoreHorizontal,
  Eye,
  Edit,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";

import { transactions, type Transaction } from "@/lib/api";
import { formatCurrency, formatDate, cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Card, CardContent } from "@/components/ui/card";
import { DataTable, type Column } from "@/components/dashboard/data-table";
import { StatsCard, StatsGrid } from "@/components/dashboard/stats-card";
import { ErrorState } from "@/components/ui/empty-state";

// Stats interface
interface DashboardStats {
  totalTransactions: number;
  totalIncome: number;
  totalExpenses: number;
  netChange: number;
}

export default function TransactionsDashboardPage() {
  const router = useRouter();

  // State
  const [transactionData, setTransactionData] = useState<Transaction[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Pagination
  const [page, setPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const pageSize = 20;

  // Filters
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<string>("all");
  const [dateRange, setDateRange] = useState<string>("all");

  // Sorting
  const [sortKey, setSortKey] = useState<string>("date");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  // Selection
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());

  // Load transactions
  const loadTransactions = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const params: Record<string, string> = {
        page: String(page),
        per_page: String(pageSize),
      };

      if (search) params.search = search;
      if (category !== "all") params.category = category;

      const result = await transactions.list(params);

      if (result.success && result.data) {
        setTransactionData(result.data.transactions);
        setTotalItems(result.data.total);

        // Calculate stats from data
        const income = result.data.transactions
          .filter((t) => t.amount > 0)
          .reduce((sum, t) => sum + t.amount, 0);
        const expenses = result.data.transactions
          .filter((t) => t.amount < 0)
          .reduce((sum, t) => sum + Math.abs(t.amount), 0);

        setStats({
          totalTransactions: result.data.total,
          totalIncome: income,
          totalExpenses: expenses,
          netChange: income - expenses,
        });
      } else {
        throw new Error(result.error?.message || "Failed to load transactions");
      }
    } catch (err) {
      console.error("Failed to load transactions:", err);
      setError(err instanceof Error ? err.message : "Failed to load transactions");
    } finally {
      setIsLoading(false);
    }
  }, [page, pageSize, search, category]);

  useEffect(() => {
    loadTransactions();
  }, [loadTransactions]);

  // Handle sort
  function handleSort(key: string) {
    if (sortKey === key) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDirection("desc");
    }
  }

  // Handle row click
  function handleRowClick(transaction: Transaction) {
    router.push(`/transactions/${transaction.id}`);
  }

  // Handle bulk enrich
  async function handleBulkEnrich() {
    if (selectedKeys.size === 0) {
      toast.error("Please select transactions to enrich");
      return;
    }

    try {
      const result = await transactions.bulkEnrich(Array.from(selectedKeys));
      if (result.success) {
        toast.success(`Enriched ${result.data?.enriched || 0} transactions`);
        loadTransactions();
        setSelectedKeys(new Set());
      }
    } catch {
      toast.error("Failed to enrich transactions");
    }
  }

  // Table columns
  const columns: Column<Transaction>[] = [
    {
      key: "date",
      header: "Date",
      sortable: true,
      width: "120px",
      render: (item) => (
        <span className="text-sm">{formatDate(item.date)}</span>
      ),
    },
    {
      key: "description",
      header: "Description",
      render: (item) => (
        <div className="max-w-[300px]">
          <div className="font-medium truncate">{item.description}</div>
          {item.entity_name && (
            <div className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
              <Building2 className="h-3 w-3" />
              {item.entity_name}
            </div>
          )}
        </div>
      ),
    },
    {
      key: "category",
      header: "Category",
      render: (item) => (
        <div className="flex flex-col gap-1">
          {item.category ? (
            <>
              <Badge variant="secondary" className="w-fit">
                {item.category}
              </Badge>
              {item.subcategory && (
                <span className="text-xs text-muted-foreground">
                  {item.subcategory}
                </span>
              )}
            </>
          ) : (
            <Badge variant="outline" className="w-fit text-muted-foreground">
              Uncategorized
            </Badge>
          )}
        </div>
      ),
    },
    {
      key: "confidence_score",
      header: "Confidence",
      width: "100px",
      render: (item) => {
        if (!item.confidence_score) return null;
        const score = item.confidence_score * 100;
        return (
          <div className="flex items-center gap-2">
            <div className="confidence-bar w-16">
              <div
                className={cn(
                  "confidence-bar-fill",
                  score >= 80 && "confidence-bar-high",
                  score >= 55 && score < 80 && "confidence-bar-medium",
                  score < 55 && "confidence-bar-low"
                )}
                style={{ width: `${score}%` }}
              />
            </div>
            <span className="text-xs text-muted-foreground">
              {score.toFixed(0)}%
            </span>
          </div>
        );
      },
    },
    {
      key: "amount",
      header: "Amount",
      align: "right",
      sortable: true,
      render: (item) => (
        <span
          className={cn(
            "font-medium",
            item.amount >= 0 ? "text-green-600" : "text-red-600"
          )}
        >
          {formatCurrency(item.amount, item.currency)}
        </span>
      ),
    },
    {
      key: "actions",
      header: "",
      width: "50px",
      render: (item) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => router.push(`/transactions/${item.id}`)}>
              <Eye className="mr-2 h-4 w-4" />
              View Details
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Edit className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={async (e) => {
                e.stopPropagation();
                const result = await transactions.enrich(item.id);
                if (result.success) {
                  toast.success("Transaction enriched");
                  loadTransactions();
                }
              }}
            >
              <Sparkles className="mr-2 h-4 w-4" />
              AI Enrich
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  if (error) {
    return <ErrorState title={error} onRetry={loadTransactions} />;
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold font-heading">Transactions</h1>
          <p className="text-muted-foreground">
            View and manage all your financial transactions
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={loadTransactions}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <Button variant="outline" size="sm">
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
        </div>
      </div>

      {/* Stats */}
      <StatsGrid>
        <StatsCard
          title="Total Transactions"
          value={stats?.totalTransactions.toLocaleString() || "0"}
          icon={Receipt}
          isLoading={isLoading}
        />
        <StatsCard
          title="Total Income"
          value={formatCurrency(stats?.totalIncome || 0)}
          icon={TrendingUp}
          trend={{ value: 5.2, label: "vs last month" }}
          isLoading={isLoading}
        />
        <StatsCard
          title="Total Expenses"
          value={formatCurrency(stats?.totalExpenses || 0)}
          icon={TrendingDown}
          trend={{ value: -2.3, label: "vs last month" }}
          isLoading={isLoading}
        />
        <StatsCard
          title="Net Change"
          value={formatCurrency(stats?.netChange || 0)}
          icon={DollarSign}
          isLoading={isLoading}
        />
      </StatsGrid>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search transactions..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
              />
            </div>
            <div className="flex items-center gap-2">
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger className="w-[180px]">
                  <Tag className="mr-2 h-4 w-4" />
                  <SelectValue placeholder="Category" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Categories</SelectItem>
                  <SelectItem value="revenue">Revenue</SelectItem>
                  <SelectItem value="expense">Expense</SelectItem>
                  <SelectItem value="transfer">Transfer</SelectItem>
                  <SelectItem value="payroll">Payroll</SelectItem>
                </SelectContent>
              </Select>

              <Select value={dateRange} onValueChange={setDateRange}>
                <SelectTrigger className="w-[150px]">
                  <Calendar className="mr-2 h-4 w-4" />
                  <SelectValue placeholder="Date Range" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Time</SelectItem>
                  <SelectItem value="today">Today</SelectItem>
                  <SelectItem value="week">This Week</SelectItem>
                  <SelectItem value="month">This Month</SelectItem>
                  <SelectItem value="quarter">This Quarter</SelectItem>
                  <SelectItem value="year">This Year</SelectItem>
                </SelectContent>
              </Select>

              <Button variant="outline" size="icon">
                <Filter className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Selection Toolbar */}
      {selectedKeys.size > 0 && (
        <div className="flex items-center justify-between rounded-lg border bg-muted/50 px-4 py-2">
          <span className="text-sm text-muted-foreground">
            {selectedKeys.size} transaction(s) selected
          </span>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleBulkEnrich}>
              <Sparkles className="mr-2 h-4 w-4" />
              AI Enrich Selected
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelectedKeys(new Set())}
            >
              Clear Selection
            </Button>
          </div>
        </div>
      )}

      {/* Data Table */}
      <DataTable
        columns={columns}
        data={transactionData}
        keyField="id"
        isLoading={isLoading}
        sortKey={sortKey}
        sortDirection={sortDirection}
        onSort={handleSort}
        selectable
        selectedKeys={selectedKeys}
        onSelectionChange={setSelectedKeys}
        page={page}
        pageSize={pageSize}
        totalItems={totalItems}
        onPageChange={setPage}
        onRowClick={handleRowClick}
        emptyMessage="No transactions found"
      />
    </div>
  );
}
