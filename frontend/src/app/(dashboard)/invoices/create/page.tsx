"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm, useFieldArray } from "react-hook-form";
import {
  ArrowLeft,
  Plus,
  Trash2,
  Save,
  Loader2,
  FileText,
  Calculator,
} from "lucide-react";
import { toast } from "sonner";

import { invoices, type CreateInvoiceData, type InvoiceLineItem } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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

// Form data type
interface InvoiceFormData {
  invoice_number: string;
  vendor_name: string;
  client_name: string;
  issue_date: string;
  due_date: string;
  currency: string;
  line_items: {
    description: string;
    quantity: number;
    unit_price: number;
  }[];
}

// Available currencies
const currencies = [
  { code: "USD", name: "US Dollar" },
  { code: "EUR", name: "Euro" },
  { code: "GBP", name: "British Pound" },
  { code: "BRL", name: "Brazilian Real" },
  { code: "JPY", name: "Japanese Yen" },
  { code: "CAD", name: "Canadian Dollar" },
  { code: "AUD", name: "Australian Dollar" },
  { code: "CHF", name: "Swiss Franc" },
];

export default function CreateInvoicePage() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form setup
  const {
    register,
    control,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<InvoiceFormData>({
    defaultValues: {
      invoice_number: "",
      vendor_name: "",
      client_name: "",
      issue_date: new Date().toISOString().split("T")[0],
      due_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000)
        .toISOString()
        .split("T")[0],
      currency: "USD",
      line_items: [{ description: "", quantity: 1, unit_price: 0 }],
    },
  });

  // Line items array
  const { fields, append, remove } = useFieldArray({
    control,
    name: "line_items",
  });

  // Watch line items for total calculation
  const watchLineItems = watch("line_items");
  const watchCurrency = watch("currency");

  // Calculate totals
  const lineItemTotals = watchLineItems.map(
    (item) => (item.quantity || 0) * (item.unit_price || 0)
  );
  const totalAmount = lineItemTotals.reduce((sum, total) => sum + total, 0);

  // Submit form
  async function onSubmit(data: InvoiceFormData) {
    setIsSubmitting(true);

    try {
      // Transform line items to include totals
      const lineItems: InvoiceLineItem[] = data.line_items
        .filter((item) => item.description.trim() !== "")
        .map((item) => ({
          description: item.description,
          quantity: item.quantity,
          unit_price: item.unit_price,
          total: item.quantity * item.unit_price,
        }));

      const invoiceData: CreateInvoiceData = {
        invoice_number: data.invoice_number,
        vendor_name: data.vendor_name,
        client_name: data.client_name || undefined,
        issue_date: data.issue_date,
        due_date: data.due_date,
        total_amount: totalAmount,
        currency: data.currency,
        line_items: lineItems.length > 0 ? lineItems : undefined,
      };

      const result = await invoices.create(invoiceData);

      if (result.success && result.data) {
        toast.success("Invoice created successfully");
        router.push(`/invoices/${result.data.id}`);
      } else {
        toast.error(result.error?.message || "Failed to create invoice");
      }
    } catch {
      toast.error("Failed to create invoice");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/invoices">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div>
          <h1 className="text-2xl font-bold font-heading">Create Invoice</h1>
          <p className="text-muted-foreground">
            Create a new invoice for your records
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Main Form */}
          <div className="lg:col-span-2 space-y-6">
            {/* Basic Information */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  Invoice Information
                </CardTitle>
                <CardDescription>
                  Enter the basic invoice details
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="invoice_number">Invoice Number *</Label>
                    <Input
                      id="invoice_number"
                      placeholder="INV-001"
                      {...register("invoice_number", {
                        required: "Invoice number is required",
                      })}
                    />
                    {errors.invoice_number && (
                      <p className="text-sm text-destructive">
                        {errors.invoice_number.message}
                      </p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="currency">Currency *</Label>
                    <Select
                      defaultValue="USD"
                      onValueChange={(value) => {
                        const event = {
                          target: { name: "currency", value },
                        };
                        register("currency").onChange(event);
                      }}
                    >
                      <SelectTrigger id="currency">
                        <SelectValue placeholder="Select currency" />
                      </SelectTrigger>
                      <SelectContent>
                        {currencies.map((currency) => (
                          <SelectItem key={currency.code} value={currency.code}>
                            {currency.code} - {currency.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="vendor_name">Vendor Name *</Label>
                    <Input
                      id="vendor_name"
                      placeholder="Vendor or Company Name"
                      {...register("vendor_name", {
                        required: "Vendor name is required",
                      })}
                    />
                    {errors.vendor_name && (
                      <p className="text-sm text-destructive">
                        {errors.vendor_name.message}
                      </p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="client_name">Client Name</Label>
                    <Input
                      id="client_name"
                      placeholder="Client (optional)"
                      {...register("client_name")}
                    />
                  </div>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="issue_date">Issue Date *</Label>
                    <Input
                      id="issue_date"
                      type="date"
                      {...register("issue_date", {
                        required: "Issue date is required",
                      })}
                    />
                    {errors.issue_date && (
                      <p className="text-sm text-destructive">
                        {errors.issue_date.message}
                      </p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="due_date">Due Date *</Label>
                    <Input
                      id="due_date"
                      type="date"
                      {...register("due_date", {
                        required: "Due date is required",
                      })}
                    />
                    {errors.due_date && (
                      <p className="text-sm text-destructive">
                        {errors.due_date.message}
                      </p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Line Items */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <Calculator className="h-5 w-5" />
                      Line Items
                    </CardTitle>
                    <CardDescription>
                      Add items to the invoice
                    </CardDescription>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      append({ description: "", quantity: 1, unit_price: 0 })
                    }
                  >
                    <Plus className="mr-2 h-4 w-4" />
                    Add Item
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Description</TableHead>
                      <TableHead className="w-[100px]">Qty</TableHead>
                      <TableHead className="w-[150px]">Unit Price</TableHead>
                      <TableHead className="w-[120px] text-right">Total</TableHead>
                      <TableHead className="w-[50px]" />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {fields.map((field, index) => (
                      <TableRow key={field.id}>
                        <TableCell>
                          <Input
                            placeholder="Item description"
                            {...register(`line_items.${index}.description`)}
                          />
                        </TableCell>
                        <TableCell>
                          <Input
                            type="number"
                            min="0"
                            step="1"
                            {...register(`line_items.${index}.quantity`, {
                              valueAsNumber: true,
                            })}
                          />
                        </TableCell>
                        <TableCell>
                          <Input
                            type="number"
                            min="0"
                            step="0.01"
                            {...register(`line_items.${index}.unit_price`, {
                              valueAsNumber: true,
                            })}
                          />
                        </TableCell>
                        <TableCell className="text-right font-medium">
                          {formatCurrency(lineItemTotals[index] || 0, watchCurrency)}
                        </TableCell>
                        <TableCell>
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            onClick={() => remove(index)}
                            disabled={fields.length === 1}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                    <TableRow className="bg-muted/50">
                      <TableCell colSpan={3} className="font-semibold">
                        Total
                      </TableCell>
                      <TableCell className="text-right font-bold text-lg">
                        {formatCurrency(totalAmount, watchCurrency)}
                      </TableCell>
                      <TableCell />
                    </TableRow>
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Summary */}
            <Card>
              <CardHeader>
                <CardTitle>Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Items</span>
                  <span>{fields.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Currency</span>
                  <span>{watchCurrency}</span>
                </div>
                <div className="border-t pt-4">
                  <div className="flex justify-between text-lg font-semibold">
                    <span>Total</span>
                    <span>{formatCurrency(totalAmount, watchCurrency)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Actions */}
            <Card>
              <CardContent className="pt-6">
                <div className="space-y-3">
                  <Button
                    type="submit"
                    className="w-full"
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Save className="mr-2 h-4 w-4" />
                    )}
                    Create Invoice
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    className="w-full"
                    onClick={() => router.push("/invoices")}
                    disabled={isSubmitting}
                  >
                    Cancel
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </form>
    </div>
  );
}
