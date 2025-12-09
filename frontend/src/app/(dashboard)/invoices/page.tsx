"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  FileText,
  Plus,
  RefreshCw,
  Search,
  Calendar,
  Building2,
  MoreHorizontal,
  Eye,
  Edit,
  Trash2,
  CheckCircle2,
  Clock,
  AlertCircle,
  Download,
  Filter,
} from "lucide-react";
import { toast } from "sonner";

import { invoices, type Invoice, type InvoiceListParams } from "@/lib/api";
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

// Status badge component
function StatusBadge({ status }: { status: Invoice["status"] }) {
  const config: Record<Invoice["status"], { label: string; variant: "outline" | "secondary" | "default" | "destructive"; icon: typeof Edit }> = {
    draft: { label: "Draft", variant: "outline", icon: Edit },
    sent: { label: "Sent", variant: "secondary", icon: Clock },
    paid: { label: "Paid", variant: "default", icon: CheckCircle2 },
    partial: { label: "Partial", variant: "secondary", icon: Clock },
    overdue: { label: "Overdue", variant: "destructive", icon: AlertCircle },
  };

  const statusConfig = config[status] || config.draft;
  const { label, variant, icon: Icon } = statusConfig;

  return (
    <Badge variant={variant} className="gap-1">
      <Icon className="h-3 w-3" />
      {label}
    </Badge>
  );
}

// Stats interface
interface InvoiceStats {
  total: number;
  draft: number;
  sent: number;
  paid: number;
  overdue: number;
  totalAmount: number;
  paidAmount: number;
}

export default function InvoicesPage() {
  const router = useRouter();

  // State
  const [invoiceData, setInvoiceData] = useState<Invoice[]>([]);
  const [stats, setStats] = useState<InvoiceStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Pagination
  const [page, setPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const pageSize = 20;

  // Filters
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<string>("all");
  const [dateRange, setDateRange] = useState<string>("all");

  // Sorting
  const [sortKey, setSortKey] = useState<string>("issue_date");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  // Load invoices
  const loadInvoices = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const params: InvoiceListParams = {
        page: String(page),
        per_page: String(pageSize),
      };

      if (search) params.search = search;
      if (status !== "all") params.status = status;

      const result = await invoices.list(params);

      if (result.success && result.data) {
        setInvoiceData(result.data.invoices);
        setTotalItems(result.data.total);

        // Calculate stats from data (normally would be a separate API call)
        const draft = result.data.invoices.filter((i) => i.status === "draft").length;
        const sent = result.data.invoices.filter((i) => i.status === "sent").length;
        const paid = result.data.invoices.filter((i) => i.status === "paid").length;
        const overdue = result.data.invoices.filter((i) => i.status === "overdue").length;
        const totalAmount = result.data.invoices.reduce((sum, i) => sum + i.total_amount, 0);
        const paidAmount = result.data.invoices
          .filter((i) => i.status === "paid")
          .reduce((sum, i) => sum + i.total_amount, 0);

        setStats({
          total: result.data.total,
          draft,
          sent,
          paid,
          overdue,
          totalAmount,
          paidAmount,
        });
      } else {
        throw new Error(result.error?.message || "Failed to load invoices");
      }
    } catch (err) {
      console.error("Failed to load invoices:", err);
      setError(err instanceof Error ? err.message : "Failed to load invoices");
    } finally {
      setIsLoading(false);
    }
  }, [page, pageSize, search, status]);

  useEffect(() => {
    loadInvoices();
  }, [loadInvoices]);

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
  function handleRowClick(invoice: Invoice) {
    router.push(`/invoices/${invoice.id}`);
  }

  // Handle delete
  async function handleDelete(invoice: Invoice) {
    if (!confirm(`Are you sure you want to delete invoice ${invoice.invoice_number}?`)) {
      return;
    }

    try {
      const result = await invoices.delete(invoice.id);
      if (result.success) {
        toast.success("Invoice deleted");
        loadInvoices();
      } else {
        toast.error(result.error?.message || "Failed to delete invoice");
      }
    } catch {
      toast.error("Failed to delete invoice");
    }
  }

  // Table columns
  const columns: Column<Invoice>[] = [
    {
      key: "invoice_number",
      header: "Invoice #",
      sortable: true,
      width: "120px",
      render: (item) => (
        <span className="font-medium font-mono">{item.invoice_number}</span>
      ),
    },
    {
      key: "vendor_name",
      header: "Vendor",
      render: (item) => (
        <div className="max-w-[200px]">
          <div className="font-medium truncate">{item.vendor_name}</div>
          {item.client_name && (
            <div className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
              <Building2 className="h-3 w-3" />
              {item.client_name}
            </div>
          )}
        </div>
      ),
    },
    {
      key: "issue_date",
      header: "Issue Date",
      sortable: true,
      width: "110px",
      render: (item) => (
        <span className="text-sm">{formatDate(item.issue_date)}</span>
      ),
    },
    {
      key: "due_date",
      header: "Due Date",
      sortable: true,
      width: "110px",
      render: (item) => {
        const isOverdue =
          item.status !== "paid" && new Date(item.due_date) < new Date();
        return (
          <span className={cn("text-sm", isOverdue && "text-red-600 font-medium")}>
            {formatDate(item.due_date)}
          </span>
        );
      },
    },
    {
      key: "status",
      header: "Status",
      width: "120px",
      render: (item) => <StatusBadge status={item.status} />,
    },
    {
      key: "total_amount",
      header: "Amount",
      align: "right",
      sortable: true,
      render: (item) => (
        <span className="font-medium">
          {formatCurrency(item.total_amount, item.currency)}
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
            <DropdownMenuItem onClick={() => router.push(`/invoices/${item.id}`)}>
              <Eye className="mr-2 h-4 w-4" />
              View Details
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => router.push(`/invoices/${item.id}/edit`)}>
              <Edit className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="text-destructive"
              onClick={(e) => {
                e.stopPropagation();
                handleDelete(item);
              }}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  if (error) {
    return <ErrorState title={error} onRetry={loadInvoices} />;
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold font-heading">Invoices</h1>
          <p className="text-muted-foreground">
            Manage your invoices and track payments
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={loadInvoices}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <Button variant="outline" size="sm">
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
          <Button onClick={() => router.push("/invoices/create")}>
            <Plus className="mr-2 h-4 w-4" />
            New Invoice
          </Button>
        </div>
      </div>

      {/* Stats */}
      <StatsGrid>
        <StatsCard
          title="Total Invoices"
          value={(stats?.total ?? 0).toLocaleString()}
          icon={FileText}
          isLoading={isLoading}
        />
        <StatsCard
          title="Pending Payment"
          value={(stats?.sent ?? 0).toLocaleString()}
          icon={Clock}
          isLoading={isLoading}
        />
        <StatsCard
          title="Paid"
          value={(stats?.paid ?? 0).toLocaleString()}
          icon={CheckCircle2}
          isLoading={isLoading}
        />
        <StatsCard
          title="Total Value"
          value={formatCurrency(stats?.totalAmount || 0)}
          icon={FileText}
          trend={
            stats
              ? {
                  value: stats.paidAmount / (stats.totalAmount || 1) * 100,
                  label: "collected",
                }
              : undefined
          }
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
                placeholder="Search invoices..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
              />
            </div>
            <div className="flex items-center gap-2">
              <Select value={status} onValueChange={setStatus}>
                <SelectTrigger className="w-[150px]">
                  <FileText className="mr-2 h-4 w-4" />
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="draft">Draft</SelectItem>
                  <SelectItem value="sent">Sent</SelectItem>
                  <SelectItem value="paid">Paid</SelectItem>
                  <SelectItem value="overdue">Overdue</SelectItem>
                  <SelectItem value="cancelled">Cancelled</SelectItem>
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

      {/* Data Table */}
      <DataTable
        columns={columns}
        data={invoiceData}
        keyField="id"
        isLoading={isLoading}
        sortKey={sortKey}
        sortDirection={sortDirection}
        onSort={handleSort}
        page={page}
        pageSize={pageSize}
        totalItems={totalItems}
        onPageChange={setPage}
        onRowClick={handleRowClick}
        emptyMessage="No invoices found"
      />
    </div>
  );
}
