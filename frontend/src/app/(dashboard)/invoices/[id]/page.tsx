"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Edit,
  Trash2,
  CheckCircle2,
  Clock,
  AlertCircle,
  FileText,
  Building2,
  Calendar,
  DollarSign,
  Link2,
  Unlink,
  Download,
  Loader2,
  ExternalLink,
} from "lucide-react";
import { toast } from "sonner";

import { invoices, type Invoice, type MatchResult } from "@/lib/api";
import { formatCurrency, formatDate, cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ErrorState, LoadingState } from "@/components/ui/empty-state";

// Status badge component
function StatusBadge({ status }: { status: Invoice["status"] }) {
  const config: Record<
    Invoice["status"],
    { label: string; variant: "outline" | "secondary" | "default" | "destructive"; icon: typeof Edit }
  > = {
    draft: { label: "Draft", variant: "outline", icon: Edit },
    sent: { label: "Sent", variant: "secondary", icon: Clock },
    paid: { label: "Paid", variant: "default", icon: CheckCircle2 },
    partial: { label: "Partial", variant: "secondary", icon: Clock },
    overdue: { label: "Overdue", variant: "destructive", icon: AlertCircle },
  };

  const statusConfig = config[status] || config.draft;
  const { label, variant, icon: Icon } = statusConfig;

  return (
    <Badge variant={variant} className="gap-1">
      <Icon className="h-3 w-3" />
      {label}
    </Badge>
  );
}

export default function InvoiceDetailPage() {
  const router = useRouter();
  const params = useParams();
  const invoiceId = params.id as string;

  // State
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Dialogs
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showMarkPaidDialog, setShowMarkPaidDialog] = useState(false);
  const [showMatchDialog, setShowMatchDialog] = useState(false);

  // Matching
  const [matches, setMatches] = useState<MatchResult[]>([]);
  const [isLoadingMatches, setIsLoadingMatches] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  // Load invoice
  const loadInvoice = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await invoices.get(invoiceId);
      if (result.success && result.data) {
        setInvoice(result.data);
      } else {
        throw new Error(result.error?.message || "Failed to load invoice");
      }
    } catch (err) {
      console.error("Failed to load invoice:", err);
      setError(err instanceof Error ? err.message : "Failed to load invoice");
    } finally {
      setIsLoading(false);
    }
  }, [invoiceId]);

  useEffect(() => {
    loadInvoice();
  }, [loadInvoice]);

  // Find matching transactions
  async function findMatches() {
    setIsLoadingMatches(true);
    try {
      const result = await invoices.findMatches(invoiceId);
      if (result.success && result.data) {
        setMatches(result.data);
        setShowMatchDialog(true);
      } else {
        toast.error(result.error?.message || "Failed to find matches");
      }
    } catch {
      toast.error("Failed to find matches");
    } finally {
      setIsLoadingMatches(false);
    }
  }

  // Link transaction
  async function linkTransaction(transactionId: string) {
    setIsProcessing(true);
    try {
      const result = await invoices.linkTransaction(invoiceId, transactionId);
      if (result.success) {
        toast.success("Transaction linked successfully");
        setShowMatchDialog(false);
        loadInvoice();
      } else {
        toast.error(result.error?.message || "Failed to link transaction");
      }
    } catch {
      toast.error("Failed to link transaction");
    } finally {
      setIsProcessing(false);
    }
  }

  // Mark as paid
  async function markAsPaid() {
    if (!invoice) return;
    setIsProcessing(true);
    try {
      const result = await invoices.markPaid(invoiceId, {
        payment_date: new Date().toISOString().split("T")[0],
        payment_amount: invoice.total_amount,
      });
      if (result.success) {
        toast.success("Invoice marked as paid");
        setShowMarkPaidDialog(false);
        loadInvoice();
      } else {
        toast.error(result.error?.message || "Failed to mark as paid");
      }
    } catch {
      toast.error("Failed to mark as paid");
    } finally {
      setIsProcessing(false);
    }
  }

  // Delete invoice
  async function handleDelete() {
    setIsProcessing(true);
    try {
      const result = await invoices.delete(invoiceId);
      if (result.success) {
        toast.success("Invoice deleted");
        router.push("/invoices");
      } else {
        toast.error(result.error?.message || "Failed to delete invoice");
      }
    } catch {
      toast.error("Failed to delete invoice");
    } finally {
      setIsProcessing(false);
    }
  }

  if (isLoading) {
    return <LoadingState message="Loading invoice..." />;
  }

  if (error || !invoice) {
    return (
      <ErrorState
        title="Invoice not found"
        description={error || "The invoice you're looking for doesn't exist."}
        onRetry={loadInvoice}
      />
    );
  }

  const isOverdue =
    invoice.status !== "paid" && new Date(invoice.due_date) < new Date();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="flex items-start gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/invoices">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold font-heading font-mono">
                {invoice.invoice_number}
              </h1>
              <StatusBadge status={invoice.status} />
            </div>
            <p className="text-muted-foreground mt-1">
              {invoice.vendor_name}
              {invoice.client_name && ` - ${invoice.client_name}`}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 ml-12 md:ml-0">
          <Button
            variant="outline"
            size="sm"
            onClick={findMatches}
            disabled={isLoadingMatches || invoice.status === "paid"}
          >
            {isLoadingMatches ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Link2 className="mr-2 h-4 w-4" />
            )}
            Find Matches
          </Button>
          {invoice.status !== "paid" && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowMarkPaidDialog(true)}
            >
              <CheckCircle2 className="mr-2 h-4 w-4" />
              Mark Paid
            </Button>
          )}
          <Button variant="outline" size="sm" asChild>
            <Link href={`/invoices/${invoiceId}/edit`}>
              <Edit className="mr-2 h-4 w-4" />
              Edit
            </Link>
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="text-destructive hover:text-destructive"
            onClick={() => setShowDeleteDialog(true)}
          >
            <Trash2 className="mr-2 h-4 w-4" />
            Delete
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Info */}
        <div className="lg:col-span-2 space-y-6">
          {/* Invoice Details */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Invoice Details
              </CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid gap-4 sm:grid-cols-2">
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">
                    Vendor
                  </dt>
                  <dd className="mt-1 flex items-center gap-2">
                    <Building2 className="h-4 w-4 text-muted-foreground" />
                    {invoice.vendor_name}
                  </dd>
                </div>
                {invoice.client_name && (
                  <div>
                    <dt className="text-sm font-medium text-muted-foreground">
                      Client
                    </dt>
                    <dd className="mt-1 flex items-center gap-2">
                      <Building2 className="h-4 w-4 text-muted-foreground" />
                      {invoice.client_name}
                    </dd>
                  </div>
                )}
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">
                    Issue Date
                  </dt>
                  <dd className="mt-1 flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    {formatDate(invoice.issue_date)}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">
                    Due Date
                  </dt>
                  <dd
                    className={cn(
                      "mt-1 flex items-center gap-2",
                      isOverdue && "text-red-600"
                    )}
                  >
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    {formatDate(invoice.due_date)}
                    {isOverdue && (
                      <Badge variant="destructive" className="ml-2">
                        Overdue
                      </Badge>
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">
                    Total Amount
                  </dt>
                  <dd className="mt-1 flex items-center gap-2 text-lg font-semibold">
                    <DollarSign className="h-4 w-4 text-muted-foreground" />
                    {formatCurrency(invoice.total_amount, invoice.currency)}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">
                    Currency
                  </dt>
                  <dd className="mt-1">{invoice.currency}</dd>
                </div>
              </dl>
            </CardContent>
          </Card>

          {/* Line Items */}
          {invoice.line_items && invoice.line_items.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Line Items</CardTitle>
                <CardDescription>
                  {invoice.line_items.length} item
                  {invoice.line_items.length !== 1 ? "s" : ""}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Description</TableHead>
                      <TableHead className="text-right w-[100px]">Qty</TableHead>
                      <TableHead className="text-right w-[120px]">
                        Unit Price
                      </TableHead>
                      <TableHead className="text-right w-[120px]">Total</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {invoice.line_items.map((item, index) => (
                      <TableRow key={index}>
                        <TableCell>{item.description}</TableCell>
                        <TableCell className="text-right">
                          {item.quantity}
                        </TableCell>
                        <TableCell className="text-right">
                          {formatCurrency(item.unit_price, invoice.currency)}
                        </TableCell>
                        <TableCell className="text-right font-medium">
                          {formatCurrency(item.total, invoice.currency)}
                        </TableCell>
                      </TableRow>
                    ))}
                    <TableRow className="bg-muted/50">
                      <TableCell colSpan={3} className="font-semibold">
                        Total
                      </TableCell>
                      <TableCell className="text-right font-bold">
                        {formatCurrency(invoice.total_amount, invoice.currency)}
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}

          {/* Attachments */}
          {invoice.attachments && invoice.attachments.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Attachments</CardTitle>
                <CardDescription>
                  {invoice.attachments.length} file
                  {invoice.attachments.length !== 1 ? "s" : ""}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {invoice.attachments.map((attachment) => (
                    <div
                      key={attachment.id}
                      className="flex items-center justify-between p-3 border rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <FileText className="h-5 w-5 text-muted-foreground" />
                        <div>
                          <p className="font-medium">{attachment.filename}</p>
                          <p className="text-xs text-muted-foreground">
                            Uploaded {formatDate(attachment.uploaded_at)}
                          </p>
                        </div>
                      </div>
                      <Button variant="ghost" size="sm" asChild>
                        <a
                          href={attachment.url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <Download className="mr-2 h-4 w-4" />
                          Download
                        </a>
                      </Button>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Matched Transaction */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Link2 className="h-5 w-5" />
                Linked Transaction
              </CardTitle>
            </CardHeader>
            <CardContent>
              {invoice.matched_transaction_id ? (
                <div className="space-y-3">
                  <div className="p-3 border rounded-lg bg-green-50 dark:bg-green-900/20">
                    <div className="flex items-center gap-2 text-green-700 dark:text-green-400">
                      <CheckCircle2 className="h-4 w-4" />
                      <span className="font-medium">Matched</span>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1 font-mono">
                      {invoice.matched_transaction_id}
                    </p>
                  </div>
                  <Button variant="outline" size="sm" className="w-full" asChild>
                    <Link href={`/transactions/${invoice.matched_transaction_id}`}>
                      <ExternalLink className="mr-2 h-4 w-4" />
                      View Transaction
                    </Link>
                  </Button>
                </div>
              ) : (
                <div className="text-center py-4">
                  <Unlink className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
                  <p className="text-sm text-muted-foreground">
                    No transaction linked
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-3"
                    onClick={findMatches}
                    disabled={isLoadingMatches}
                  >
                    {isLoadingMatches ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Link2 className="mr-2 h-4 w-4" />
                    )}
                    Find Matches
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

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
                    <p className="text-sm font-medium">Created</p>
                    <p className="text-xs text-muted-foreground">
                      {formatDate(invoice.created_at)}
                    </p>
                  </div>
                </div>
                {invoice.updated_at !== invoice.created_at && (
                  <div className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <div className="h-2 w-2 rounded-full bg-primary" />
                      <div className="flex-1 w-px bg-border" />
                    </div>
                    <div className="pb-4">
                      <p className="text-sm font-medium">Updated</p>
                      <p className="text-xs text-muted-foreground">
                        {formatDate(invoice.updated_at)}
                      </p>
                    </div>
                  </div>
                )}
                {invoice.status === "paid" && (
                  <div className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <div className="h-2 w-2 rounded-full bg-green-500" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-green-600">Paid</p>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Invoice</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete invoice {invoice.invoice_number}?
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowDeleteDialog(false)}
              disabled={isProcessing}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={isProcessing}
            >
              {isProcessing ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="mr-2 h-4 w-4" />
              )}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Mark Paid Dialog */}
      <Dialog open={showMarkPaidDialog} onOpenChange={setShowMarkPaidDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Mark as Paid</DialogTitle>
            <DialogDescription>
              Mark invoice {invoice.invoice_number} as paid for{" "}
              {formatCurrency(invoice.total_amount, invoice.currency)}?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowMarkPaidDialog(false)}
              disabled={isProcessing}
            >
              Cancel
            </Button>
            <Button onClick={markAsPaid} disabled={isProcessing}>
              {isProcessing ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <CheckCircle2 className="mr-2 h-4 w-4" />
              )}
              Mark Paid
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Match Dialog */}
      <Dialog open={showMatchDialog} onOpenChange={setShowMatchDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Matching Transactions</DialogTitle>
            <DialogDescription>
              {matches.length > 0
                ? `Found ${matches.length} potential matching transaction${matches.length !== 1 ? "s" : ""}`
                : "No matching transactions found"}
            </DialogDescription>
          </DialogHeader>
          {matches.length > 0 ? (
            <div className="max-h-[400px] overflow-y-auto space-y-3">
              {matches.map((match) => (
                <div
                  key={match.transaction_id}
                  className="p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">
                          {formatCurrency(
                            match.transaction.amount,
                            match.transaction.currency
                          )}
                        </span>
                        <Badge variant="outline">
                          {Math.round(match.confidence_score * 100)}% match
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">
                        {match.transaction.description}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {formatDate(match.transaction.date)}
                      </p>
                      {match.match_reasons.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {match.match_reasons.map((reason, i) => (
                            <Badge key={i} variant="secondary" className="text-xs">
                              {reason}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                    <Button
                      size="sm"
                      onClick={() => linkTransaction(match.transaction_id)}
                      disabled={isProcessing}
                    >
                      {isProcessing ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        "Link"
                      )}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Unlink className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
              <p className="text-muted-foreground">
                No transactions match this invoice amount and date range.
              </p>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowMatchDialog(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
