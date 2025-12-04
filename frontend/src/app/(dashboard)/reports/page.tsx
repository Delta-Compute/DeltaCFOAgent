"use client";

import { useState } from "react";
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
} from "lucide-react";

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

// Report types
interface ReportType {
  id: string;
  title: string;
  description: string;
  icon: typeof BarChart3;
  href?: string;
  comingSoon?: boolean;
}

const reports: ReportType[] = [
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
    comingSoon: true,
  },
  {
    id: "cash-flow",
    title: "Cash Flow Statement",
    description: "Track the movement of cash in and out of your business",
    icon: DollarSign,
    comingSoon: true,
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
  {
    id: "tax-summary",
    title: "Tax Summary Report",
    description: "Overview of tax-related transactions and deductions for filing purposes",
    icon: FileText,
    comingSoon: true,
  },
];

// Report Card Component
function ReportCard({ report }: { report: ReportType }) {
  const router = useRouter();
  const Icon = report.icon;

  return (
    <Card
      className={`
        relative overflow-hidden transition-all
        ${report.comingSoon ? "opacity-70" : "hover:border-primary/50 cursor-pointer"}
      `}
      onClick={() => !report.comingSoon && report.href && router.push(report.href)}
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
              {!report.comingSoon && (
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
          <Button variant="outline" className="w-full">
            View Report
          </Button>
        </CardContent>
      )}
    </Card>
  );
}

export default function ReportsPage() {
  const [dateRange, setDateRange] = useState("year");

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
              <SelectItem value="custom">Custom Range</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Export All
          </Button>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Revenue (YTD)</CardDescription>
            <CardTitle className="text-2xl text-green-600">$1,234,567</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xs text-muted-foreground flex items-center gap-1">
              <TrendingUp className="h-3 w-3 text-green-500" />
              +12.5% from last year
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Expenses (YTD)</CardDescription>
            <CardTitle className="text-2xl text-red-600">$876,543</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xs text-muted-foreground flex items-center gap-1">
              <TrendingUp className="h-3 w-3 text-red-500" />
              +8.3% from last year
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Net Profit (YTD)</CardDescription>
            <CardTitle className="text-2xl text-primary">$358,024</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xs text-muted-foreground flex items-center gap-1">
              <TrendingUp className="h-3 w-3 text-green-500" />
              +25.2% from last year
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Report Cards */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Available Reports</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {reports.map((report) => (
            <ReportCard key={report.id} report={report} />
          ))}
        </div>
      </div>
    </div>
  );
}
