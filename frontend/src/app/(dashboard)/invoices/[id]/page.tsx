"use client";

import { useState, useEffect, useCallback, useRef } from "react";
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
  Upload,
  Plus,
  Receipt,
  CreditCard,
  X,
} from "lucide-react";
import { toast } from "sonner";

import {
  invoices,
  type Invoice,
  type MatchResult,
  type InvoicePayment,
  type InvoiceAttachment,
  type AddPaymentData,
} from "@/lib/api";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
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
  const [showAddPaymentDialog, setShowAddPaymentDialog] = useState(false);

  // Matching
  const [matches, setMatches] = useState<MatchResult[]>([]);
  const [isLoadingMatches, setIsLoadingMatches] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  // Payments
  const [payments, setPayments] = useState<InvoicePayment[]>([]);
  const [isLoadingPayments, setIsLoadingPayments] = useState(false);
  const [newPayment, setNewPayment] = useState<AddPaymentData>({
    payment_date: new Date().toISOString().split("T")[0],
    amount: 0,
    payment_method: "",
    reference_number: "",
    notes: "",
  });

  // File uploads
  const attachmentInputRef = useRef<HTMLInputElement>(null);
  const receiptInputRef = useRef<HTMLInputElement>(null);
  const [isUploadingAttachment, setIsUploadingAttachment] = useState(false);
  const [isUploadingReceipt, setIsUploadingReceipt] = useState(false);
  const [uploadingReceiptForPayment, setUploadingReceiptForPayment] = useState<string | null>(null);

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

  // Load payments
  const loadPayments = useCallback(async () => {
    setIsLoadingPayments(true);
    try {
      const result = await invoices.getPayments(invoiceId);
      if (result.success && result.data) {
        setPayments(result.data);
      }
    } catch (err) {
      console.error("Failed to load payments:", err);
    } finally {
      setIsLoadingPayments(false);
    }
  }, [invoiceId]);

  useEffect(() => {
    if (invoiceId) {
      loadPayments();
    }
  }, [invoiceId, loadPayments]);

  // Upload attachment
  async function handleAttachmentUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploadingAttachment(true);
    try {
      const result = await invoices.uploadAttachment(invoiceId, file);
      if (result.success) {
        toast.success("Attachment uploaded successfully");
        loadInvoice();
      } else {
        toast.error(result.error?.message || "Failed to upload attachment");
      }
    } catch {
      toast.error("Failed to upload attachment");
    } finally {
      setIsUploadingAttachment(false);
      if (attachmentInputRef.current) {
        attachmentInputRef.current.value = "";
      }
    }
  }

  // Delete attachment
  async function handleDeleteAttachment(attachmentId: string) {
    setIsProcessing(true);
    try {
      const result = await invoices.deleteAttachment(invoiceId, attachmentId);
      if (result.success) {
        toast.success("Attachment deleted");
        loadInvoice();
      } else {
        toast.error(result.error?.message || "Failed to delete attachment");
      }
    } catch {
      toast.error("Failed to delete attachment");
    } finally {
      setIsProcessing(false);
    }
  }

  // Add payment
  async function handleAddPayment() {
    if (!newPayment.amount || newPayment.amount <= 0) {
      toast.error("Please enter a valid payment amount");
      return;
    }

    setIsProcessing(true);
    try {
      const result = await invoices.addPayment(invoiceId, {
        ...newPayment,
        currency: invoice?.currency,
      });
      if (result.success) {
        toast.success("Payment recorded successfully");
        setShowAddPaymentDialog(false);
        setNewPayment({
          payment_date: new Date().toISOString().split("T")[0],
          amount: 0,
          payment_method: "",
          reference_number: "",
          notes: "",
        });
        loadPayments();
        loadInvoice();
      } else {
        toast.error(result.error?.message || "Failed to record payment");
      }
    } catch {
      toast.error("Failed to record payment");
    } finally {
      setIsProcessing(false);
    }
  }

  // Delete payment
  async function handleDeletePayment(paymentId: string) {
    setIsProcessing(true);
    try {
      const result = await invoices.deletePayment(invoiceId, paymentId);
      if (result.success) {
        toast.success("Payment deleted");
        loadPayments();
        loadInvoice();
      } else {
        toast.error(result.error?.message || "Failed to delete payment");
      }
    } catch {
      toast.error("Failed to delete payment");
    } finally {
      setIsProcessing(false);
    }
  }

  // Upload payment receipt
  async function handleReceiptUpload(paymentId: string, e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploadingReceipt(true);
    setUploadingReceiptForPayment(paymentId);
    try {
      const result = await invoices.uploadPaymentReceipt(invoiceId, paymentId, file);
      if (result.success) {
        toast.success("Receipt uploaded successfully");
        loadPayments();
      } else {
        toast.error(result.error?.message || "Failed to upload receipt");
      }
    } catch {
      toast.error("Failed to upload receipt");
    } finally {
      setIsUploadingReceipt(false);
      setUploadingReceiptForPayment(null);
      if (receiptInputRef.current) {
        receiptInputRef.current.value = "";
      }
    }
  }

  // Calculate total paid
  const totalPaid = payments.reduce((sum, p) => sum + p.amount, 0);
  const remainingBalance = invoice ? invoice.total_amount - totalPaid : 0;

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
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Attachments</CardTitle>
                <CardDescription>
                  {invoice.attachments?.length || 0} file
                  {(invoice.attachments?.length || 0) !== 1 ? "s" : ""}
                </CardDescription>
              </div>
              <div>
                <input
                  ref={attachmentInputRef}
                  type="file"
                  className="hidden"
                  accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg"
                  onChange={handleAttachmentUpload}
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => attachmentInputRef.current?.click()}
                  disabled={isUploadingAttachment}
                >
                  {isUploadingAttachment ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Upload className="mr-2 h-4 w-4" />
                  )}
                  Upload
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {invoice.attachments && invoice.attachments.length > 0 ? (
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
                      <div className="flex items-center gap-2">
                        <Button variant="ghost" size="sm" asChild>
                          <a
                            href={attachment.url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <Download className="h-4 w-4" />
                          </a>
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:text-destructive"
                          onClick={() => handleDeleteAttachment(attachment.id)}
                          disabled={isProcessing}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-6 text-muted-foreground">
                  <FileText className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No attachments yet</p>
                  <p className="text-xs">Upload invoices, contracts, or receipts</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Payments */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <CreditCard className="h-5 w-5" />
                  Payment History
                </CardTitle>
                <CardDescription>
                  {payments.length} payment{payments.length !== 1 ? "s" : ""} recorded
                </CardDescription>
              </div>
              {invoice.status !== "paid" && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setNewPayment({
                      payment_date: new Date().toISOString().split("T")[0],
                      amount: remainingBalance > 0 ? remainingBalance : invoice.total_amount,
                      payment_method: "",
                      reference_number: "",
                      notes: "",
                    });
                    setShowAddPaymentDialog(true);
                  }}
                >
                  <Plus className="mr-2 h-4 w-4" />
                  Add Payment
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {/* Payment Summary */}
              {payments.length > 0 && (
                <div className="mb-4 p-3 bg-muted/50 rounded-lg">
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <p className="text-muted-foreground">Total</p>
                      <p className="font-semibold">
                        {formatCurrency(invoice.total_amount, invoice.currency)}
                      </p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Paid</p>
                      <p className="font-semibold text-green-600">
                        {formatCurrency(totalPaid, invoice.currency)}
                      </p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Balance</p>
                      <p className={cn(
                        "font-semibold",
                        remainingBalance > 0 ? "text-orange-600" : "text-green-600"
                      )}>
                        {formatCurrency(remainingBalance, invoice.currency)}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {isLoadingPayments ? (
                <div className="flex items-center justify-center py-6">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : payments.length > 0 ? (
                <div className="space-y-3">
                  {payments.map((payment) => (
                    <div
                      key={payment.id}
                      className="flex items-start justify-between p-3 border rounded-lg"
                    >
                      <div className="flex items-start gap-3">
                        <div className="p-2 bg-green-100 dark:bg-green-900/20 rounded-full">
                          <CheckCircle2 className="h-4 w-4 text-green-600" />
                        </div>
                        <div>
                          <p className="font-medium">
                            {formatCurrency(payment.amount, payment.currency)}
                          </p>
                          <p className="text-sm text-muted-foreground">
                            {formatDate(payment.payment_date)}
                            {payment.payment_method && ` - ${payment.payment_method}`}
                          </p>
                          {payment.reference_number && (
                            <p className="text-xs text-muted-foreground font-mono">
                              Ref: {payment.reference_number}
                            </p>
                          )}
                          {payment.notes && (
                            <p className="text-xs text-muted-foreground mt-1">
                              {payment.notes}
                            </p>
                          )}
                          {payment.receipt && (
                            <a
                              href={payment.receipt.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 text-xs text-primary mt-1 hover:underline"
                            >
                              <Receipt className="h-3 w-3" />
                              {payment.receipt.filename}
                            </a>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-1">
                        {!payment.receipt && (
                          <>
                            <input
                              ref={receiptInputRef}
                              type="file"
                              className="hidden"
                              accept=".pdf,.png,.jpg,.jpeg"
                              onChange={(e) => handleReceiptUpload(payment.id, e)}
                            />
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setUploadingReceiptForPayment(payment.id);
                                receiptInputRef.current?.click();
                              }}
                              disabled={isUploadingReceipt}
                            >
                              {isUploadingReceipt && uploadingReceiptForPayment === payment.id ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <Receipt className="h-4 w-4" />
                              )}
                            </Button>
                          </>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:text-destructive"
                          onClick={() => handleDeletePayment(payment.id)}
                          disabled={isProcessing}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-6 text-muted-foreground">
                  <CreditCard className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No payments recorded</p>
                  <p className="text-xs">Add a payment when received</p>
                </div>
              )}
            </CardContent>
          </Card>
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

      {/* Add Payment Dialog */}
      <Dialog open={showAddPaymentDialog} onOpenChange={setShowAddPaymentDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Record Payment</DialogTitle>
            <DialogDescription>
              Record a payment for invoice {invoice.invoice_number}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="payment_date">Payment Date</Label>
                <Input
                  id="payment_date"
                  type="date"
                  value={newPayment.payment_date}
                  onChange={(e) =>
                    setNewPayment({ ...newPayment, payment_date: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="amount">Amount ({invoice.currency})</Label>
                <Input
                  id="amount"
                  type="number"
                  step="0.01"
                  min="0"
                  value={newPayment.amount || ""}
                  onChange={(e) =>
                    setNewPayment({
                      ...newPayment,
                      amount: parseFloat(e.target.value) || 0,
                    })
                  }
                  placeholder="0.00"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="payment_method">Payment Method</Label>
              <Select
                value={newPayment.payment_method || ""}
                onValueChange={(value) =>
                  setNewPayment({ ...newPayment, payment_method: value })
                }
              >
                <SelectTrigger id="payment_method">
                  <SelectValue placeholder="Select method" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="bank_transfer">Bank Transfer</SelectItem>
                  <SelectItem value="credit_card">Credit Card</SelectItem>
                  <SelectItem value="check">Check</SelectItem>
                  <SelectItem value="cash">Cash</SelectItem>
                  <SelectItem value="crypto">Cryptocurrency</SelectItem>
                  <SelectItem value="other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="reference_number">Reference Number (optional)</Label>
              <Input
                id="reference_number"
                value={newPayment.reference_number || ""}
                onChange={(e) =>
                  setNewPayment({ ...newPayment, reference_number: e.target.value })
                }
                placeholder="Transaction ID, check number, etc."
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="notes">Notes (optional)</Label>
              <Textarea
                id="notes"
                value={newPayment.notes || ""}
                onChange={(e) =>
                  setNewPayment({ ...newPayment, notes: e.target.value })
                }
                placeholder="Any additional notes about this payment"
                rows={2}
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowAddPaymentDialog(false)}
              disabled={isProcessing}
            >
              Cancel
            </Button>
            <Button onClick={handleAddPayment} disabled={isProcessing}>
              {isProcessing ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Plus className="mr-2 h-4 w-4" />
              )}
              Record Payment
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
