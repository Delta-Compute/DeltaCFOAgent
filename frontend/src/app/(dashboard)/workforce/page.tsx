"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Users,
  Plus,
  RefreshCw,
  Search,
  User,
  Briefcase,
  MoreHorizontal,
  Eye,
  Edit,
  Trash2,
  FileText,
  DollarSign,
  CheckCircle2,
  Clock,
} from "lucide-react";
import { toast } from "sonner";

import {
  workforce,
  payslips as payslipsApi,
  type WorkforceMember,
  type Payslip,
} from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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

// Employment type badge
function EmploymentTypeBadge({ type }: { type: WorkforceMember["employment_type"] }) {
  return (
    <Badge variant={type === "employee" ? "default" : "secondary"} className="gap-1">
      {type === "employee" ? (
        <User className="h-3 w-3" />
      ) : (
        <Briefcase className="h-3 w-3" />
      )}
      {type === "employee" ? "Employee" : "Contractor"}
    </Badge>
  );
}

// Payslip status badge
function PayslipStatusBadge({ status }: { status: Payslip["status"] }) {
  const config: Record<Payslip["status"], { label: string; variant: "outline" | "secondary" | "default"; icon: typeof Edit }> = {
    draft: { label: "Draft", variant: "outline", icon: Edit },
    approved: { label: "Approved", variant: "secondary", icon: CheckCircle2 },
    paid: { label: "Paid", variant: "default", icon: CheckCircle2 },
  };

  const { label, variant, icon: Icon } = config[status];

  return (
    <Badge variant={variant} className="gap-1">
      <Icon className="h-3 w-3" />
      {label}
    </Badge>
  );
}

// Stats interface
interface WorkforceStats {
  totalMembers: number;
  employees: number;
  contractors: number;
  activeMembers: number;
}

interface PayslipStats {
  totalPayslips: number;
  draft: number;
  approved: number;
  paid: number;
  totalAmount: number;
}

export default function WorkforcePage() {
  const [activeTab, setActiveTab] = useState("members");

  // Members state
  const [members, setMembers] = useState<WorkforceMember[]>([]);
  const [memberStats, setMemberStats] = useState<WorkforceStats | null>(null);
  const [isMembersLoading, setIsMembersLoading] = useState(true);
  const [membersError, setMembersError] = useState<string | null>(null);
  const [membersPage, setMembersPage] = useState(1);
  const [membersTotal, setMembersTotal] = useState(0);
  const [membersSearch, setMembersSearch] = useState("");

  // Payslips state
  const [payslips, setPayslips] = useState<Payslip[]>([]);
  const [payslipStats, setPayslipStats] = useState<PayslipStats | null>(null);
  const [isPayslipsLoading, setIsPayslipsLoading] = useState(true);
  const [payslipsError, setPayslipsError] = useState<string | null>(null);
  const [payslipsPage, setPayslipsPage] = useState(1);
  const [payslipsTotal, setPayslipsTotal] = useState(0);
  const [payslipsSearch, setPayslipsSearch] = useState("");

  const pageSize = 20;

  // Load members
  const loadMembers = useCallback(async () => {
    setIsMembersLoading(true);
    setMembersError(null);

    try {
      const params: Record<string, string> = {
        page: String(membersPage),
        per_page: String(pageSize),
      };

      if (membersSearch) params.search = membersSearch;

      const result = await workforce.list(params);

      if (result.success && result.data) {
        setMembers(result.data.members);
        setMembersTotal(result.data.total);

        // Calculate stats
        const employees = result.data.members.filter((m) => m.employment_type === "employee").length;
        const contractors = result.data.members.filter((m) => m.employment_type === "contractor").length;
        const activeMembers = result.data.members.filter((m) => m.status === "active").length;

        setMemberStats({
          totalMembers: result.data.total,
          employees,
          contractors,
          activeMembers,
        });
      } else {
        throw new Error(result.error?.message || "Failed to load workforce members");
      }
    } catch (err) {
      console.error("Failed to load members:", err);
      setMembersError(err instanceof Error ? err.message : "Failed to load members");
    } finally {
      setIsMembersLoading(false);
    }
  }, [membersPage, membersSearch]);

  // Load payslips
  const loadPayslips = useCallback(async () => {
    setIsPayslipsLoading(true);
    setPayslipsError(null);

    try {
      const params: Record<string, string> = {
        page: String(payslipsPage),
        per_page: String(pageSize),
      };

      if (payslipsSearch) params.search = payslipsSearch;

      const result = await payslipsApi.list(params);

      if (result.success && result.data) {
        setPayslips(result.data.payslips);
        setPayslipsTotal(result.data.total);

        // Calculate stats
        const draft = result.data.payslips.filter((p) => p.status === "draft").length;
        const approved = result.data.payslips.filter((p) => p.status === "approved").length;
        const paid = result.data.payslips.filter((p) => p.status === "paid").length;
        const totalAmount = result.data.payslips.reduce((sum, p) => sum + p.net_amount, 0);

        setPayslipStats({
          totalPayslips: result.data.total,
          draft,
          approved,
          paid,
          totalAmount,
        });
      } else {
        throw new Error(result.error?.message || "Failed to load payslips");
      }
    } catch (err) {
      console.error("Failed to load payslips:", err);
      setPayslipsError(err instanceof Error ? err.message : "Failed to load payslips");
    } finally {
      setIsPayslipsLoading(false);
    }
  }, [payslipsPage, payslipsSearch]);

  // Load data based on active tab
  useEffect(() => {
    if (activeTab === "members") {
      loadMembers();
    } else {
      loadPayslips();
    }
  }, [activeTab, loadMembers, loadPayslips]);

  // Delete member
  async function handleDeleteMember(member: WorkforceMember) {
    if (!confirm(`Are you sure you want to delete ${member.full_name}?`)) {
      return;
    }

    try {
      const result = await workforce.delete(member.id);
      if (result.success) {
        toast.success("Member deleted");
        loadMembers();
      } else {
        toast.error(result.error?.message || "Failed to delete member");
      }
    } catch {
      toast.error("Failed to delete member");
    }
  }

  // Delete payslip
  async function handleDeletePayslip(payslip: Payslip) {
    if (!confirm(`Are you sure you want to delete payslip ${payslip.payslip_number}?`)) {
      return;
    }

    try {
      const result = await payslipsApi.delete(payslip.id);
      if (result.success) {
        toast.success("Payslip deleted");
        loadPayslips();
      } else {
        toast.error(result.error?.message || "Failed to delete payslip");
      }
    } catch {
      toast.error("Failed to delete payslip");
    }
  }

  // Members columns
  const memberColumns: Column<WorkforceMember>[] = [
    {
      key: "full_name",
      header: "Name",
      render: (item) => (
        <div>
          <div className="font-medium">{item.full_name}</div>
          <div className="text-xs text-muted-foreground">{item.email}</div>
        </div>
      ),
    },
    {
      key: "employment_type",
      header: "Type",
      width: "130px",
      render: (item) => <EmploymentTypeBadge type={item.employment_type} />,
    },
    {
      key: "job_title",
      header: "Position",
      render: (item) => (
        <div>
          <div className="font-medium">{item.job_title || "-"}</div>
          {item.department && (
            <div className="text-xs text-muted-foreground">{item.department}</div>
          )}
        </div>
      ),
    },
    {
      key: "date_of_hire",
      header: "Hire Date",
      width: "110px",
      render: (item) => (
        <span className="text-sm">{formatDate(item.date_of_hire)}</span>
      ),
    },
    {
      key: "pay_rate",
      header: "Pay Rate",
      align: "right",
      render: (item) => (
        <div className="text-right">
          <div className="font-medium">
            {formatCurrency(item.pay_rate, item.currency)}
          </div>
          <div className="text-xs text-muted-foreground">{item.pay_frequency}</div>
        </div>
      ),
    },
    {
      key: "status",
      header: "Status",
      width: "100px",
      render: (item) => (
        <Badge variant={item.status === "active" ? "default" : "outline"}>
          {item.status}
        </Badge>
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
              onClick={() => handleDeleteMember(item)}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  // Payslips columns
  const payslipColumns: Column<Payslip>[] = [
    {
      key: "payslip_number",
      header: "Payslip #",
      width: "120px",
      render: (item) => (
        <span className="font-medium font-mono">{item.payslip_number}</span>
      ),
    },
    {
      key: "workforce_member_name",
      header: "Employee",
      render: (item) => (
        <span className="font-medium">{item.workforce_member_name}</span>
      ),
    },
    {
      key: "pay_period",
      header: "Pay Period",
      render: (item) => (
        <span className="text-sm">
          {formatDate(item.pay_period_start)} - {formatDate(item.pay_period_end)}
        </span>
      ),
    },
    {
      key: "payment_date",
      header: "Payment Date",
      width: "110px",
      render: (item) => (
        <span className="text-sm">{formatDate(item.payment_date)}</span>
      ),
    },
    {
      key: "net_amount",
      header: "Net Amount",
      align: "right",
      render: (item) => (
        <div className="text-right">
          <div className="font-medium">
            {formatCurrency(item.net_amount, item.currency)}
          </div>
          <div className="text-xs text-muted-foreground">
            Gross: {formatCurrency(item.gross_amount, item.currency)}
          </div>
        </div>
      ),
    },
    {
      key: "status",
      header: "Status",
      width: "120px",
      render: (item) => <PayslipStatusBadge status={item.status} />,
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
            {item.status !== "paid" && (
              <DropdownMenuItem>
                <CheckCircle2 className="mr-2 h-4 w-4" />
                Mark as Paid
              </DropdownMenuItem>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="text-destructive"
              onClick={() => handleDeletePayslip(item)}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold font-heading">Workforce</h1>
          <p className="text-muted-foreground">
            Manage employees, contractors, and payroll
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={activeTab === "members" ? loadMembers : loadPayslips}
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            {activeTab === "members" ? "Add Member" : "Create Payslip"}
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="members" className="gap-2">
            <Users className="h-4 w-4" />
            Members
          </TabsTrigger>
          <TabsTrigger value="payslips" className="gap-2">
            <FileText className="h-4 w-4" />
            Payslips
          </TabsTrigger>
        </TabsList>

        {/* Members Tab */}
        <TabsContent value="members" className="space-y-6">
          {/* Stats */}
          <StatsGrid>
            <StatsCard
              title="Total Members"
              value={memberStats?.totalMembers.toLocaleString() || "0"}
              icon={Users}
              isLoading={isMembersLoading}
            />
            <StatsCard
              title="Employees"
              value={memberStats?.employees.toLocaleString() || "0"}
              icon={User}
              isLoading={isMembersLoading}
            />
            <StatsCard
              title="Contractors"
              value={memberStats?.contractors.toLocaleString() || "0"}
              icon={Briefcase}
              isLoading={isMembersLoading}
            />
            <StatsCard
              title="Active"
              value={memberStats?.activeMembers.toLocaleString() || "0"}
              icon={CheckCircle2}
              isLoading={isMembersLoading}
            />
          </StatsGrid>

          {/* Search */}
          <Card>
            <CardContent className="pt-6">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search members..."
                  value={membersSearch}
                  onChange={(e) => setMembersSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </CardContent>
          </Card>

          {/* Table */}
          {membersError ? (
            <ErrorState title={membersError} onRetry={loadMembers} />
          ) : (
            <DataTable
              columns={memberColumns}
              data={members}
              keyField="id"
              isLoading={isMembersLoading}
              page={membersPage}
              pageSize={pageSize}
              totalItems={membersTotal}
              onPageChange={setMembersPage}
              emptyMessage="No workforce members found"
            />
          )}
        </TabsContent>

        {/* Payslips Tab */}
        <TabsContent value="payslips" className="space-y-6">
          {/* Stats */}
          <StatsGrid>
            <StatsCard
              title="Total Payslips"
              value={payslipStats?.totalPayslips.toLocaleString() || "0"}
              icon={FileText}
              isLoading={isPayslipsLoading}
            />
            <StatsCard
              title="Draft"
              value={payslipStats?.draft.toLocaleString() || "0"}
              icon={Edit}
              isLoading={isPayslipsLoading}
            />
            <StatsCard
              title="Pending Payment"
              value={payslipStats?.approved.toLocaleString() || "0"}
              icon={Clock}
              isLoading={isPayslipsLoading}
            />
            <StatsCard
              title="Total Paid"
              value={formatCurrency(payslipStats?.totalAmount || 0)}
              icon={DollarSign}
              isLoading={isPayslipsLoading}
            />
          </StatsGrid>

          {/* Search */}
          <Card>
            <CardContent className="pt-6">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search payslips..."
                  value={payslipsSearch}
                  onChange={(e) => setPayslipsSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </CardContent>
          </Card>

          {/* Table */}
          {payslipsError ? (
            <ErrorState title={payslipsError} onRetry={loadPayslips} />
          ) : (
            <DataTable
              columns={payslipColumns}
              data={payslips}
              keyField="id"
              isLoading={isPayslipsLoading}
              page={payslipsPage}
              pageSize={pageSize}
              totalItems={payslipsTotal}
              onPageChange={setPayslipsPage}
              emptyMessage="No payslips found"
            />
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
