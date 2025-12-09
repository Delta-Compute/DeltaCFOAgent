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
  Archive,
  Copy,
  CheckCircle,
  AlertTriangle,
  FileText,
} from "lucide-react";
import { toast } from "sonner";
import { formatCurrency, formatDate, cn } from "@/lib/utils";

// Types for duplicate detection
interface DuplicateTransaction {
  transaction_id: string;
  date: string;
  description: string;
  amount: number;
  classified_entity: string | null;
  accounting_category: string | null;
  subcategory: string | null;
  confidence: number;
  source_file: string | null;
}

interface DuplicateGroup {
  date: string;
  description: string;
  amount: number;
  count: number;
  transactions: DuplicateTransaction[];
}

interface DuplicateDetectionModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDuplicatesResolved: () => void;
}

export function DuplicateDetectionModal({
  open,
  onOpenChange,
  onDuplicatesResolved,
}: DuplicateDetectionModalProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [duplicateGroups, setDuplicateGroups] = useState<DuplicateGroup[]>([]);
  const [totalGroups, setTotalGroups] = useState(0);
  const [totalDuplicates, setTotalDuplicates] = useState(0);

  // Track selected transactions per group
  const [selectedTransactions, setSelectedTransactions] = useState<
    Record<number, Set<string>>
  >({});

  // Confirmation dialog state
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean;
    title: string;
    description: string;
    onConfirm: () => void;
  } | null>(null);

  // Fetch duplicates when modal opens
  useEffect(() => {
    if (open) {
      findDuplicates();
    } else {
      // Reset state when closed
      setDuplicateGroups([]);
      setSelectedTransactions({});
      setError(null);
    }
  }, [open]);

  async function findDuplicates() {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/transactions/find-duplicates", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      const data = await response.json();

      if (data.success) {
        setDuplicateGroups(data.duplicate_groups || []);
        setTotalGroups(data.total_groups || 0);
        setTotalDuplicates(data.total_duplicates || 0);

        // Initialize selection state for each group
        const initialSelection: Record<number, Set<string>> = {};
        (data.duplicate_groups || []).forEach((_: DuplicateGroup, i: number) => {
          initialSelection[i] = new Set();
        });
        setSelectedTransactions(initialSelection);
      } else {
        setError(data.error || "Failed to find duplicates");
      }
    } catch {
      setError("Failed to scan for duplicates");
    } finally {
      setIsLoading(false);
    }
  }

  // Toggle single transaction selection
  function toggleTransaction(groupIndex: number, transactionId: string) {
    setSelectedTransactions((prev) => {
      const groupSet = new Set(prev[groupIndex] || []);
      if (groupSet.has(transactionId)) {
        groupSet.delete(transactionId);
      } else {
        groupSet.add(transactionId);
      }
      return { ...prev, [groupIndex]: groupSet };
    });
  }

  // Toggle all transactions in a group
  function toggleAllInGroup(groupIndex: number) {
    const group = duplicateGroups[groupIndex];
    const currentSelection = selectedTransactions[groupIndex] || new Set();
    const allSelected = group.transactions.every((t) =>
      currentSelection.has(t.transaction_id)
    );

    setSelectedTransactions((prev) => {
      if (allSelected) {
        // Deselect all
        return { ...prev, [groupIndex]: new Set() };
      } else {
        // Select all
        return {
          ...prev,
          [groupIndex]: new Set(group.transactions.map((t) => t.transaction_id)),
        };
      }
    });
  }

  // Check if all in group are selected
  function isAllSelected(groupIndex: number): boolean {
    const group = duplicateGroups[groupIndex];
    const selection = selectedTransactions[groupIndex] || new Set();
    return (
      group.transactions.length > 0 &&
      group.transactions.every((t) => selection.has(t.transaction_id))
    );
  }

  // Check if some (but not all) are selected
  function isSomeSelected(groupIndex: number): boolean {
    const group = duplicateGroups[groupIndex];
    const selection = selectedTransactions[groupIndex] || new Set();
    return (
      selection.size > 0 &&
      !group.transactions.every((t) => selection.has(t.transaction_id))
    );
  }

  // Archive transactions
  async function archiveTransactions(transactionIds: string[]) {
    try {
      const response = await fetch("/api/archive_transactions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transaction_ids: transactionIds }),
      });
      const data = await response.json();

      if (data.success) {
        toast.success(`Archived ${data.archived_count} transaction(s)`);
        if (data.warning) {
          toast.warning(data.warning);
        }
        // Refresh duplicates list
        findDuplicates();
        onDuplicatesResolved();
        return true;
      } else {
        toast.error(data.error || "Failed to archive transactions");
        return false;
      }
    } catch {
      toast.error("Failed to archive transactions");
      return false;
    }
  }

  // Archive single transaction
  function handleArchiveSingle(transactionId: string) {
    setConfirmDialog({
      open: true,
      title: "Archive Transaction",
      description: "Are you sure you want to archive this transaction?",
      onConfirm: async () => {
        await archiveTransactions([transactionId]);
        setConfirmDialog(null);
      },
    });
  }

  // Archive all but first in a group
  function handleArchiveAllButFirst(groupIndex: number) {
    const group = duplicateGroups[groupIndex];
    const idsToArchive = group.transactions.slice(1).map((t) => t.transaction_id);

    setConfirmDialog({
      open: true,
      title: "Archive Duplicates",
      description: `This will archive ${idsToArchive.length} duplicate transaction(s), keeping the first one.`,
      onConfirm: async () => {
        await archiveTransactions(idsToArchive);
        setConfirmDialog(null);
      },
    });
  }

  // Archive selected transactions
  function handleArchiveSelected() {
    const allSelected: string[] = [];
    Object.values(selectedTransactions).forEach((set) => {
      set.forEach((id) => allSelected.push(id));
    });

    if (allSelected.length === 0) {
      toast.error("No transactions selected");
      return;
    }

    setConfirmDialog({
      open: true,
      title: "Archive Selected",
      description: `Archive ${allSelected.length} selected transaction(s)?`,
      onConfirm: async () => {
        await archiveTransactions(allSelected);
        setConfirmDialog(null);
      },
    });
  }

  // Archive all but first globally (across all groups)
  function handleArchiveAllButFirstGlobally() {
    const idsToArchive: string[] = [];
    duplicateGroups.forEach((group) => {
      // Skip the first transaction in each group
      group.transactions.slice(1).forEach((t) => {
        idsToArchive.push(t.transaction_id);
      });
    });

    if (idsToArchive.length === 0) {
      toast.info("No duplicates to archive");
      return;
    }

    setConfirmDialog({
      open: true,
      title: "Archive All Duplicates",
      description: `This will archive ${idsToArchive.length} duplicate transaction(s) across all groups, keeping the first in each group.`,
      onConfirm: async () => {
        await archiveTransactions(idsToArchive);
        setConfirmDialog(null);
      },
    });
  }

  // Get total selected count
  function getTotalSelectedCount(): number {
    return Object.values(selectedTransactions).reduce(
      (sum, set) => sum + set.size,
      0
    );
  }

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-5xl max-h-[85vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Copy className="h-5 w-5" />
              Duplicate Detection
            </DialogTitle>
            <DialogDescription>
              Identify and manage duplicate transactions
            </DialogDescription>
          </DialogHeader>

          <div className="flex-1 overflow-auto space-y-4">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                <p className="mt-4 text-muted-foreground">
                  Scanning for duplicate transactions...
                </p>
              </div>
            ) : error ? (
              <div className="flex flex-col items-center justify-center py-12">
                <AlertTriangle className="h-12 w-12 text-muted-foreground/50" />
                <p className="mt-4 text-muted-foreground">{error}</p>
                <Button variant="outline" className="mt-4" onClick={findDuplicates}>
                  Try Again
                </Button>
              </div>
            ) : duplicateGroups.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12">
                <CheckCircle className="h-12 w-12 text-green-500" />
                <p className="mt-4 text-lg font-medium">No duplicates found!</p>
                <p className="text-muted-foreground">
                  All your transactions appear to be unique.
                </p>
              </div>
            ) : (
              <>
                {/* Summary */}
                <div className="flex items-center justify-between border-b pb-4">
                  <div className="flex items-center gap-4">
                    <Badge variant="secondary" className="text-sm">
                      {totalGroups} group{totalGroups !== 1 ? "s" : ""}
                    </Badge>
                    <Badge variant="outline" className="text-sm">
                      {totalDuplicates} duplicate transactions
                    </Badge>
                    {getTotalSelectedCount() > 0 && (
                      <Badge className="text-sm">
                        {getTotalSelectedCount()} selected
                      </Badge>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleArchiveSelected}
                      disabled={getTotalSelectedCount() === 0}
                    >
                      <Archive className="mr-2 h-4 w-4" />
                      Archive Selected
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={handleArchiveAllButFirstGlobally}
                    >
                      <Archive className="mr-2 h-4 w-4" />
                      Archive All Duplicates
                    </Button>
                  </div>
                </div>

                {/* Duplicate Groups */}
                <div className="space-y-6">
                  {duplicateGroups.map((group, groupIndex) => (
                    <div
                      key={groupIndex}
                      className="rounded-lg border bg-muted/30 overflow-hidden"
                    >
                      {/* Group Header */}
                      <div className="bg-muted/50 px-4 py-3 border-b flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <Badge variant="outline">
                            Group {groupIndex + 1}
                          </Badge>
                          <span className="text-sm font-medium">
                            {group.count} transactions
                          </span>
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleArchiveAllButFirst(groupIndex)}
                        >
                          <Archive className="mr-2 h-4 w-4" />
                          Keep First, Archive Rest
                        </Button>
                      </div>

                      {/* Group Info */}
                      <div className="px-4 py-3 bg-blue-50 dark:bg-blue-950/20 border-b">
                        <div className="grid grid-cols-3 gap-4 text-sm">
                          <div>
                            <span className="text-muted-foreground">Date:</span>{" "}
                            <span className="font-medium">{formatDate(group.date)}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">Amount:</span>{" "}
                            <span className={cn(
                              "font-medium",
                              group.amount >= 0 ? "text-green-600" : "text-red-600"
                            )}>
                              {formatCurrency(group.amount)}
                            </span>
                          </div>
                          <div className="truncate">
                            <span className="text-muted-foreground">Description:</span>{" "}
                            <span className="font-medium">{group.description}</span>
                          </div>
                        </div>
                      </div>

                      {/* Transactions Table */}
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="w-[50px]">
                              <Checkbox
                                checked={isAllSelected(groupIndex)}
                                // Use data attribute for indeterminate
                                data-state={
                                  isSomeSelected(groupIndex)
                                    ? "indeterminate"
                                    : isAllSelected(groupIndex)
                                    ? "checked"
                                    : "unchecked"
                                }
                                onCheckedChange={() => toggleAllInGroup(groupIndex)}
                              />
                            </TableHead>
                            <TableHead>ID</TableHead>
                            <TableHead>Entity</TableHead>
                            <TableHead>Category</TableHead>
                            <TableHead>Source</TableHead>
                            <TableHead className="text-center">Confidence</TableHead>
                            <TableHead className="w-[80px]"></TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {group.transactions.map((txn, txnIndex) => {
                            const isSelected =
                              selectedTransactions[groupIndex]?.has(
                                txn.transaction_id
                              ) || false;
                            const isFirst = txnIndex === 0;

                            return (
                              <TableRow
                                key={txn.transaction_id}
                                className={cn(isFirst && "bg-green-50 dark:bg-green-950/20")}
                              >
                                <TableCell>
                                  <Checkbox
                                    checked={isSelected}
                                    onCheckedChange={() =>
                                      toggleTransaction(groupIndex, txn.transaction_id)
                                    }
                                  />
                                </TableCell>
                                <TableCell>
                                  <div className="flex items-center gap-2">
                                    <span className="font-mono text-xs truncate max-w-[100px]">
                                      {txn.transaction_id.slice(0, 8)}...
                                    </span>
                                    {isFirst && (
                                      <Badge variant="secondary" className="text-xs">
                                        Keep
                                      </Badge>
                                    )}
                                  </div>
                                </TableCell>
                                <TableCell>
                                  {txn.classified_entity || "-"}
                                </TableCell>
                                <TableCell>
                                  <div>
                                    {txn.accounting_category || "-"}
                                    {txn.subcategory && (
                                      <div className="text-xs text-muted-foreground">
                                        {txn.subcategory}
                                      </div>
                                    )}
                                  </div>
                                </TableCell>
                                <TableCell>
                                  {txn.source_file ? (
                                    <div className="flex items-center gap-1 text-xs">
                                      <FileText className="h-3 w-3" />
                                      <span className="truncate max-w-[100px]">
                                        {txn.source_file}
                                      </span>
                                    </div>
                                  ) : (
                                    "-"
                                  )}
                                </TableCell>
                                <TableCell className="text-center">
                                  {txn.confidence ? (
                                    <span className="text-xs">
                                      {Math.round(txn.confidence * 100)}%
                                    </span>
                                  ) : (
                                    "-"
                                  )}
                                </TableCell>
                                <TableCell>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() =>
                                      handleArchiveSingle(txn.transaction_id)
                                    }
                                  >
                                    <Archive className="h-4 w-4" />
                                  </Button>
                                </TableCell>
                              </TableRow>
                            );
                          })}
                        </TableBody>
                      </Table>
                    </div>
                  ))}
                </div>
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
              Archive
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
