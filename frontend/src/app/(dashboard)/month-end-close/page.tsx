"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Calendar,
  CheckCircle2,
  Clock,
  AlertCircle,
  Lock,
  Unlock,
  Send,
  ThumbsUp,
  ThumbsDown,
  XCircle,
  Play,
  Plus,
  RefreshCw,
  FileText,
  Receipt,
  CreditCard,
  AlertTriangle,
  ChevronDown,
  Loader2,
  History,
  SkipForward,
} from "lucide-react";
import { toast } from "sonner";

import {
  monthEndClose,
  type AccountingPeriod,
  type ChecklistItem,
  type ReconciliationStatus,
  type AdjustingEntry,
  type EntriesSummary,
  type ActivityLogEntry,
  type PeriodStatus,
  type ChecklistItemStatus,
  type HealthStatus,
} from "@/lib/api";
import { formatCurrency, formatDate, cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { LoadingState } from "@/components/ui/empty-state";

// Status badge component
function PeriodStatusBadge({ status }: { status: PeriodStatus }) {
  const config: Record<
    PeriodStatus,
    { label: string; variant: "outline" | "secondary" | "default" | "destructive"; icon: typeof Clock }
  > = {
    open: { label: "Open", variant: "outline", icon: Clock },
    in_progress: { label: "In Progress", variant: "secondary", icon: Play },
    pending_approval: { label: "Pending Approval", variant: "secondary", icon: Send },
    locked: { label: "Locked", variant: "default", icon: Lock },
    closed: { label: "Closed", variant: "default", icon: CheckCircle2 },
  };

  const statusConfig = config[status] || config.open;
  const { label, variant, icon: Icon } = statusConfig;

  return (
    <Badge variant={variant} className="gap-1">
      <Icon className="h-3 w-3" />
      {label}
    </Badge>
  );
}

// Health status badge
function HealthBadge({ health }: { health: HealthStatus }) {
  const config: Record<HealthStatus, { label: string; color: string }> = {
    excellent: { label: "Excellent", color: "bg-green-100 text-green-800" },
    good: { label: "Good", color: "bg-blue-100 text-blue-800" },
    warning: { label: "Warning", color: "bg-yellow-100 text-yellow-800" },
    critical: { label: "Critical", color: "bg-red-100 text-red-800" },
  };

  const { label, color } = config[health] || config.warning;

  return <span className={cn("px-2 py-1 rounded-full text-xs font-medium", color)}>{label}</span>;
}

// Checklist item status icon
function ChecklistStatusIcon({ status }: { status: ChecklistItemStatus }) {
  switch (status) {
    case "completed":
      return <CheckCircle2 className="h-5 w-5 text-green-500" />;
    case "skipped":
      return <SkipForward className="h-5 w-5 text-gray-400" />;
    case "blocked":
      return <AlertCircle className="h-5 w-5 text-red-500" />;
    case "in_progress":
      return <Clock className="h-5 w-5 text-blue-500" />;
    default:
      return <div className="h-5 w-5 rounded-full border-2 border-gray-300" />;
  }
}

// Reconciliation card component
function ReconciliationCard({
  title,
  icon: Icon,
  matched,
  total,
  percentage,
  passed,
  onViewUnmatched,
}: {
  title: string;
  icon: typeof FileText;
  matched: number;
  total: number;
  percentage: number;
  passed: boolean;
  onViewUnmatched: () => void;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Icon className="h-4 w-4" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Match Rate</span>
            <span className={cn("font-medium", passed ? "text-green-600" : "text-orange-600")}>
              {percentage.toFixed(1)}%
            </span>
          </div>
          <Progress value={percentage} className={cn("h-2", !passed && "bg-orange-100")} />
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>{matched} matched</span>
            <span>{total - matched} unmatched</span>
          </div>
          {total - matched > 0 && (
            <Button variant="link" size="sm" className="p-0 h-auto" onClick={onViewUnmatched}>
              View unmatched items
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default function MonthEndClosePage() {
  // State
  const [periods, setPeriods] = useState<AccountingPeriod[]>([]);
  const [selectedPeriod, setSelectedPeriod] = useState<AccountingPeriod | null>(null);
  const [checklist, setChecklist] = useState<ChecklistItem[]>([]);
  const [reconciliation, setReconciliation] = useState<ReconciliationStatus | null>(null);
  const [entriesSummary, setEntriesSummary] = useState<EntriesSummary | null>(null);
  const [activityLog, setActivityLog] = useState<ActivityLogEntry[]>([]);

  // Loading states
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingPeriod, setIsLoadingPeriod] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  // Dialogs
  const [showCreatePeriodDialog, setShowCreatePeriodDialog] = useState(false);
  const [showUnlockDialog, setShowUnlockDialog] = useState(false);
  const [showRejectDialog, setShowRejectDialog] = useState(false);
  const [showSkipDialog, setShowSkipDialog] = useState(false);
  const [showActivityLogDialog, setShowActivityLogDialog] = useState(false);
  const [skipItemId, setSkipItemId] = useState<string | null>(null);

  // Form state
  const [newPeriod, setNewPeriod] = useState<{
    period_name: string;
    period_type: "monthly" | "quarterly" | "annual";
    start_date: string;
    end_date: string;
    notes: string;
  }>({
    period_name: "",
    period_type: "monthly",
    start_date: "",
    end_date: "",
    notes: "",
  });
  const [unlockReason, setUnlockReason] = useState("");
  const [rejectReason, setRejectReason] = useState("");
  const [skipReason, setSkipReason] = useState("");

  // Load periods
  const loadPeriods = useCallback(async () => {
    try {
      const result = await monthEndClose.listPeriods({ per_page: "50" });
      if (result.success && result.data) {
        setPeriods(result.data.periods);
        // Select first period if none selected
        if (result.data.periods.length > 0 && !selectedPeriod) {
          loadPeriod(result.data.periods[0].id);
        }
      }
    } catch (err) {
      console.error("Failed to load periods:", err);
    } finally {
      setIsLoading(false);
    }
  }, [selectedPeriod]);

  // Load single period with all related data
  const loadPeriod = useCallback(async (periodId: string) => {
    setIsLoadingPeriod(true);
    try {
      const [periodResult, checklistResult, reconciliationResult, summaryResult] = await Promise.all([
        monthEndClose.getPeriod(periodId),
        monthEndClose.getChecklist(periodId),
        monthEndClose.getReconciliationStatus(periodId),
        monthEndClose.getEntriesSummary(periodId),
      ]);

      if (periodResult.success && periodResult.data) {
        setSelectedPeriod(periodResult.data);
      }
      if (checklistResult.success && checklistResult.data) {
        setChecklist(checklistResult.data);
      }
      if (reconciliationResult.success && reconciliationResult.data) {
        setReconciliation(reconciliationResult.data);
      }
      if (summaryResult.success && summaryResult.data) {
        setEntriesSummary(summaryResult.data);
      }
    } catch (err) {
      console.error("Failed to load period:", err);
      toast.error("Failed to load period data");
    } finally {
      setIsLoadingPeriod(false);
    }
  }, []);

  useEffect(() => {
    loadPeriods();
  }, [loadPeriods]);

  // Workflow actions
  async function handleStartClose() {
    if (!selectedPeriod) return;
    setIsProcessing(true);
    try {
      const result = await monthEndClose.startCloseProcess(selectedPeriod.id);
      if (result.success) {
        toast.success("Close process started");
        loadPeriod(selectedPeriod.id);
      } else {
        toast.error(result.error?.message || "Failed to start close process");
      }
    } catch {
      toast.error("Failed to start close process");
    } finally {
      setIsProcessing(false);
    }
  }

  async function handleLockPeriod() {
    if (!selectedPeriod) return;
    setIsProcessing(true);
    try {
      const result = await monthEndClose.lockPeriod(selectedPeriod.id);
      if (result.success) {
        toast.success("Period locked");
        loadPeriod(selectedPeriod.id);
      } else {
        toast.error(result.error?.message || "Failed to lock period");
      }
    } catch {
      toast.error("Failed to lock period");
    } finally {
      setIsProcessing(false);
    }
  }

  async function handleUnlockPeriod() {
    if (!selectedPeriod || !unlockReason.trim()) return;
    setIsProcessing(true);
    try {
      const result = await monthEndClose.unlockPeriod(selectedPeriod.id, unlockReason);
      if (result.success) {
        toast.success("Period unlocked");
        setShowUnlockDialog(false);
        setUnlockReason("");
        loadPeriod(selectedPeriod.id);
      } else {
        toast.error(result.error?.message || "Failed to unlock period");
      }
    } catch {
      toast.error("Failed to unlock period");
    } finally {
      setIsProcessing(false);
    }
  }

  async function handleSubmitForApproval() {
    if (!selectedPeriod) return;
    setIsProcessing(true);
    try {
      const result = await monthEndClose.submitForApproval(selectedPeriod.id);
      if (result.success) {
        toast.success("Submitted for approval");
        loadPeriod(selectedPeriod.id);
      } else {
        toast.error(result.error?.message || "Failed to submit for approval");
      }
    } catch {
      toast.error("Failed to submit for approval");
    } finally {
      setIsProcessing(false);
    }
  }

  async function handleApprovePeriod() {
    if (!selectedPeriod) return;
    setIsProcessing(true);
    try {
      const result = await monthEndClose.approvePeriod(selectedPeriod.id);
      if (result.success) {
        toast.success("Period approved");
        loadPeriod(selectedPeriod.id);
      } else {
        toast.error(result.error?.message || "Failed to approve period");
      }
    } catch {
      toast.error("Failed to approve period");
    } finally {
      setIsProcessing(false);
    }
  }

  async function handleRejectPeriod() {
    if (!selectedPeriod || !rejectReason.trim()) return;
    setIsProcessing(true);
    try {
      const result = await monthEndClose.rejectPeriod(selectedPeriod.id, rejectReason);
      if (result.success) {
        toast.success("Period rejected");
        setShowRejectDialog(false);
        setRejectReason("");
        loadPeriod(selectedPeriod.id);
      } else {
        toast.error(result.error?.message || "Failed to reject period");
      }
    } catch {
      toast.error("Failed to reject period");
    } finally {
      setIsProcessing(false);
    }
  }

  async function handleClosePeriod() {
    if (!selectedPeriod) return;
    setIsProcessing(true);
    try {
      const result = await monthEndClose.closePeriod(selectedPeriod.id);
      if (result.success) {
        toast.success("Period closed successfully");
        loadPeriod(selectedPeriod.id);
        loadPeriods();
      } else {
        toast.error(result.error?.message || "Failed to close period");
      }
    } catch {
      toast.error("Failed to close period");
    } finally {
      setIsProcessing(false);
    }
  }

  // Checklist actions
  async function handleCompleteItem(itemId: string) {
    setIsProcessing(true);
    try {
      const result = await monthEndClose.completeChecklistItem(itemId);
      if (result.success && selectedPeriod) {
        toast.success("Item completed");
        loadPeriod(selectedPeriod.id);
      } else {
        toast.error(result.error?.message || "Failed to complete item");
      }
    } catch {
      toast.error("Failed to complete item");
    } finally {
      setIsProcessing(false);
    }
  }

  async function handleSkipItem() {
    if (!skipItemId || !skipReason.trim()) return;
    setIsProcessing(true);
    try {
      const result = await monthEndClose.skipChecklistItem(skipItemId, skipReason);
      if (result.success && selectedPeriod) {
        toast.success("Item skipped");
        setShowSkipDialog(false);
        setSkipItemId(null);
        setSkipReason("");
        loadPeriod(selectedPeriod.id);
      } else {
        toast.error(result.error?.message || "Failed to skip item");
      }
    } catch {
      toast.error("Failed to skip item");
    } finally {
      setIsProcessing(false);
    }
  }

  async function handleRunAutoChecks() {
    if (!selectedPeriod) return;
    setIsProcessing(true);
    try {
      const result = await monthEndClose.runAllAutoChecks(selectedPeriod.id);
      if (result.success) {
        toast.success("Auto-checks completed");
        loadPeriod(selectedPeriod.id);
      } else {
        toast.error(result.error?.message || "Failed to run auto-checks");
      }
    } catch {
      toast.error("Failed to run auto-checks");
    } finally {
      setIsProcessing(false);
    }
  }

  // Create period
  async function handleCreatePeriod() {
    if (!newPeriod.period_name || !newPeriod.start_date || !newPeriod.end_date) {
      toast.error("Please fill in all required fields");
      return;
    }
    setIsProcessing(true);
    try {
      const result = await monthEndClose.createPeriod(newPeriod);
      if (result.success && result.data) {
        toast.success("Period created");
        setShowCreatePeriodDialog(false);
        setNewPeriod({
          period_name: "",
          period_type: "monthly",
          start_date: "",
          end_date: "",
          notes: "",
        });
        loadPeriods();
        loadPeriod(result.data.id);
      } else {
        toast.error(result.error?.message || "Failed to create period");
      }
    } catch {
      toast.error("Failed to create period");
    } finally {
      setIsProcessing(false);
    }
  }

  // Load activity log
  async function handleViewActivityLog() {
    if (!selectedPeriod) return;
    try {
      const result = await monthEndClose.getActivityLog(selectedPeriod.id, { per_page: "50" });
      if (result.success && result.data) {
        setActivityLog(result.data.entries);
        setShowActivityLogDialog(true);
      }
    } catch {
      toast.error("Failed to load activity log");
    }
  }

  // Group checklist items by category
  const checklistByCategory = checklist.reduce((acc, item) => {
    if (!acc[item.category]) {
      acc[item.category] = [];
    }
    acc[item.category].push(item);
    return acc;
  }, {} as Record<string, ChecklistItem[]>);

  // Calculate progress
  const completedItems = checklist.filter((i) => i.status === "completed" || i.status === "skipped").length;
  const totalItems = checklist.length;
  const progressPercent = totalItems > 0 ? (completedItems / totalItems) * 100 : 0;

  if (isLoading) {
    return <LoadingState message="Loading periods..." />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold font-heading">Month-End Close</h1>
          <p className="text-muted-foreground">Manage accounting period closings</p>
        </div>
        <div className="flex items-center gap-3">
          <Select
            value={selectedPeriod?.id || ""}
            onValueChange={(value) => loadPeriod(value)}
          >
            <SelectTrigger className="w-[250px]">
              <SelectValue placeholder="Select period" />
            </SelectTrigger>
            <SelectContent>
              {periods.map((period) => (
                <SelectItem key={period.id} value={period.id}>
                  {period.period_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={() => setShowCreatePeriodDialog(true)}>
            <Plus className="mr-2 h-4 w-4" />
            New Period
          </Button>
        </div>
      </div>

      {selectedPeriod ? (
        isLoadingPeriod ? (
          <LoadingState message="Loading period data..." />
        ) : (
          <>
            {/* Period Info & Progress */}
            <Card>
              <CardContent className="pt-6">
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-3">
                      <h2 className="text-xl font-semibold">{selectedPeriod.period_name}</h2>
                      <PeriodStatusBadge status={selectedPeriod.status} />
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {formatDate(selectedPeriod.start_date)} - {formatDate(selectedPeriod.end_date)}
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className="text-2xl font-bold">{progressPercent.toFixed(0)}%</p>
                      <p className="text-xs text-muted-foreground">
                        {completedItems} of {totalItems} tasks
                      </p>
                    </div>
                    <div className="w-32">
                      <Progress value={progressPercent} className="h-3" />
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Quick Stats */}
            <div className="grid gap-4 md:grid-cols-4">
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-green-100 rounded-full">
                      <CheckCircle2 className="h-5 w-5 text-green-600" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold">
                        {checklist.filter((i) => i.status === "completed").length}
                      </p>
                      <p className="text-xs text-muted-foreground">Completed</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-yellow-100 rounded-full">
                      <Clock className="h-5 w-5 text-yellow-600" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold">
                        {checklist.filter((i) => i.status === "pending" || i.status === "in_progress").length}
                      </p>
                      <p className="text-xs text-muted-foreground">Pending</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-red-100 rounded-full">
                      <AlertCircle className="h-5 w-5 text-red-600" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold">
                        {checklist.filter((i) => i.status === "blocked").length}
                      </p>
                      <p className="text-xs text-muted-foreground">Blocked</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-gray-100 rounded-full">
                      <SkipForward className="h-5 w-5 text-gray-600" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold">
                        {checklist.filter((i) => i.status === "skipped").length}
                      </p>
                      <p className="text-xs text-muted-foreground">Skipped</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Reconciliation Status */}
            {reconciliation && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <h3 className="text-lg font-semibold">Reconciliation Status</h3>
                    <HealthBadge health={reconciliation.overall_health} />
                  </div>
                  <Button variant="outline" size="sm" onClick={handleRunAutoChecks} disabled={isProcessing}>
                    <RefreshCw className={cn("mr-2 h-4 w-4", isProcessing && "animate-spin")} />
                    Run Auto-Checks
                  </Button>
                </div>
                <div className="grid gap-4 md:grid-cols-3">
                  <ReconciliationCard
                    title="Invoice Matching"
                    icon={FileText}
                    matched={reconciliation.invoice_stats.matched}
                    total={reconciliation.invoice_stats.total}
                    percentage={reconciliation.invoice_stats.match_percentage}
                    passed={reconciliation.invoice_stats.passed}
                    onViewUnmatched={() => {}}
                  />
                  <ReconciliationCard
                    title="Payroll Matching"
                    icon={Receipt}
                    matched={reconciliation.payslip_stats.matched}
                    total={reconciliation.payslip_stats.total}
                    percentage={reconciliation.payslip_stats.match_percentage}
                    passed={reconciliation.payslip_stats.passed}
                    onViewUnmatched={() => {}}
                  />
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <CreditCard className="h-4 w-4" />
                        Transaction Classification
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-muted-foreground">Classification Rate</span>
                          <span
                            className={cn(
                              "font-medium",
                              reconciliation.transaction_stats.passed ? "text-green-600" : "text-orange-600"
                            )}
                          >
                            {reconciliation.transaction_stats.classification_percentage.toFixed(1)}%
                          </span>
                        </div>
                        <Progress
                          value={reconciliation.transaction_stats.classification_percentage}
                          className="h-2"
                        />
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                          <span>{reconciliation.transaction_stats.classified} classified</span>
                          <span>{reconciliation.transaction_stats.needs_review} need review</span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </div>
            )}

            {/* Checklist */}
            <Card>
              <CardHeader>
                <CardTitle>Close Checklist</CardTitle>
                <CardDescription>Complete all required tasks to close the period</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {Object.entries(checklistByCategory).map(([category, items]) => (
                    <div key={category} className="space-y-3">
                      <h4 className="font-medium text-sm text-muted-foreground uppercase tracking-wider">
                        {category}
                      </h4>
                      <div className="space-y-2">
                        {items.map((item) => (
                          <div
                            key={item.id}
                            className={cn(
                              "flex items-start gap-3 p-3 rounded-lg border",
                              item.status === "completed" && "bg-green-50 border-green-200",
                              item.status === "skipped" && "bg-gray-50 border-gray-200",
                              item.status === "blocked" && "bg-red-50 border-red-200"
                            )}
                          >
                            <ChecklistStatusIcon status={item.status} />
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <p className="font-medium">{item.name}</p>
                                {item.is_required && (
                                  <Badge variant="outline" className="text-xs">
                                    Required
                                  </Badge>
                                )}
                              </div>
                              {item.description && (
                                <p className="text-sm text-muted-foreground mt-1">{item.description}</p>
                              )}
                              {item.auto_check_result && (
                                <div
                                  className={cn(
                                    "text-xs mt-2 p-2 rounded",
                                    item.auto_check_result.passed ? "bg-green-100" : "bg-yellow-100"
                                  )}
                                >
                                  {item.auto_check_result.message}
                                </div>
                              )}
                              {item.skip_reason && (
                                <p className="text-xs text-muted-foreground mt-1">
                                  Skipped: {item.skip_reason}
                                </p>
                              )}
                              {item.completed_at && (
                                <p className="text-xs text-muted-foreground mt-1">
                                  Completed {formatDate(item.completed_at)}
                                </p>
                              )}
                            </div>
                            {item.status === "pending" || item.status === "in_progress" ? (
                              <div className="flex gap-2">
                                <Button
                                  size="sm"
                                  onClick={() => handleCompleteItem(item.id)}
                                  disabled={isProcessing || selectedPeriod.status === "closed"}
                                >
                                  Complete
                                </Button>
                                {!item.is_required && (
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => {
                                      setSkipItemId(item.id);
                                      setShowSkipDialog(true);
                                    }}
                                    disabled={isProcessing || selectedPeriod.status === "closed"}
                                  >
                                    Skip
                                  </Button>
                                )}
                              </div>
                            ) : null}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                  {checklist.length === 0 && (
                    <div className="text-center py-8 text-muted-foreground">
                      <p>No checklist items configured for this period.</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Adjusting Entries Summary */}
            {entriesSummary && (
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle>Adjusting Entries</CardTitle>
                      <CardDescription>
                        {entriesSummary.total} entries totaling{" "}
                        {formatCurrency(entriesSummary.total_amount, "USD")}
                      </CardDescription>
                    </div>
                    <Button variant="outline" size="sm" disabled>
                      <Plus className="mr-2 h-4 w-4" />
                      Add Entry
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-4 md:grid-cols-5">
                    <div className="text-center p-3 bg-muted rounded-lg">
                      <p className="text-2xl font-bold">{entriesSummary.draft}</p>
                      <p className="text-xs text-muted-foreground">Draft</p>
                    </div>
                    <div className="text-center p-3 bg-muted rounded-lg">
                      <p className="text-2xl font-bold">{entriesSummary.pending_approval}</p>
                      <p className="text-xs text-muted-foreground">Pending</p>
                    </div>
                    <div className="text-center p-3 bg-muted rounded-lg">
                      <p className="text-2xl font-bold">{entriesSummary.approved}</p>
                      <p className="text-xs text-muted-foreground">Approved</p>
                    </div>
                    <div className="text-center p-3 bg-muted rounded-lg">
                      <p className="text-2xl font-bold">{entriesSummary.rejected}</p>
                      <p className="text-xs text-muted-foreground">Rejected</p>
                    </div>
                    <div className="text-center p-3 bg-green-100 rounded-lg">
                      <p className="text-2xl font-bold text-green-700">{entriesSummary.posted}</p>
                      <p className="text-xs text-green-600">Posted</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Action Buttons */}
            <Card>
              <CardContent className="pt-6">
                <div className="flex flex-wrap gap-3">
                  {selectedPeriod.status === "open" && (
                    <Button onClick={handleStartClose} disabled={isProcessing}>
                      <Play className="mr-2 h-4 w-4" />
                      Start Close Process
                    </Button>
                  )}
                  {selectedPeriod.status === "in_progress" && (
                    <>
                      <Button onClick={handleLockPeriod} disabled={isProcessing}>
                        <Lock className="mr-2 h-4 w-4" />
                        Lock Period
                      </Button>
                      <Button variant="outline" onClick={handleSubmitForApproval} disabled={isProcessing}>
                        <Send className="mr-2 h-4 w-4" />
                        Submit for Approval
                      </Button>
                    </>
                  )}
                  {selectedPeriod.status === "locked" && (
                    <Button
                      variant="outline"
                      onClick={() => setShowUnlockDialog(true)}
                      disabled={isProcessing}
                    >
                      <Unlock className="mr-2 h-4 w-4" />
                      Unlock Period
                    </Button>
                  )}
                  {selectedPeriod.status === "pending_approval" && (
                    <>
                      <Button onClick={handleApprovePeriod} disabled={isProcessing}>
                        <ThumbsUp className="mr-2 h-4 w-4" />
                        Approve
                      </Button>
                      <Button
                        variant="destructive"
                        onClick={() => setShowRejectDialog(true)}
                        disabled={isProcessing}
                      >
                        <ThumbsDown className="mr-2 h-4 w-4" />
                        Reject
                      </Button>
                    </>
                  )}
                  {(selectedPeriod.status === "locked" || selectedPeriod.status === "pending_approval") &&
                    selectedPeriod.approved_at && (
                      <Button onClick={handleClosePeriod} disabled={isProcessing}>
                        <CheckCircle2 className="mr-2 h-4 w-4" />
                        Close Period
                      </Button>
                    )}
                  <Button variant="ghost" onClick={handleViewActivityLog}>
                    <History className="mr-2 h-4 w-4" />
                    View Activity Log
                  </Button>
                </div>
              </CardContent>
            </Card>
          </>
        )
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <Calendar className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No Period Selected</h3>
            <p className="text-muted-foreground mb-4">
              Select an existing period or create a new one to get started.
            </p>
            <Button onClick={() => setShowCreatePeriodDialog(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Create New Period
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Create Period Dialog */}
      <Dialog open={showCreatePeriodDialog} onOpenChange={setShowCreatePeriodDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Accounting Period</DialogTitle>
            <DialogDescription>Set up a new accounting period for month-end close.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="period_name">Period Name</Label>
              <Input
                id="period_name"
                value={newPeriod.period_name}
                onChange={(e) => setNewPeriod({ ...newPeriod, period_name: e.target.value })}
                placeholder="e.g., December 2024"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="period_type">Period Type</Label>
              <Select
                value={newPeriod.period_type}
                onValueChange={(value: "monthly" | "quarterly" | "annual") =>
                  setNewPeriod({ ...newPeriod, period_type: value })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="monthly">Monthly</SelectItem>
                  <SelectItem value="quarterly">Quarterly</SelectItem>
                  <SelectItem value="annual">Annual</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="start_date">Start Date</Label>
                <Input
                  id="start_date"
                  type="date"
                  value={newPeriod.start_date}
                  onChange={(e) => setNewPeriod({ ...newPeriod, start_date: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="end_date">End Date</Label>
                <Input
                  id="end_date"
                  type="date"
                  value={newPeriod.end_date}
                  onChange={(e) => setNewPeriod({ ...newPeriod, end_date: e.target.value })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="notes">Notes (optional)</Label>
              <Textarea
                id="notes"
                value={newPeriod.notes}
                onChange={(e) => setNewPeriod({ ...newPeriod, notes: e.target.value })}
                placeholder="Any additional notes for this period"
                rows={2}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreatePeriodDialog(false)} disabled={isProcessing}>
              Cancel
            </Button>
            <Button onClick={handleCreatePeriod} disabled={isProcessing}>
              {isProcessing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Plus className="mr-2 h-4 w-4" />}
              Create Period
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Unlock Dialog */}
      <Dialog open={showUnlockDialog} onOpenChange={setShowUnlockDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Unlock Period</DialogTitle>
            <DialogDescription>
              Unlocking allows modifications. Provide a reason for the audit trail.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label htmlFor="unlock_reason">Reason for Unlock</Label>
            <Textarea
              id="unlock_reason"
              value={unlockReason}
              onChange={(e) => setUnlockReason(e.target.value)}
              placeholder="Explain why this period needs to be unlocked"
              rows={3}
              className="mt-2"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowUnlockDialog(false)} disabled={isProcessing}>
              Cancel
            </Button>
            <Button onClick={handleUnlockPeriod} disabled={isProcessing || !unlockReason.trim()}>
              {isProcessing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Unlock className="mr-2 h-4 w-4" />}
              Unlock
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reject Dialog */}
      <Dialog open={showRejectDialog} onOpenChange={setShowRejectDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject Period</DialogTitle>
            <DialogDescription>
              The period will be sent back for corrections. Provide a reason.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label htmlFor="reject_reason">Rejection Reason</Label>
            <Textarea
              id="reject_reason"
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="Explain what needs to be corrected"
              rows={3}
              className="mt-2"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRejectDialog(false)} disabled={isProcessing}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleRejectPeriod}
              disabled={isProcessing || !rejectReason.trim()}
            >
              {isProcessing ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <ThumbsDown className="mr-2 h-4 w-4" />
              )}
              Reject
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Skip Item Dialog */}
      <Dialog open={showSkipDialog} onOpenChange={setShowSkipDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Skip Checklist Item</DialogTitle>
            <DialogDescription>Provide a reason for skipping this task.</DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label htmlFor="skip_reason">Skip Reason</Label>
            <Textarea
              id="skip_reason"
              value={skipReason}
              onChange={(e) => setSkipReason(e.target.value)}
              placeholder="Explain why this item is being skipped"
              rows={3}
              className="mt-2"
            />
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowSkipDialog(false);
                setSkipItemId(null);
                setSkipReason("");
              }}
              disabled={isProcessing}
            >
              Cancel
            </Button>
            <Button onClick={handleSkipItem} disabled={isProcessing || !skipReason.trim()}>
              {isProcessing ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <SkipForward className="mr-2 h-4 w-4" />
              )}
              Skip Item
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Activity Log Dialog */}
      <Dialog open={showActivityLogDialog} onOpenChange={setShowActivityLogDialog}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle>Activity Log</DialogTitle>
            <DialogDescription>History of actions taken on this period</DialogDescription>
          </DialogHeader>
          <div className="flex-1 overflow-y-auto py-4">
            {activityLog.length > 0 ? (
              <div className="space-y-3">
                {activityLog.map((entry) => (
                  <div key={entry.id} className="flex gap-3 p-3 border rounded-lg">
                    <div className="p-2 bg-muted rounded-full h-fit">
                      <History className="h-4 w-4" />
                    </div>
                    <div className="flex-1">
                      <p className="font-medium">{entry.action}</p>
                      <p className="text-sm text-muted-foreground">
                        {entry.user_name || "System"} - {formatDate(entry.created_at)}
                      </p>
                      {entry.details && (
                        <p className="text-xs text-muted-foreground mt-1">
                          {JSON.stringify(entry.details)}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <p>No activity recorded yet.</p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowActivityLogDialog(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
