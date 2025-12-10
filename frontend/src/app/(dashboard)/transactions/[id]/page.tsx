"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Edit,
  Sparkles,
  Building2,
  Calendar,
  DollarSign,
  Tag,
  FileText,
  ArrowRightFromLine,
  ArrowRightToLine,
  MessageSquare,
  Loader2,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";

import { transactions, type Transaction } from "@/lib/api";
import { formatCurrency, formatDate, cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ErrorState, LoadingState } from "@/components/ui/empty-state";

// Confidence badge component
function ConfidenceBadge({ score }: { score?: number }) {
  if (!score) return null;
  const percent = Math.round(score * 100);

  let variant: "default" | "secondary" | "destructive" = "default";
  let label = "High";

  if (percent < 55) {
    variant = "destructive";
    label = "Low";
  } else if (percent < 80) {
    variant = "secondary";
    label = "Medium";
  }

  return (
    <Badge variant={variant} className="gap-1">
      {label} ({percent}%)
    </Badge>
  );
}

export default function TransactionDetailPage() {
  const params = useParams();
  const transactionId = params.id as string;

  // State
  const [transaction, setTransaction] = useState<Transaction | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEnriching, setIsEnriching] = useState(false);

  // Load transaction
  const loadTransaction = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await transactions.get(transactionId);
      if (result.success && result.data) {
        setTransaction(result.data);
      } else {
        throw new Error(result.error?.message || "Failed to load transaction");
      }
    } catch (err) {
      console.error("Failed to load transaction:", err);
      setError(err instanceof Error ? err.message : "Failed to load transaction");
    } finally {
      setIsLoading(false);
    }
  }, [transactionId]);

  useEffect(() => {
    loadTransaction();
  }, [loadTransaction]);

  // Enrich transaction with AI
  async function handleEnrich() {
    setIsEnriching(true);
    try {
      const result = await transactions.enrich(transactionId);
      if (result.success) {
        toast.success("Transaction enriched with AI");
        loadTransaction();
      } else {
        toast.error(result.error?.message || "Failed to enrich transaction");
      }
    } catch {
      toast.error("Failed to enrich transaction");
    } finally {
      setIsEnriching(false);
    }
  }

  if (isLoading) {
    return <LoadingState message="Loading transaction..." />;
  }

  if (error || !transaction) {
    return (
      <ErrorState
        title="Transaction not found"
        description={error || "The transaction you're looking for doesn't exist."}
        onRetry={loadTransaction}
      />
    );
  }

  const isPositive = transaction.amount >= 0;
  const needsReview = transaction.needs_review || (transaction.confidence_score && transaction.confidence_score < 0.55);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="flex items-start gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/dashboard">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold font-heading">
                Transaction Details
              </h1>
              {needsReview && (
                <Badge variant="destructive" className="gap-1">
                  <AlertTriangle className="h-3 w-3" />
                  Needs Review
                </Badge>
              )}
              <ConfidenceBadge score={transaction.confidence_score} />
            </div>
            <p className="text-muted-foreground mt-1 max-w-xl truncate">
              {transaction.description}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 ml-12 md:ml-0">
          <Button
            variant="outline"
            size="sm"
            onClick={handleEnrich}
            disabled={isEnriching}
          >
            {isEnriching ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="mr-2 h-4 w-4" />
            )}
            AI Enrich
          </Button>
          <Button variant="outline" size="sm">
            <Edit className="mr-2 h-4 w-4" />
            Edit
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Info */}
        <div className="lg:col-span-2 space-y-6">
          {/* Transaction Details */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Transaction Details
              </CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid gap-4 sm:grid-cols-2">
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">
                    Date
                  </dt>
                  <dd className="mt-1 flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    {formatDate(transaction.date)}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">
                    Amount
                  </dt>
                  <dd className={cn(
                    "mt-1 flex items-center gap-2 text-lg font-semibold",
                    isPositive ? "text-green-600" : "text-red-600"
                  )}>
                    <DollarSign className="h-4 w-4 text-muted-foreground" />
                    {formatCurrency(transaction.amount, transaction.currency)}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">
                    Currency
                  </dt>
                  <dd className="mt-1">{transaction.currency || "USD"}</dd>
                </div>
                {transaction.entity_name && (
                  <div>
                    <dt className="text-sm font-medium text-muted-foreground">
                      Entity
                    </dt>
                    <dd className="mt-1 flex items-center gap-2">
                      <Building2 className="h-4 w-4 text-muted-foreground" />
                      {transaction.entity_name}
                    </dd>
                  </div>
                )}
                <div className="sm:col-span-2">
                  <dt className="text-sm font-medium text-muted-foreground">
                    Description
                  </dt>
                  <dd className="mt-1">{transaction.description}</dd>
                </div>
              </dl>
            </CardContent>
          </Card>

          {/* Classification */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Tag className="h-5 w-5" />
                Classification
              </CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid gap-4 sm:grid-cols-2">
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">
                    Category
                  </dt>
                  <dd className="mt-1">
                    {transaction.category ? (
                      <Badge variant="secondary">{transaction.category}</Badge>
                    ) : (
                      <span className="text-muted-foreground">Uncategorized</span>
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">
                    Subcategory
                  </dt>
                  <dd className="mt-1">
                    {transaction.subcategory || (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">
                    AI Confidence
                  </dt>
                  <dd className="mt-1">
                    <ConfidenceBadge score={transaction.confidence_score} />
                  </dd>
                </div>
              </dl>
            </CardContent>
          </Card>

          {/* Origin & Destination */}
          {(transaction.origin || transaction.destination) && (
            <Card>
              <CardHeader>
                <CardTitle>Transfer Details</CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="grid gap-4 sm:grid-cols-2">
                  {transaction.origin && (
                    <div>
                      <dt className="text-sm font-medium text-muted-foreground">
                        Origin
                      </dt>
                      <dd className="mt-1 flex items-center gap-2">
                        <ArrowRightFromLine className="h-4 w-4 text-muted-foreground" />
                        {transaction.origin}
                      </dd>
                    </div>
                  )}
                  {transaction.destination && (
                    <div>
                      <dt className="text-sm font-medium text-muted-foreground">
                        Destination
                      </dt>
                      <dd className="mt-1 flex items-center gap-2">
                        <ArrowRightToLine className="h-4 w-4 text-muted-foreground" />
                        {transaction.destination}
                      </dd>
                    </div>
                  )}
                </dl>
              </CardContent>
            </Card>
          )}

          {/* Justification */}
          {transaction.justification && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MessageSquare className="h-5 w-5" />
                  Justification
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p>{transaction.justification}</p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Source Info */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Source
              </CardTitle>
            </CardHeader>
            <CardContent>
              {transaction.source_file ? (
                <div className="p-3 border rounded-lg bg-muted/50">
                  <p className="font-medium truncate">{transaction.source_file}</p>
                </div>
              ) : (
                <p className="text-muted-foreground">Manual entry</p>
              )}
            </CardContent>
          </Card>

          {/* Matched Invoice */}
          {transaction.matched_invoice_id && (
            <Card>
              <CardHeader>
                <CardTitle>Matched Invoice</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="p-3 border rounded-lg bg-green-50 dark:bg-green-900/20">
                  <div className="flex items-center gap-2 text-green-700 dark:text-green-400">
                    <CheckCircle2 className="h-4 w-4" />
                    <span className="font-medium">Matched</span>
                  </div>
                  <p className="text-sm text-muted-foreground mt-1 font-mono truncate">
                    {transaction.matched_invoice_id}
                  </p>
                </div>
                <Button variant="outline" size="sm" className="w-full mt-3" asChild>
                  <Link href={`/invoices/${transaction.matched_invoice_id}`}>
                    View Invoice
                  </Link>
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Timeline */}
          <Card>
            <CardHeader>
              <CardTitle>Timeline</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex gap-3">
                  <div className="flex flex-col items-center">
                    <div className="h-2 w-2 rounded-full bg-primary" />
                    <div className="flex-1 w-px bg-border" />
                  </div>
                  <div className="pb-4">
                    <p className="text-sm font-medium">Transaction Date</p>
                    <p className="text-xs text-muted-foreground">
                      {formatDate(transaction.date)}
                    </p>
                  </div>
                </div>
                <div className="flex gap-3">
                  <div className="flex flex-col items-center">
                    <div className="h-2 w-2 rounded-full bg-primary" />
                    <div className="flex-1 w-px bg-border" />
                  </div>
                  <div className="pb-4">
                    <p className="text-sm font-medium">Created</p>
                    <p className="text-xs text-muted-foreground">
                      {formatDate(transaction.created_at)}
                    </p>
                  </div>
                </div>
                {transaction.updated_at !== transaction.created_at && (
                  <div className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <div className="h-2 w-2 rounded-full bg-primary" />
                    </div>
                    <div>
                      <p className="text-sm font-medium">Updated</p>
                      <p className="text-xs text-muted-foreground">
                        {formatDate(transaction.updated_at)}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Notes */}
          {transaction.notes && (
            <Card>
              <CardHeader>
                <CardTitle>Notes</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm">{transaction.notes}</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
