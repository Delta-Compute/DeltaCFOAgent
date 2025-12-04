"use client";

import { cva, type VariantProps } from "class-variance-authority";
import {
  CheckCircle2,
  XCircle,
  Clock,
  AlertCircle,
  CircleDot,
  Loader2,
  Ban,
  CheckCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";

// Status badge variants
const statusBadgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium",
  {
    variants: {
      variant: {
        // Success states
        success: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
        completed: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
        paid: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
        active: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
        matched: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",

        // Warning states
        warning: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
        pending: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
        partial: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
        review: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",

        // Danger states
        error: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
        failed: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
        overdue: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
        rejected: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
        cancelled: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",

        // Info states
        info: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
        processing: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
        sent: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",

        // Neutral states
        default: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
        draft: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
        inactive: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

// Status icons
const statusIcons = {
  success: CheckCircle2,
  completed: CheckCircle2,
  paid: CheckCheck,
  active: CheckCircle2,
  matched: CheckCircle2,

  warning: AlertCircle,
  pending: Clock,
  partial: CircleDot,
  review: AlertCircle,

  error: XCircle,
  failed: XCircle,
  overdue: AlertCircle,
  rejected: Ban,
  cancelled: XCircle,

  info: CircleDot,
  processing: Loader2,
  sent: CheckCircle2,

  default: CircleDot,
  draft: CircleDot,
  inactive: Ban,
} as const;

type StatusVariant = keyof typeof statusIcons;

interface StatusBadgeProps extends VariantProps<typeof statusBadgeVariants> {
  children?: React.ReactNode;
  showIcon?: boolean;
  className?: string;
}

export function StatusBadge({
  variant = "default",
  children,
  showIcon = true,
  className,
}: StatusBadgeProps) {
  const Icon = variant ? statusIcons[variant as StatusVariant] : statusIcons.default;
  const isSpinning = variant === "processing";

  return (
    <span className={cn(statusBadgeVariants({ variant }), className)}>
      {showIcon && (
        <Icon className={cn("h-3 w-3", isSpinning && "animate-spin")} />
      )}
      {children}
    </span>
  );
}

// Helper to convert status string to variant
export function getStatusVariant(status: string): StatusVariant {
  const normalized = status.toLowerCase().replace(/[_-]/g, "");

  const statusMap: Record<string, StatusVariant> = {
    // Success
    success: "success",
    completed: "completed",
    complete: "completed",
    paid: "paid",
    active: "active",
    matched: "matched",
    confirmed: "success",
    approved: "success",

    // Warning
    warning: "warning",
    pending: "pending",
    partial: "partial",
    partiallypaid: "partial",
    review: "review",
    needsreview: "review",

    // Danger
    error: "error",
    failed: "failed",
    overdue: "overdue",
    rejected: "rejected",
    cancelled: "cancelled",
    canceled: "cancelled",

    // Info
    info: "info",
    processing: "processing",
    inprogress: "processing",
    sent: "sent",

    // Neutral
    draft: "draft",
    inactive: "inactive",
    disabled: "inactive",
  };

  return statusMap[normalized] || "default";
}
