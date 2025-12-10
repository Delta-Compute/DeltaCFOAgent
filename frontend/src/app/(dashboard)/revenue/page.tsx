"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Receipt,
  CheckCircle2,
  Clock,
  AlertCircle,
  RefreshCw,
  Play,
  Check,
  X,
  Unlink,
  FileText,
  DollarSign,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { toast } from "sonner";

import {
  revenue,
  type MatchingStats,
  type PendingMatch,
  type MatchedPair,
} from "@/lib/api";
import { formatCurrency, formatDate, cn, getConfidenceLevel } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { StatsCard, StatsGrid } from "@/components/dashboard/stats-card";
import { ErrorState, EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/loading";

// Pending Match Card Component
function PendingMatchCard({
  match,
  onConfirm,
  onReject,
  isProcessing,
}: {
  match: PendingMatch;
  onConfirm: () => void;
  onReject: () => void;
  isProcessing: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const confidenceLevel = getConfidenceLevel(match.confidence_score);

  return (
    <Card className="overflow-hidden">
      <div className="p-4">
        {/* Header with invoice and transaction summary */}
        <div className="flex flex-col lg:flex-row lg:items-start gap-4">
          {/* Invoice Side */}
          <div className="flex-1 space-y-2">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Invoice</span>
            </div>
            <div>
              <p className="font-semibold">{match.invoice.invoice_number}</p>
              <p className="text-sm text-muted-foreground">
                {match.invoice.vendor_name}
              </p>
              <p className="text-sm font-medium text-primary">
                {formatCurrency(match.invoice.total_amount, match.invoice.currency)}
              </p>
              <p className="text-xs text-muted-foreground">
                Due: {formatDate(match.invoice.due_date)}
              </p>
            </div>
          </div>

          {/* Arrow / Confidence */}
          <div className="flex lg:flex-col items-center justify-center gap-2 py-2">
            <Badge
              variant="outline"
              className={cn(
                "text-xs",
                confidenceLevel === "high" && "border-green-500 text-green-700",
                confidenceLevel === "medium" && "border-yellow-500 text-yellow-700",
                confidenceLevel === "low" && "border-red-500 text-red-700"
              )}
            >
              {(match.confidence_score * 100).toFixed(0)}%
            </Badge>
            <div className="h-px w-8 lg:w-px lg:h-8 bg-border" />
          </div>

          {/* Transaction Side */}
          <div className="flex-1 space-y-2">
            <div className="flex items-center gap-2">
              <DollarSign className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Transaction</span>
            </div>
            <div>
              <p className="font-semibold truncate" title={match.transaction.description}>
                {match.transaction.description}
              </p>
              <p className="text-sm font-medium text-green-600">
                {formatCurrency(match.transaction.amount, match.transaction.currency)}
              </p>
              <p className="text-xs text-muted-foreground">
                Date: {formatDate(match.transaction.date)}
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex lg:flex-col gap-2">
            <Button
              size="sm"
              onClick={onConfirm}
              disabled={isProcessing}
              className="flex-1"
            >
              <Check className="h-4 w-4 mr-1" />
              Confirm
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={onReject}
              disabled={isProcessing}
              className="flex-1"
            >
              <X className="h-4 w-4 mr-1" />
              Reject
            </Button>
          </div>
        </div>

        {/* Match Reasons (expandable) */}
        {match.match_reasons && match.match_reasons.length > 0 && (
          <div className="mt-3 pt-3 border-t">
            <button
              className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
              Match reasons ({match.match_reasons.length})
            </button>
            {expanded && (
              <ul className="mt-2 space-y-1">
                {match.match_reasons.map((reason, idx) => (
                  <li key={idx} className="text-sm text-muted-foreground flex items-start gap-2">
                    <Check className="h-4 w-4 text-green-500 flex-shrink-0 mt-0.5" />
                    {reason}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}

// Matched Pair Card Component
function MatchedPairCard({
  pair,
  onUnmatch,
  isProcessing,
}: {
  pair: MatchedPair;
  onUnmatch: () => void;
  isProcessing: boolean;
}) {
  return (
    <Card>
      <div className="p-4">
        <div className="flex flex-col lg:flex-row lg:items-center gap-4">
          {/* Invoice Info */}
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <span className="font-medium">{pair.invoice.invoice_number}</span>
            </div>
            <p className="text-sm text-muted-foreground">{pair.invoice.vendor_name}</p>
            <p className="text-sm font-medium">
              {formatCurrency(pair.invoice.total_amount, pair.invoice.currency)}
            </p>
          </div>

          {/* Link indicator */}
          <div className="flex items-center gap-2 text-green-600">
            <CheckCircle2 className="h-5 w-5" />
            <span className="text-sm font-medium">Matched</span>
          </div>

          {/* Transaction Info */}
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <DollarSign className="h-4 w-4 text-muted-foreground" />
              <span className="font-medium truncate" title={pair.transaction.description}>
                {pair.transaction.description.slice(0, 30)}...
              </span>
            </div>
            <p className="text-sm text-muted-foreground">
              {formatDate(pair.transaction.date)}
            </p>
            <p className="text-sm font-medium text-green-600">
              {formatCurrency(pair.transaction.amount, pair.transaction.currency)}
            </p>
          </div>

          {/* Meta & Actions */}
          <div className="flex items-center gap-3">
            <div className="text-right">
              <Badge variant={pair.match_method === "auto" ? "secondary" : "outline"}>
                {pair.match_method === "auto" ? "Auto" : "Manual"}
              </Badge>
              <p className="text-xs text-muted-foreground mt-1">
                {formatDate(pair.matched_at)}
              </p>
            </div>
            <Button
              size="sm"
              variant="ghost"
              onClick={onUnmatch}
              disabled={isProcessing}
            >
              <Unlink className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
}

export default function RevenueRecognitionPage() {
  // State
  const [stats, setStats] = useState<MatchingStats | null>(null);
  const [pendingMatches, setPendingMatches] = useState<PendingMatch[]>([]);
  const [matchedPairs, setMatchedPairs] = useState<MatchedPair[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRunningMatch, setIsRunningMatch] = useState(false);
  const [processingIds, setProcessingIds] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  // Pagination
  const [pendingPage, setPendingPage] = useState(1);
  const [pendingTotal, setPendingTotal] = useState(0);
  const [matchedPage, setMatchedPage] = useState(1);
  const [matchedTotal, setMatchedTotal] = useState(0);
  const pageSize = 10;

  // Load stats
  const loadStats = useCallback(async () => {
    const result = await revenue.getStats();
    if (result.success && result.data) {
      setStats(result.data);
    }
  }, []);

  // Load pending matches
  const loadPendingMatches = useCallback(async () => {
    const result = await revenue.getPendingMatches({
      page: String(pendingPage),
      per_page: String(pageSize),
    });
    if (result.success && result.data) {
      setPendingMatches(result.data.matches);
      setPendingTotal(result.data.total);
    }
  }, [pendingPage]);

  // Load matched pairs
  const loadMatchedPairs = useCallback(async () => {
    const result = await revenue.getMatchedPairs({
      page: String(matchedPage),
      per_page: String(pageSize),
    });
    if (result.success && result.data) {
      setMatchedPairs(result.data.pairs);
      setMatchedTotal(result.data.total);
    }
  }, [matchedPage]);

  // Load all data
  const loadAllData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      await Promise.all([loadStats(), loadPendingMatches(), loadMatchedPairs()]);
    } catch {
      setError("Failed to load revenue data");
    } finally {
      setIsLoading(false);
    }
  }, [loadStats, loadPendingMatches, loadMatchedPairs]);

  useEffect(() => {
    loadAllData();
  }, [loadAllData]);

  // Run matching
  async function handleRunMatching() {
    setIsRunningMatch(true);
    try {
      const result = await revenue.runMatching();
      if (result.success && result.data) {
        toast.success(
          `Found ${result.data.matches_found} matches. ` +
          `${result.data.auto_confirmed} auto-confirmed, ` +
          `${result.data.pending_review} pending review.`
        );
        await loadAllData();
      } else {
        toast.error(result.error?.message || "Failed to run matching");
      }
    } catch {
      toast.error("Failed to run matching");
    } finally {
      setIsRunningMatch(false);
    }
  }

  // Confirm match
  async function handleConfirmMatch(match: PendingMatch) {
    const key = `${match.invoice.id}-${match.transaction.id}`;
    setProcessingIds((prev) => new Set(prev).add(key));
    try {
      const result = await revenue.confirmMatch(match.invoice.id, match.transaction.id);
      if (result.success) {
        toast.success("Match confirmed");
        await Promise.all([loadStats(), loadPendingMatches(), loadMatchedPairs()]);
      } else {
        toast.error(result.error?.message || "Failed to confirm match");
      }
    } catch {
      toast.error("Failed to confirm match");
    } finally {
      setProcessingIds((prev) => {
        const next = new Set(prev);
        next.delete(key);
        return next;
      });
    }
  }

  // Reject match
  async function handleRejectMatch(match: PendingMatch) {
    const key = `${match.invoice.id}-${match.transaction.id}`;
    setProcessingIds((prev) => new Set(prev).add(key));
    try {
      const result = await revenue.rejectMatch(match.invoice.id, match.transaction.id);
      if (result.success) {
        toast.success("Match rejected");
        await Promise.all([loadStats(), loadPendingMatches()]);
      } else {
        toast.error(result.error?.message || "Failed to reject match");
      }
    } catch {
      toast.error("Failed to reject match");
    } finally {
      setProcessingIds((prev) => {
        const next = new Set(prev);
        next.delete(key);
        return next;
      });
    }
  }

  // Unmatch
  async function handleUnmatch(pair: MatchedPair) {
    const key = pair.invoice.id;
    setProcessingIds((prev) => new Set(prev).add(key));
    try {
      const result = await revenue.unmatch(pair.invoice.id);
      if (result.success) {
        toast.success("Match removed");
        await Promise.all([loadStats(), loadPendingMatches(), loadMatchedPairs()]);
      } else {
        toast.error(result.error?.message || "Failed to unmatch");
      }
    } catch {
      toast.error("Failed to unmatch");
    } finally {
      setProcessingIds((prev) => {
        const next = new Set(prev);
        next.delete(key);
        return next;
      });
    }
  }

  if (error) {
    return <ErrorState title={error} onRetry={loadAllData} />;
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold font-heading">Revenue Recognition</h1>
          <p className="text-muted-foreground">
            Match invoices with bank transactions to recognize revenue
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={loadAllData} disabled={isLoading}>
            <RefreshCw className={cn("mr-2 h-4 w-4", isLoading && "animate-spin")} />
            Refresh
          </Button>
          <Button onClick={handleRunMatching} disabled={isRunningMatch}>
            {isRunningMatch ? (
              <>
                <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                Running...
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Run Matching
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Stats */}
      <StatsGrid>
        <StatsCard
          title="Total Invoices"
          value={stats?.total_invoices?.toLocaleString() || "0"}
          icon={Receipt}
          isLoading={isLoading}
        />
        <StatsCard
          title="Matched"
          value={stats?.matched_invoices?.toLocaleString() || "0"}
          icon={CheckCircle2}
          trend={stats?.match_rate ? { value: stats.match_rate, label: "match rate" } : undefined}
          isLoading={isLoading}
        />
        <StatsCard
          title="Pending Review"
          value={stats?.pending_matches?.toLocaleString() || "0"}
          icon={Clock}
          isLoading={isLoading}
        />
        <StatsCard
          title="Unmatched"
          value={stats?.unmatched_invoices?.toLocaleString() || "0"}
          icon={AlertCircle}
          isLoading={isLoading}
        />
      </StatsGrid>

      {/* Pending Matches Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Pending Matches
          </CardTitle>
          <CardDescription>
            Review and approve suggested invoice-transaction matches
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-32 w-full" />
              ))}
            </div>
          ) : pendingMatches.length === 0 ? (
            <EmptyState
              icon={CheckCircle2}
              title="No pending matches"
              description="All matches have been reviewed. Run matching to find new potential matches."
            />
          ) : (
            <div className="space-y-4">
              {pendingMatches.map((match) => (
                <PendingMatchCard
                  key={`${match.invoice.id}-${match.transaction.id}`}
                  match={match}
                  onConfirm={() => handleConfirmMatch(match)}
                  onReject={() => handleRejectMatch(match)}
                  isProcessing={processingIds.has(`${match.invoice.id}-${match.transaction.id}`)}
                />
              ))}
              {/* Pagination */}
              {pendingTotal > pageSize && (
                <div className="flex items-center justify-between pt-4 border-t">
                  <p className="text-sm text-muted-foreground">
                    Showing {(pendingPage - 1) * pageSize + 1} to{" "}
                    {Math.min(pendingPage * pageSize, pendingTotal)} of {pendingTotal}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPendingPage((p) => Math.max(1, p - 1))}
                      disabled={pendingPage <= 1}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPendingPage((p) => p + 1)}
                      disabled={pendingPage * pageSize >= pendingTotal}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Matched Pairs Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-green-600" />
            Confirmed Matches
          </CardTitle>
          <CardDescription>
            Successfully matched invoice-transaction pairs
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-24 w-full" />
              ))}
            </div>
          ) : matchedPairs.length === 0 ? (
            <EmptyState
              icon={Receipt}
              title="No confirmed matches"
              description="Confirm pending matches or run matching to find potential matches."
            />
          ) : (
            <div className="space-y-4">
              {matchedPairs.map((pair) => (
                <MatchedPairCard
                  key={pair.invoice.id}
                  pair={pair}
                  onUnmatch={() => handleUnmatch(pair)}
                  isProcessing={processingIds.has(pair.invoice.id)}
                />
              ))}
              {/* Pagination */}
              {matchedTotal > pageSize && (
                <div className="flex items-center justify-between pt-4 border-t">
                  <p className="text-sm text-muted-foreground">
                    Showing {(matchedPage - 1) * pageSize + 1} to{" "}
                    {Math.min(matchedPage * pageSize, matchedTotal)} of {matchedTotal}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setMatchedPage((p) => Math.max(1, p - 1))}
                      disabled={matchedPage <= 1}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setMatchedPage((p) => p + 1)}
                      disabled={matchedPage * pageSize >= matchedTotal}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
