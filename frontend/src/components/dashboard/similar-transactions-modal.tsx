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
import { Loader2, RefreshCw, Check, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { formatCurrency, formatDate, cn } from "@/lib/utils";

interface SimilarTransaction {
  transaction_id: string;
  date: string;
  description: string;
  amount: number;
  currency?: string;
  classified_entity?: string;
  confidence?: number;
}

interface SimilarTransactionsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  transactionId: string | null;
  newEntity: string;
  onUpdated: () => void;
}

export function SimilarTransactionsModal({
  open,
  onOpenChange,
  transactionId,
  newEntity,
  onUpdated,
}: SimilarTransactionsModalProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [similarTransactions, setSimilarTransactions] = useState<SimilarTransaction[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [hasLearnedPatterns, setHasLearnedPatterns] = useState(true);

  // Fetch similar transactions when modal opens
  useEffect(() => {
    if (open && transactionId && newEntity) {
      fetchSimilarTransactions();
    } else {
      // Reset state when closed
      setSimilarTransactions([]);
      setSelectedIds(new Set());
      setError(null);
    }
  }, [open, transactionId, newEntity]);

  async function fetchSimilarTransactions() {
    if (!transactionId || !newEntity) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `/api/suggestions?transaction_id=${transactionId}&field_type=similar_entities&value=${encodeURIComponent(newEntity)}`
      );
      const data = await response.json();

      const suggestions = data.suggestions || [];
      setSimilarTransactions(suggestions);
      setHasLearnedPatterns(data.has_learned_patterns !== false);

      // Pre-select all by default
      setSelectedIds(new Set(suggestions.map((t: SimilarTransaction) => t.transaction_id)));
    } catch {
      setError("Failed to fetch similar transactions");
    } finally {
      setIsLoading(false);
    }
  }

  function toggleTransaction(txId: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(txId)) {
        next.delete(txId);
      } else {
        next.add(txId);
      }
      return next;
    });
  }

  function selectAll(select: boolean) {
    if (select) {
      setSelectedIds(new Set(similarTransactions.map((t) => t.transaction_id)));
    } else {
      setSelectedIds(new Set());
    }
  }

  async function applyToSelected() {
    if (selectedIds.size === 0) return;

    setIsApplying(true);
    let successCount = 0;
    let errorCount = 0;

    try {
      // Build updates array for bulk update
      const updates = Array.from(selectedIds).map((txId) => ({
        transaction_id: txId,
        field: "classified_entity",
        value: newEntity,
      }));

      const response = await fetch("/api/bulk_update_transactions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ updates }),
      });

      const data = await response.json();

      if (data.success) {
        successCount = selectedIds.size;
        toast.success(`Updated ${successCount} transaction(s) to "${newEntity}"`);
        onUpdated();
        onOpenChange(false);
      } else {
        errorCount = selectedIds.size;
        toast.error(data.error || "Failed to update transactions");
      }
    } catch {
      toast.error("Failed to update transactions");
    } finally {
      setIsApplying(false);
    }
  }

  // Calculate selected amount total
  const selectedTotal = similarTransactions
    .filter((t) => selectedIds.has(t.transaction_id))
    .reduce((sum, t) => sum + (t.amount || 0), 0);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <RefreshCw className="h-5 w-5" />
            Update Similar Transactions
          </DialogTitle>
          <DialogDescription>
            Apply the same entity classification to similar transactions
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-auto space-y-4">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              <p className="mt-4 text-muted-foreground">
                Finding similar transactions with AI...
              </p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-12">
              <AlertCircle className="h-12 w-12 text-muted-foreground/50" />
              <p className="mt-4 text-muted-foreground">{error}</p>
              <Button variant="outline" className="mt-4" onClick={fetchSimilarTransactions}>
                Try Again
              </Button>
            </div>
          ) : similarTransactions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Check className="h-12 w-12 text-green-500" />
              <p className="mt-4 text-muted-foreground">
                No similar transactions found. Your entity classification is unique.
              </p>
            </div>
          ) : (
            <>
              {/* Update Preview */}
              <div className="rounded-lg border bg-muted/30 p-4">
                <h4 className="font-medium mb-2">Entity Update Preview</h4>
                <p className="text-sm">
                  <strong>Change:</strong> Entity to &quot;{newEntity}&quot;
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  AI analyzed unclassified transactions and found similar patterns
                </p>
                {!hasLearnedPatterns && (
                  <p className="text-xs text-muted-foreground mt-2">
                    (Using intelligent matching as fallback - pattern learning will improve accuracy over time)
                  </p>
                )}
              </div>

              {/* Selection Controls */}
              <div className="flex items-center justify-between">
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => selectAll(true)}>
                    Select All
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => selectAll(false)}>
                    Deselect All
                  </Button>
                </div>
                <div className="text-sm text-muted-foreground">
                  {selectedIds.size} of {similarTransactions.length} selected
                  {selectedIds.size > 0 && (
                    <span className="ml-2">
                      ({formatCurrency(selectedTotal)})
                    </span>
                  )}
                </div>
              </div>

              {/* Transactions List */}
              <div className="space-y-2 max-h-[300px] overflow-auto">
                {similarTransactions.map((tx) => (
                  <div
                    key={tx.transaction_id}
                    className={cn(
                      "rounded-lg border p-3 transition-colors cursor-pointer",
                      selectedIds.has(tx.transaction_id)
                        ? "border-primary bg-primary/5"
                        : "bg-muted/30"
                    )}
                    onClick={() => toggleTransaction(tx.transaction_id)}
                  >
                    <div className="flex items-start gap-3">
                      <Checkbox
                        checked={selectedIds.has(tx.transaction_id)}
                        onCheckedChange={() => toggleTransaction(tx.transaction_id)}
                        className="mt-1"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-sm text-muted-foreground">
                            {formatDate(tx.date)}
                          </span>
                          <span
                            className={cn(
                              "font-medium text-sm",
                              tx.amount >= 0 ? "text-green-600" : "text-red-600"
                            )}
                          >
                            {formatCurrency(tx.amount, tx.currency)}
                          </span>
                        </div>
                        <p className="text-sm truncate mt-1" title={tx.description}>
                          {tx.description}
                        </p>
                        <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                          <span>Current: {tx.classified_entity || "Unclassified"}</span>
                          <span>|</span>
                          <span>
                            Confidence: {Math.round((tx.confidence || 0) * 100)}%
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Apply Button */}
              <div className="pt-4 border-t flex justify-end gap-2">
                <Button variant="outline" onClick={() => onOpenChange(false)}>
                  Skip These
                </Button>
                <Button
                  onClick={applyToSelected}
                  disabled={selectedIds.size === 0 || isApplying}
                >
                  {isApplying ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Check className="mr-2 h-4 w-4" />
                  )}
                  Update {selectedIds.size} Transaction{selectedIds.size !== 1 ? "s" : ""}
                </Button>
              </div>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
