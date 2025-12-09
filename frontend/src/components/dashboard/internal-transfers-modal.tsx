"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Loader2,
  ArrowLeftRight,
  CheckCircle,
  AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";
import { formatCurrency, formatDate, cn } from "@/lib/utils";
import {
  transactions,
  type InternalTransferMatch,
  type TransactionPair,
} from "@/lib/api";

interface InternalTransfersModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onTransfersApplied: () => void;
}

export function InternalTransfersModal({
  open,
  onOpenChange,
  onTransfersApplied,
}: InternalTransfersModalProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [matches, setMatches] = useState<InternalTransferMatch[]>([]);

  // Track selected matches
  const [selectedMatches, setSelectedMatches] = useState<Set<number>>(
    new Set()
  );

  // Confirmation dialog state
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean;
    title: string;
    description: string;
    onConfirm: () => void;
  } | null>(null);

  // Fetch internal transfers when modal opens
  useEffect(() => {
    if (open) {
      detectInternalTransfers();
    } else {
      // Reset state when closed
      setMatches([]);
      setSelectedMatches(new Set());
      setError(null);
    }
  }, [open]);

  async function detectInternalTransfers() {
    setIsLoading(true);
    setError(null);

    try {
      const response = await transactions.detectInternalTransfers();

      if (response.success && response.data) {
        setMatches(response.data.matches || []);
        // Initialize all matches as selected by default
        const allIndices = new Set(
          (response.data.matches || []).map((_: InternalTransferMatch, i: number) => i)
        );
        setSelectedMatches(allIndices);
      } else {
        setError(response.error?.message || "Failed to detect internal transfers");
      }
    } catch {
      setError("Failed to scan for internal transfers");
    } finally {
      setIsLoading(false);
    }
  }

  // Toggle single match selection
  function toggleMatch(index: number) {
    setSelectedMatches((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  }

  // Toggle all matches
  function toggleAll() {
    if (selectedMatches.size === matches.length) {
      setSelectedMatches(new Set());
    } else {
      setSelectedMatches(new Set(matches.map((_, i) => i)));
    }
  }

  // Apply internal transfer classification
  async function applyInternalTransfers(matchIndices: number[]) {
    const pairs: TransactionPair[] = matchIndices.map((index) => ({
      tx1_id: matches[index].tx1.id,
      tx2_id: matches[index].tx2.id,
    }));

    setIsApplying(true);
    try {
      const response = await transactions.applyInternalTransfer(pairs);

      if (response.success && response.data) {
        toast.success(response.data.message);
        detectInternalTransfers(); // Refresh list
        onTransfersApplied();
        return true;
      } else {
        toast.error(response.error?.message || "Failed to apply classification");
        return false;
      }
    } catch {
      toast.error("Failed to apply internal transfer classification");
      return false;
    } finally {
      setIsApplying(false);
    }
  }

  // Apply selected matches
  function handleApplySelected() {
    const selectedIndices = Array.from(selectedMatches);
    if (selectedIndices.length === 0) {
      toast.error("No transfer pairs selected");
      return;
    }

    setConfirmDialog({
      open: true,
      title: "Apply Internal Transfer Classification",
      description: `This will classify ${selectedIndices.length} pair(s) (${selectedIndices.length * 2} transactions) as internal transfers.`,
      onConfirm: async () => {
        await applyInternalTransfers(selectedIndices);
        setConfirmDialog(null);
      },
    });
  }

  // Apply by confidence threshold
  function handleApplyByConfidence(minScore: number) {
    const matchingIndices = matches
      .map((match, index) => ({ match, index }))
      .filter(({ match }) => match.match_score >= minScore)
      .map(({ index }) => index);

    if (matchingIndices.length === 0) {
      toast.warning(
        `No transfer pairs found with confidence >= ${Math.round(minScore * 100)}%`
      );
      return;
    }

    const threshold = Math.round(minScore * 100);
    setConfirmDialog({
      open: true,
      title: "Apply Internal Transfer Classification",
      description: `Apply "Internal Transfer" to ${matchingIndices.length} pair(s) with confidence >= ${threshold}%?`,
      onConfirm: async () => {
        await applyInternalTransfers(matchingIndices);
        setConfirmDialog(null);
      },
    });
  }

  // Get confidence badge color
  function getConfidenceBadge(score: number) {
    const percent = Math.round(score * 100);
    if (score >= 0.7) {
      return (
        <Badge className="bg-green-600 hover:bg-green-700">{percent}%</Badge>
      );
    }
    if (score >= 0.5) {
      return (
        <Badge className="bg-yellow-600 hover:bg-yellow-700">{percent}%</Badge>
      );
    }
    return <Badge className="bg-red-600 hover:bg-red-700">{percent}%</Badge>;
  }

  // Get counts by confidence level
  const highConfidenceCount = matches.filter(
    (m) => m.match_score >= 0.9
  ).length;
  const mediumConfidenceCount = matches.filter(
    (m) => m.match_score >= 0.7
  ).length;

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-6xl max-h-[85vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ArrowLeftRight className="h-5 w-5" />
              Internal Transfers Detection
            </DialogTitle>
            <DialogDescription>
              Detect and classify matching transaction pairs as internal
              transfers
            </DialogDescription>
          </DialogHeader>

          <div className="flex-1 overflow-auto space-y-4">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                <p className="mt-4 text-muted-foreground">
                  Scanning for internal transfers...
                </p>
              </div>
            ) : error ? (
              <div className="flex flex-col items-center justify-center py-12">
                <AlertTriangle className="h-12 w-12 text-muted-foreground/50" />
                <p className="mt-4 text-muted-foreground">{error}</p>
                <Button
                  variant="outline"
                  className="mt-4"
                  onClick={detectInternalTransfers}
                >
                  Try Again
                </Button>
              </div>
            ) : matches.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12">
                <CheckCircle className="h-12 w-12 text-green-500" />
                <p className="mt-4 text-lg font-medium">
                  No internal transfers detected!
                </p>
                <p className="text-muted-foreground">
                  No matching transaction pairs were found.
                </p>
              </div>
            ) : (
              <>
                {/* Summary */}
                <div className="flex items-center justify-between border-b pb-4">
                  <div className="flex items-center gap-4">
                    <Badge variant="secondary" className="text-sm">
                      {matches.length} potential pair
                      {matches.length !== 1 ? "s" : ""}
                    </Badge>
                    <Badge variant="outline" className="text-sm">
                      {selectedMatches.size} selected
                    </Badge>
                    <span className="text-sm text-muted-foreground">
                      High (90%+): {highConfidenceCount} | Medium (70%+):{" "}
                      {mediumConfidenceCount}
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleApplyByConfidence(0.9)}
                      disabled={isApplying || highConfidenceCount === 0}
                    >
                      Apply 90%+
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleApplyByConfidence(0.7)}
                      disabled={isApplying || mediumConfidenceCount === 0}
                    >
                      Apply 70%+
                    </Button>
                    <Button
                      size="sm"
                      onClick={handleApplySelected}
                      disabled={isApplying || selectedMatches.size === 0}
                    >
                      {isApplying ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      ) : (
                        <ArrowLeftRight className="mr-2 h-4 w-4" />
                      )}
                      Apply Selected
                    </Button>
                  </div>
                </div>

                {/* Matches Table */}
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[50px]">
                        <Checkbox
                          checked={selectedMatches.size === matches.length}
                          data-state={
                            selectedMatches.size > 0 &&
                            selectedMatches.size < matches.length
                              ? "indeterminate"
                              : selectedMatches.size === matches.length
                              ? "checked"
                              : "unchecked"
                          }
                          onCheckedChange={toggleAll}
                        />
                      </TableHead>
                      <TableHead>Transaction 1 (Outgoing)</TableHead>
                      <TableHead>Transaction 2 (Incoming)</TableHead>
                      <TableHead className="text-center w-[100px]">
                        Confidence
                      </TableHead>
                      <TableHead>Match Reasons</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {matches.map((match, index) => {
                      const isSelected = selectedMatches.has(index);
                      const tx1 = match.tx1;
                      const tx2 = match.tx2;

                      return (
                        <TableRow
                          key={index}
                          className={cn(
                            isSelected && "bg-blue-50 dark:bg-blue-950/20"
                          )}
                        >
                          <TableCell>
                            <Checkbox
                              checked={isSelected}
                              onCheckedChange={() => toggleMatch(index)}
                            />
                          </TableCell>
                          <TableCell>
                            <div className="space-y-1 text-sm">
                              <div className="font-medium">
                                {formatDate(tx1.date)}
                              </div>
                              <div className="text-muted-foreground truncate max-w-[200px]">
                                {tx1.description}
                              </div>
                              <div
                                className={cn(
                                  "font-medium",
                                  (tx1.amount || 0) >= 0
                                    ? "text-green-600"
                                    : "text-red-600"
                                )}
                              >
                                {formatCurrency(tx1.amount || 0, tx1.currency)}
                              </div>
                              {tx1.origin && (
                                <div className="text-xs text-muted-foreground">
                                  Origin: {tx1.origin.slice(0, 20)}...
                                </div>
                              )}
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className="space-y-1 text-sm">
                              <div className="font-medium">
                                {formatDate(tx2.date)}
                              </div>
                              <div className="text-muted-foreground truncate max-w-[200px]">
                                {tx2.description}
                              </div>
                              <div
                                className={cn(
                                  "font-medium",
                                  (tx2.amount || 0) >= 0
                                    ? "text-green-600"
                                    : "text-red-600"
                                )}
                              >
                                {formatCurrency(tx2.amount || 0, tx2.currency)}
                              </div>
                              {tx2.destination && (
                                <div className="text-xs text-muted-foreground">
                                  Dest: {tx2.destination.slice(0, 20)}...
                                </div>
                              )}
                            </div>
                          </TableCell>
                          <TableCell className="text-center">
                            {getConfidenceBadge(match.match_score)}
                          </TableCell>
                          <TableCell>
                            <div className="flex flex-wrap gap-1">
                              {match.match_reasons.map((reason, i) => (
                                <Badge
                                  key={i}
                                  variant="outline"
                                  className="text-xs"
                                >
                                  {reason}
                                </Badge>
                              ))}
                            </div>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Confirmation Dialog */}
      <AlertDialog
        open={confirmDialog?.open || false}
        onOpenChange={(open) => !open && setConfirmDialog(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{confirmDialog?.title}</AlertDialogTitle>
            <AlertDialogDescription>
              {confirmDialog?.description}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDialog?.onConfirm}>
              Apply
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
