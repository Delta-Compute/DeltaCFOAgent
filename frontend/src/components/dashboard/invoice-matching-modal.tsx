"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Loader2, Check, X, FileText, Receipt } from "lucide-react";
import { toast } from "sonner";
import { formatCurrency, formatDate, cn } from "@/lib/utils";

// Types for invoice matching
interface InvoiceMatchData {
  invoice_id: string;
  transaction_id: string;
  score: number;
  match_type?: string;
  explanation?: string;
  invoice?: {
    customer_name?: string;
    invoice_number?: string;
    total_amount?: number;
    currency?: string;
    date?: string;
  };
  transaction?: {
    description?: string;
    amount?: number;
    currency?: string;
    date?: string;
    classified_entity?: string;
  };
}

interface InvoiceMatchingModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  matches: InvoiceMatchData[];
  isLoading: boolean;
  onMatchUpdated: () => void;
}

export function InvoiceMatchingModal({
  open,
  onOpenChange,
  matches,
  isLoading,
  onMatchUpdated,
}: InvoiceMatchingModalProps) {
  const [processingIds, setProcessingIds] = useState<Set<string>>(new Set());

  // Accept a match
  async function handleAccept(match: InvoiceMatchData) {
    const matchKey = `${match.invoice_id}_${match.transaction_id}`;
    setProcessingIds((prev) => new Set(prev).add(matchKey));

    try {
      const response = await fetch("/api/revenue/confirm-match", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          invoice_id: match.invoice_id,
          transaction_id: match.transaction_id,
          customer_name: match.invoice?.customer_name || "",
          invoice_number: match.invoice?.invoice_number || "",
          user_id: "admin",
        }),
      });

      const data = await response.json();

      if (data.success) {
        toast.success("Match accepted! Transaction reclassified as Revenue.");
        onMatchUpdated();
      } else {
        toast.error(data.error || "Failed to accept match");
      }
    } catch {
      toast.error("Failed to accept match");
    } finally {
      setProcessingIds((prev) => {
        const next = new Set(prev);
        next.delete(matchKey);
        return next;
      });
    }
  }

  // Reject a match
  async function handleReject(match: InvoiceMatchData) {
    const matchKey = `${match.invoice_id}_${match.transaction_id}`;
    setProcessingIds((prev) => new Set(prev).add(matchKey));

    try {
      const response = await fetch("/api/revenue/unmatch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          invoice_id: match.invoice_id,
          reason: "User rejected match",
          user_id: "admin",
        }),
      });

      const data = await response.json();

      if (data.success) {
        toast.success("Match rejected");
        onMatchUpdated();
      } else {
        toast.error(data.error || "Failed to reject match");
      }
    } catch {
      toast.error("Failed to reject match");
    } finally {
      setProcessingIds((prev) => {
        const next = new Set(prev);
        next.delete(matchKey);
        return next;
      });
    }
  }

  // Get confidence badge color
  function getConfidenceBadge(score: number) {
    const percent = Math.round(score * 100);
    if (percent >= 80) {
      return (
        <Badge className="bg-green-600 hover:bg-green-700">
          HIGH {percent}%
        </Badge>
      );
    }
    if (percent >= 60) {
      return (
        <Badge className="bg-yellow-600 hover:bg-yellow-700">
          MED {percent}%
        </Badge>
      );
    }
    return (
      <Badge className="bg-red-600 hover:bg-red-700">LOW {percent}%</Badge>
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Receipt className="h-5 w-5" />
            Invoice Matching Results
          </DialogTitle>
          <DialogDescription>
            Review and accept/reject suggested invoice-transaction matches
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-auto">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              <p className="mt-4 text-muted-foreground">
                Running matching algorithm...
              </p>
            </div>
          ) : matches.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12">
              <FileText className="h-12 w-12 text-muted-foreground/50" />
              <p className="mt-4 text-muted-foreground">
                No matches found. All invoices may already be matched or there
                are no eligible transactions.
              </p>
            </div>
          ) : (
            <>
              <div className="mb-4 flex items-center gap-4">
                <Badge variant="outline" className="text-sm">
                  {matches.length} match{matches.length !== 1 ? "es" : ""} found
                </Badge>
              </div>

              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[200px]">Invoice</TableHead>
                      <TableHead className="w-[250px]">Transaction</TableHead>
                      <TableHead className="w-[100px] text-center">
                        Confidence
                      </TableHead>
                      <TableHead>Reason</TableHead>
                      <TableHead className="w-[140px] text-center">
                        Actions
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {matches.map((match) => {
                      const matchKey = `${match.invoice_id}_${match.transaction_id}`;
                      const isProcessing = processingIds.has(matchKey);

                      return (
                        <TableRow key={matchKey}>
                          <TableCell>
                            <div className="space-y-1">
                              <div className="font-medium">
                                {match.invoice?.customer_name || "Unknown"}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                #{match.invoice?.invoice_number || "N/A"}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {formatCurrency(
                                  match.invoice?.total_amount || 0,
                                  match.invoice?.currency
                                )}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {match.invoice?.date ? formatDate(match.invoice.date) : "-"}
                              </div>
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className="space-y-1">
                              <div className="font-medium truncate max-w-[220px]">
                                {match.transaction?.description || "Unknown"}
                              </div>
                              <div
                                className={cn(
                                  "text-xs",
                                  (match.transaction?.amount || 0) >= 0
                                    ? "text-green-600"
                                    : "text-red-600"
                                )}
                              >
                                {formatCurrency(
                                  Math.abs(match.transaction?.amount || 0),
                                  match.transaction?.currency
                                )}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {match.transaction?.date ? formatDate(match.transaction.date) : "-"}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {match.transaction?.classified_entity || "N/A"}
                              </div>
                            </div>
                          </TableCell>
                          <TableCell className="text-center">
                            {getConfidenceBadge(match.score)}
                            <div className="text-xs text-muted-foreground mt-1">
                              {match.match_type || "Auto"}
                            </div>
                          </TableCell>
                          <TableCell>
                            <p className="text-sm text-muted-foreground">
                              {match.explanation ||
                                `Matched based on ${match.match_type || "similarity"}`}
                            </p>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center justify-center gap-1">
                              <Button
                                size="sm"
                                variant="default"
                                className="h-8 bg-green-600 hover:bg-green-700"
                                onClick={() => handleAccept(match)}
                                disabled={isProcessing}
                              >
                                {isProcessing ? (
                                  <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                  <Check className="h-4 w-4" />
                                )}
                              </Button>
                              <Button
                                size="sm"
                                variant="destructive"
                                className="h-8"
                                onClick={() => handleReject(match)}
                                disabled={isProcessing}
                              >
                                {isProcessing ? (
                                  <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                  <X className="h-4 w-4" />
                                )}
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
