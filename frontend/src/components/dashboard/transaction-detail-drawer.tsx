"use client";

import { type Transaction } from "@/lib/api";
import { formatCurrency, formatDate, cn } from "@/lib/utils";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Calendar,
  Building2,
  Tag,
  DollarSign,
  FileText,
  Hash,
  Clock,
  ArrowRightFromLine,
  ArrowRightToLine,
} from "lucide-react";

interface TransactionDetailDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  transaction: Transaction | null;
}

export function TransactionDetailDrawer({
  open,
  onOpenChange,
  transaction,
}: TransactionDetailDrawerProps) {
  if (!transaction) return null;

  const confidencePercent = transaction.confidence_score
    ? Math.round(transaction.confidence_score * 100)
    : 0;

  function getConfidenceBadge(score: number) {
    if (score >= 80) {
      return <Badge className="bg-green-600 hover:bg-green-700">High {score}%</Badge>;
    }
    if (score >= 55) {
      return <Badge className="bg-yellow-600 hover:bg-yellow-700">Medium {score}%</Badge>;
    }
    return <Badge className="bg-red-600 hover:bg-red-700">Low {score}%</Badge>;
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[400px] sm:w-[540px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Transaction Details</SheetTitle>
          <SheetDescription>
            Full details for this transaction
          </SheetDescription>
        </SheetHeader>

        <div className="mt-6 space-y-6">
          {/* Amount and Type */}
          <div className="text-center py-4 bg-muted/30 rounded-lg">
            <div
              className={cn(
                "text-3xl font-bold",
                transaction.amount >= 0 ? "text-green-600" : "text-red-600"
              )}
            >
              {formatCurrency(transaction.amount, transaction.currency)}
            </div>
            <div className="text-sm text-muted-foreground mt-1">
              {transaction.amount >= 0 ? "Income" : "Expense"}
            </div>
          </div>

          <Separator />

          {/* Description */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <FileText className="h-4 w-4" />
              Description
            </div>
            <p className="text-sm">{transaction.description || "No description"}</p>
          </div>

          <Separator />

          {/* Details Grid */}
          <div className="grid grid-cols-2 gap-4">
            {/* Date */}
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <Calendar className="h-4 w-4" />
                Date
              </div>
              <p className="text-sm">{formatDate(transaction.date)}</p>
            </div>

            {/* Entity */}
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <Building2 className="h-4 w-4" />
                Entity
              </div>
              <p className="text-sm">{transaction.entity_name || "Unclassified"}</p>
            </div>

            {/* Category */}
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <Tag className="h-4 w-4" />
                Category
              </div>
              <p className="text-sm">{transaction.category || "Uncategorized"}</p>
            </div>

            {/* Subcategory */}
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <Tag className="h-4 w-4" />
                Subcategory
              </div>
              <p className="text-sm">{transaction.subcategory || "-"}</p>
            </div>

            {/* Confidence */}
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <Hash className="h-4 w-4" />
                Confidence
              </div>
              <div>{transaction.confidence_score ? getConfidenceBadge(confidencePercent) : "-"}</div>
            </div>

            {/* Currency */}
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <DollarSign className="h-4 w-4" />
                Currency
              </div>
              <p className="text-sm">{transaction.currency || "USD"}</p>
            </div>
          </div>

          <Separator />

          {/* Origin/Destination */}
          {(transaction.origin || transaction.destination) && (
            <>
              <div className="space-y-3">
                {transaction.origin && (
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                      <ArrowRightFromLine className="h-4 w-4" />
                      Origin
                    </div>
                    <p className="text-sm font-mono text-xs break-all bg-muted/50 p-2 rounded">
                      {transaction.origin}
                    </p>
                  </div>
                )}
                {transaction.destination && (
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                      <ArrowRightToLine className="h-4 w-4" />
                      Destination
                    </div>
                    <p className="text-sm font-mono text-xs break-all bg-muted/50 p-2 rounded">
                      {transaction.destination}
                    </p>
                  </div>
                )}
              </div>
              <Separator />
            </>
          )}

          {/* Justification */}
          {transaction.justification && (
            <>
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                  <FileText className="h-4 w-4" />
                  Justification
                </div>
                <p className="text-sm text-muted-foreground italic">
                  {transaction.justification}
                </p>
              </div>
              <Separator />
            </>
          )}

          {/* Metadata */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <Clock className="h-4 w-4" />
              Metadata
            </div>
            <div className="text-xs text-muted-foreground space-y-1">
              <p>ID: <span className="font-mono">{transaction.id}</span></p>
              {transaction.source_file && (
                <p>Source: {transaction.source_file}</p>
              )}
              {transaction.needs_review && (
                <Badge variant="outline" className="mt-2">Needs Review</Badge>
              )}
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
