"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  TrendingUp,
  Download,
  Calendar,
  RefreshCw,
  DollarSign,
  ArrowUpRight,
  ArrowDownRight,
} from "lucide-react";

import { transactions, type Transaction } from "@/lib/api";
import { formatCurrency, cn } from "@/lib/utils";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ErrorState, LoadingState } from "@/components/ui/empty-state";

// Period type
type Period = "month" | "quarter" | "year";

// Monthly data structure
interface MonthlyData {
  month: string;
  revenue: number;
  expenses: number;
  netIncome: number;
}

// Category breakdown
interface CategoryData {
  category: string;
  amount: number;
  percentage: number;
  trend: number;
}

// Helper to get month name
function getMonthName(date: Date): string {
  return date.toLocaleDateString("en-US", { month: "short", year: "numeric" });
}

// Helper to calculate period dates
function getPeriodDates(period: Period): { start: Date; end: Date } {
  const end = new Date();
  const start = new Date();

  switch (period) {
    case "month":
      start.setMonth(start.getMonth() - 1);
      break;
    case "quarter":
      start.setMonth(start.getMonth() - 3);
      break;
    case "year":
      start.setFullYear(start.getFullYear() - 1);
      break;
  }

  return { start, end };
}

// Simple bar chart component
function SimpleBarChart({
  data,
  currency,
}: {
  data: MonthlyData[];
  currency: string;
}) {
  const maxValue = Math.max(
    ...data.flatMap((d) => [Math.abs(d.revenue), Math.abs(d.expenses)])
  );

  return (
    <div className="space-y-4">
      {data.map((item, index) => (
        <div key={index} className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="font-medium">{item.month}</span>
            <span
              className={cn(
                "font-medium",
                item.netIncome >= 0 ? "text-green-600" : "text-red-600"
              )}
            >
              {formatCurrency(item.netIncome, currency)}
            </span>
          </div>
          <div className="space-y-1">
            {/* Revenue bar */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground w-16">Revenue</span>
              <div className="flex-1 h-4 bg-muted rounded overflow-hidden">
                <div
                  className="h-full bg-green-500 rounded"
                  style={{
                    width: `${(item.revenue / maxValue) * 100}%`,
                  }}
                />
              </div>
              <span className="text-xs w-20 text-right">
                {formatCurrency(item.revenue, currency)}
              </span>
            </div>
            {/* Expenses bar */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground w-16">Expenses</span>
              <div className="flex-1 h-4 bg-muted rounded overflow-hidden">
                <div
                  className="h-full bg-red-500 rounded"
                  style={{
                    width: `${(item.expenses / maxValue) * 100}%`,
                  }}
                />
              </div>
              <span className="text-xs w-20 text-right">
                {formatCurrency(item.expenses, currency)}
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function PLTrendReportPage() {
  // State
  const [txData, setTxData] = useState<Transaction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState<Period>("year");
  const currency = "USD"; // Default currency

  // Load transactions
  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const { start, end } = getPeriodDates(period);
      const result = await transactions.list({
        start_date: start.toISOString().split("T")[0],
        end_date: end.toISOString().split("T")[0],
        per_page: "1000", // Get all for analysis
      });

      if (result.success && result.data) {
        setTxData(result.data.transactions);
      } else {
        throw new Error(result.error?.message || "Failed to load data");
      }
    } catch (err) {
      console.error("Failed to load P&L data:", err);
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setIsLoading(false);
    }
  }, [period]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Calculate P&L data from transactions
  const plData = useMemo(() => {
    // Group by month
    const monthlyMap = new Map<string, { revenue: number; expenses: number }>();

    txData.forEach((tx) => {
      const date = new Date(tx.date);
      const monthKey = getMonthName(date);

      if (!monthlyMap.has(monthKey)) {
        monthlyMap.set(monthKey, { revenue: 0, expenses: 0 });
      }

      const monthData = monthlyMap.get(monthKey)!;
      if (tx.amount > 0) {
        monthData.revenue += tx.amount;
      } else {
        monthData.expenses += Math.abs(tx.amount);
      }
    });

    // Convert to array and sort by date
    const monthlyData: MonthlyData[] = Array.from(monthlyMap.entries())
      .map(([month, data]) => ({
        month,
        revenue: data.revenue,
        expenses: data.expenses,
        netIncome: data.revenue - data.expenses,
      }))
      .sort((a, b) => {
        const dateA = new Date(a.month);
        const dateB = new Date(b.month);
        return dateA.getTime() - dateB.getTime();
      })
      .slice(-12); // Last 12 months max

    return monthlyData;
  }, [txData]);

  // Calculate totals
  const totals = useMemo(() => {
    const revenue = plData.reduce((sum, d) => sum + d.revenue, 0);
    const expenses = plData.reduce((sum, d) => sum + d.expenses, 0);
    const netIncome = revenue - expenses;
    const profitMargin = revenue > 0 ? (netIncome / revenue) * 100 : 0;

    // Calculate trends (compare first and last half)
    const halfIndex = Math.floor(plData.length / 2);
    const firstHalf = plData.slice(0, halfIndex);
    const secondHalf = plData.slice(halfIndex);

    const firstHalfRevenue = firstHalf.reduce((sum, d) => sum + d.revenue, 0);
    const secondHalfRevenue = secondHalf.reduce((sum, d) => sum + d.revenue, 0);
    const revenueTrend =
      firstHalfRevenue > 0
        ? ((secondHalfRevenue - firstHalfRevenue) / firstHalfRevenue) * 100
        : 0;

    const firstHalfExpenses = firstHalf.reduce((sum, d) => sum + d.expenses, 0);
    const secondHalfExpenses = secondHalf.reduce((sum, d) => sum + d.expenses, 0);
    const expensesTrend =
      firstHalfExpenses > 0
        ? ((secondHalfExpenses - firstHalfExpenses) / firstHalfExpenses) * 100
        : 0;

    return {
      revenue,
      expenses,
      netIncome,
      profitMargin,
      revenueTrend,
      expensesTrend,
    };
  }, [plData]);

  // Calculate category breakdown
  const categoryBreakdown = useMemo(() => {
    const categoryMap = new Map<string, number>();

    txData.forEach((tx) => {
      const category = tx.category || "Uncategorized";
      const current = categoryMap.get(category) || 0;
      categoryMap.set(category, current + Math.abs(tx.amount));
    });

    const totalAmount = Array.from(categoryMap.values()).reduce(
      (sum, val) => sum + val,
      0
    );

    const categories: CategoryData[] = Array.from(categoryMap.entries())
      .map(([category, amount]) => ({
        category,
        amount,
        percentage: totalAmount > 0 ? (amount / totalAmount) * 100 : 0,
        trend: 0, // Would need historical data for trend
      }))
      .sort((a, b) => b.amount - a.amount)
      .slice(0, 10);

    return categories;
  }, [txData]);

  if (isLoading) {
    return <LoadingState message="Loading P&L data..." />;
  }

  if (error) {
    return (
      <ErrorState
        title="Failed to load report"
        description={error}
        onRetry={loadData}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/reports">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-bold font-heading">
              Profit & Loss Trend
            </h1>
            <p className="text-muted-foreground">
              Income, expenses, and net profit analysis
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 ml-12 md:ml-0">
          <Select
            value={period}
            onValueChange={(value) => setPeriod(value as Period)}
          >
            <SelectTrigger className="w-[150px]">
              <Calendar className="mr-2 h-4 w-4" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="month">Last Month</SelectItem>
              <SelectItem value="quarter">Last Quarter</SelectItem>
              <SelectItem value="year">Last Year</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={loadData}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <Button variant="outline" size="sm">
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Revenue</CardDescription>
            <CardTitle className="text-2xl text-green-600">
              {formatCurrency(totals.revenue, currency)}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div
              className={cn(
                "text-xs flex items-center gap-1",
                totals.revenueTrend >= 0 ? "text-green-600" : "text-red-600"
              )}
            >
              {totals.revenueTrend >= 0 ? (
                <ArrowUpRight className="h-3 w-3" />
              ) : (
                <ArrowDownRight className="h-3 w-3" />
              )}
              {Math.abs(totals.revenueTrend).toFixed(1)}% vs prev period
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Expenses</CardDescription>
            <CardTitle className="text-2xl text-red-600">
              {formatCurrency(totals.expenses, currency)}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div
              className={cn(
                "text-xs flex items-center gap-1",
                totals.expensesTrend <= 0 ? "text-green-600" : "text-red-600"
              )}
            >
              {totals.expensesTrend >= 0 ? (
                <ArrowUpRight className="h-3 w-3" />
              ) : (
                <ArrowDownRight className="h-3 w-3" />
              )}
              {Math.abs(totals.expensesTrend).toFixed(1)}% vs prev period
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Net Income</CardDescription>
            <CardTitle
              className={cn(
                "text-2xl",
                totals.netIncome >= 0 ? "text-green-600" : "text-red-600"
              )}
            >
              {formatCurrency(totals.netIncome, currency)}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xs text-muted-foreground">
              {totals.netIncome >= 0 ? "Profit" : "Loss"}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Profit Margin</CardDescription>
            <CardTitle
              className={cn(
                "text-2xl",
                totals.profitMargin >= 0 ? "text-green-600" : "text-red-600"
              )}
            >
              {totals.profitMargin.toFixed(1)}%
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xs text-muted-foreground">
              Net income / Revenue
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Monthly Trend Chart */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Monthly Trend
            </CardTitle>
            <CardDescription>
              Revenue vs expenses over time
            </CardDescription>
          </CardHeader>
          <CardContent>
            {plData.length > 0 ? (
              <SimpleBarChart data={plData} currency={currency} />
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                No data available for the selected period
              </div>
            )}
          </CardContent>
        </Card>

        {/* Category Breakdown */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="h-5 w-5" />
              Category Breakdown
            </CardTitle>
            <CardDescription>Top categories by amount</CardDescription>
          </CardHeader>
          <CardContent>
            {categoryBreakdown.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Category</TableHead>
                    <TableHead className="text-right">Amount</TableHead>
                    <TableHead className="text-right w-[80px]">%</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {categoryBreakdown.map((cat) => (
                    <TableRow key={cat.category}>
                      <TableCell className="font-medium">
                        {cat.category}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatCurrency(cat.amount, currency)}
                      </TableCell>
                      <TableCell className="text-right">
                        {cat.percentage.toFixed(1)}%
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                No categories found
              </div>
            )}
          </CardContent>
        </Card>

        {/* Monthly Detail Table */}
        <Card>
          <CardHeader>
            <CardTitle>Monthly Detail</CardTitle>
            <CardDescription>Detailed breakdown by month</CardDescription>
          </CardHeader>
          <CardContent>
            {plData.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Month</TableHead>
                    <TableHead className="text-right">Revenue</TableHead>
                    <TableHead className="text-right">Expenses</TableHead>
                    <TableHead className="text-right">Net</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {plData.map((item) => (
                    <TableRow key={item.month}>
                      <TableCell className="font-medium">{item.month}</TableCell>
                      <TableCell className="text-right text-green-600">
                        {formatCurrency(item.revenue, currency)}
                      </TableCell>
                      <TableCell className="text-right text-red-600">
                        {formatCurrency(item.expenses, currency)}
                      </TableCell>
                      <TableCell
                        className={cn(
                          "text-right font-medium",
                          item.netIncome >= 0 ? "text-green-600" : "text-red-600"
                        )}
                      >
                        {formatCurrency(item.netIncome, currency)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                No data available
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
