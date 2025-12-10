"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  BarChart3,
  TrendingUp,
  FileText,
  Download,
  Calendar,
  DollarSign,
  PieChart,
  ArrowUpRight,
  Loader2,
  FileDown,
} from "lucide-react";
import { toast } from "sonner";

import { reports as reportsApi, exports as exportsApi, transactions } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { SankeyFlowChart } from "@/components/dashboard/sankey-flow-chart";

// Report types
interface ReportType {
  id: string;
  title: string;
  description: string;
  icon: typeof BarChart3;
  href?: string;
  downloadAction?: () => Promise<void>;
  comingSoon?: boolean;
}

export default function ReportsPage() {
  const router = useRouter();
  const [dateRange, setDateRange] = useState("year");
  const [isDownloading, setIsDownloading] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [stats, setStats] = useState({
    totalRevenue: 0,
    totalExpenses: 0,
    netProfit: 0,
  });
  const [isLoadingStats, setIsLoadingStats] = useState(true);

  // Get date range params based on selection
  const getDateParams = useCallback(() => {
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth();

    switch (dateRange) {
      case "month":
        return {
          start_date: new Date(year, month, 1).toISOString().split("T")[0],
          end_date: new Date(year, month + 1, 0).toISOString().split("T")[0],
        };
      case "quarter":
        const quarterStart = Math.floor(month / 3) * 3;
        return {
          start_date: new Date(year, quarterStart, 1).toISOString().split("T")[0],
          end_date: new Date(year, quarterStart + 3, 0).toISOString().split("T")[0],
        };
      case "lastyear":
        return {
          start_date: `${year - 1}-01-01`,
          end_date: `${year - 1}-12-31`,
        };
      case "year":
      default:
        return {
          start_date: `${year}-01-01`,
          end_date: `${year}-12-31`,
        };
    }
  }, [dateRange]);

  // Get label for the selected date range
  const getDateRangeLabel = () => {
    switch (dateRange) {
      case "month":
        return "This Month";
      case "quarter":
        return "This Quarter";
      case "lastyear":
        return "Last Year";
      case "year":
      default:
        return "Year to Date";
    }
  };

  // Load stats with date filters
  const loadStats = useCallback(async () => {
    setIsLoadingStats(true);
    try {
      const params = getDateParams();
      const result = await transactions.getStats({
        start_date: params.start_date,
        end_date: params.end_date,
      });
      if (result.success && result.data) {
        const data = result.data;
        setStats({
          totalRevenue: data.total_revenue || 0,
          totalExpenses: data.total_expenses || 0,
          netProfit: (data.total_revenue || 0) - (data.total_expenses || 0),
        });
      }
    } catch (err) {
      console.error("Failed to load stats:", err);
    } finally {
      setIsLoadingStats(false);
    }
  }, [getDateParams]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  // Download handlers
  const handleDownloadDre = async () => {
    setIsDownloading("dre");
    try {
      const params = getDateParams();
      const result = await reportsApi.downloadDrePdf(params);
      if (result.success) {
        toast.success("DRE report downloaded successfully");
      } else {
        toast.error(result.error?.message || "Failed to download DRE report");
      }
    } catch {
      toast.error("Failed to download DRE report");
    } finally {
      setIsDownloading(null);
    }
  };

  const handleDownloadBalanceSheet = async () => {
    setIsDownloading("balance-sheet");
    try {
      const params = getDateParams();
      const result = await reportsApi.downloadBalanceSheetPdf(params);
      if (result.success) {
        toast.success("Balance Sheet downloaded successfully");
      } else {
        toast.error(result.error?.message || "Failed to download Balance Sheet");
      }
    } catch {
      toast.error("Failed to download Balance Sheet");
    } finally {
      setIsDownloading(null);
    }
  };

  const handleDownloadCashFlow = async () => {
    setIsDownloading("cash-flow");
    try {
      const params = getDateParams();
      const result = await reportsApi.downloadCashFlowPdf(params);
      if (result.success) {
        toast.success("Cash Flow Statement downloaded successfully");
      } else {
        toast.error(result.error?.message || "Failed to download Cash Flow Statement");
      }
    } catch {
      toast.error("Failed to download Cash Flow Statement");
    } finally {
      setIsDownloading(null);
    }
  };

  const handleExportAll = async () => {
    setIsExporting(true);
    try {
      const params = {
        ...getDateParams(),
        format: "csv" as const,
      };
      const result = await exportsApi.transactions(params);
      if (result.success) {
        toast.success("Transactions exported successfully");
      } else {
        toast.error(result.error?.message || "Failed to export transactions");
      }
    } catch {
      toast.error("Failed to export transactions");
    } finally {
      setIsExporting(false);
    }
  };

  // Report definitions
  const reportsList: ReportType[] = [
    {
      id: "dre",
      title: "DRE (Income Statement)",
      description: "Demonstrativo de Resultado do Exercicio - Complete income statement with revenue, costs, and expenses",
      icon: FileText,
      downloadAction: handleDownloadDre,
    },
    {
      id: "pl-trend",
      title: "Profit & Loss Trend",
      description: "View income, expenses, and net profit over time with detailed breakdown by category",
      icon: TrendingUp,
      href: "/reports/pl-trend",
    },
    {
      id: "balance-sheet",
      title: "Balance Sheet",
      description: "Summary of assets, liabilities, and equity at a specific point in time",
      icon: BarChart3,
      downloadAction: handleDownloadBalanceSheet,
    },
    {
      id: "cash-flow",
      title: "Cash Flow Statement",
      description: "Track the movement of cash in and out of your business",
      icon: DollarSign,
      downloadAction: handleDownloadCashFlow,
    },
    {
      id: "expense-breakdown",
      title: "Expense Breakdown",
      description: "Detailed analysis of expenses by category, vendor, and time period",
      icon: PieChart,
      comingSoon: true,
    },
    {
      id: "revenue-analysis",
      title: "Revenue Analysis",
      description: "Analyze revenue streams, client contributions, and growth trends",
      icon: TrendingUp,
      comingSoon: true,
    },
  ];

  // Report Card Component
  function ReportCard({ report }: { report: ReportType }) {
    const Icon = report.icon;
    const isDownloadingThis = isDownloading === report.id;

    const handleClick = () => {
      if (report.comingSoon) return;
      if (report.href) {
        router.push(report.href);
      }
    };

    const handleDownload = async (e: React.MouseEvent) => {
      e.stopPropagation();
      if (report.downloadAction) {
        await report.downloadAction();
      }
    };

    return (
      <Card
        className={`
          relative overflow-hidden transition-all
          ${report.comingSoon ? "opacity-70" : "hover:border-primary/50"}
          ${report.href && !report.comingSoon ? "cursor-pointer" : ""}
        `}
        onClick={handleClick}
      >
        {report.comingSoon && (
          <div className="absolute top-2 right-2">
            <span className="text-xs bg-muted px-2 py-1 rounded-full text-muted-foreground">
              Coming Soon
            </span>
          </div>
        )}
        <CardHeader>
          <div className="flex items-start gap-4">
            <div className="p-2 bg-primary/10 rounded-lg">
              <Icon className="h-6 w-6 text-primary" />
            </div>
            <div className="flex-1">
              <CardTitle className="text-lg flex items-center gap-2">
                {report.title}
                {!report.comingSoon && report.href && (
                  <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
                )}
              </CardTitle>
              <CardDescription className="mt-1">
                {report.description}
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        {!report.comingSoon && (
          <CardContent>
            {report.href ? (
              <Button variant="outline" className="w-full">
                View Report
              </Button>
            ) : report.downloadAction ? (
              <Button
                variant="outline"
                className="w-full"
                onClick={handleDownload}
                disabled={isDownloadingThis}
              >
                {isDownloadingThis ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <FileDown className="mr-2 h-4 w-4" />
                )}
                Download PDF
              </Button>
            ) : null}
          </CardContent>
        )}
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold font-heading">Reports</h1>
          <p className="text-muted-foreground">
            Generate financial reports and insights
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={dateRange} onValueChange={setDateRange}>
            <SelectTrigger className="w-[180px]">
              <Calendar className="mr-2 h-4 w-4" />
              <SelectValue placeholder="Select period" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="month">This Month</SelectItem>
              <SelectItem value="quarter">This Quarter</SelectItem>
              <SelectItem value="year">This Year</SelectItem>
              <SelectItem value="lastyear">Last Year</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={handleExportAll} disabled={isExporting}>
            {isExporting ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Download className="mr-2 h-4 w-4" />
            )}
            Export Transactions
          </Button>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Revenue</CardDescription>
            <CardTitle className="text-2xl text-green-600">
              {isLoadingStats ? (
                <Loader2 className="h-6 w-6 animate-spin" />
              ) : (
                formatCurrency(stats.totalRevenue)
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xs text-muted-foreground flex items-center gap-1">
              <TrendingUp className="h-3 w-3 text-green-500" />
              {getDateRangeLabel()}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Expenses</CardDescription>
            <CardTitle className="text-2xl text-red-600">
              {isLoadingStats ? (
                <Loader2 className="h-6 w-6 animate-spin" />
              ) : (
                formatCurrency(stats.totalExpenses)
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xs text-muted-foreground flex items-center gap-1">
              <TrendingUp className="h-3 w-3 text-red-500" />
              {getDateRangeLabel()}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Net Profit</CardDescription>
            <CardTitle className="text-2xl text-primary">
              {isLoadingStats ? (
                <Loader2 className="h-6 w-6 animate-spin" />
              ) : (
                formatCurrency(stats.netProfit)
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xs text-muted-foreground flex items-center gap-1">
              <TrendingUp className="h-3 w-3 text-green-500" />
              {getDateRangeLabel()}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Sankey Flow Chart */}
      <SankeyFlowChart
        startDate={getDateParams().start_date}
        endDate={getDateParams().end_date}
      />

      {/* Report Cards */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Available Reports</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {reportsList.map((report) => (
            <ReportCard key={report.id} report={report} />
          ))}
        </div>
      </div>
    </div>
  );
}
