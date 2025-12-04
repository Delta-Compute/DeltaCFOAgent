"use client";

import { cva, type VariantProps } from "class-variance-authority";
import {
  ChevronUp,
  ChevronDown,
  Minus,
  AlertTriangle,
  Flag,
} from "lucide-react";
import { cn } from "@/lib/utils";

// Priority badge variants
const priorityBadgeVariants = cva(
  "inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium",
  {
    variants: {
      priority: {
        critical: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
        high: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
        medium: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
        normal: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
        low: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
      },
    },
    defaultVariants: {
      priority: "normal",
    },
  }
);

// Priority icons
const priorityIcons = {
  critical: AlertTriangle,
  high: ChevronUp,
  medium: Minus,
  normal: Flag,
  low: ChevronDown,
} as const;

type PriorityLevel = keyof typeof priorityIcons;

interface PriorityBadgeProps extends VariantProps<typeof priorityBadgeVariants> {
  children?: React.ReactNode;
  showIcon?: boolean;
  className?: string;
}

export function PriorityBadge({
  priority = "normal",
  children,
  showIcon = true,
  className,
}: PriorityBadgeProps) {
  const Icon = priority ? priorityIcons[priority as PriorityLevel] : priorityIcons.normal;

  // Default labels
  const labels: Record<PriorityLevel, string> = {
    critical: "Critical",
    high: "High",
    medium: "Medium",
    normal: "Normal",
    low: "Low",
  };

  return (
    <span className={cn(priorityBadgeVariants({ priority }), className)}>
      {showIcon && <Icon className="h-3 w-3" />}
      {children || labels[priority as PriorityLevel]}
    </span>
  );
}

// Helper to convert numeric priority to level
export function getPriorityLevel(priority: number): PriorityLevel {
  if (priority < 100) return "critical";
  if (priority < 500) return "high";
  if (priority < 750) return "medium";
  if (priority < 900) return "normal";
  return "low";
}

// Helper to convert string to priority level
export function normalizePriority(priority: string | number): PriorityLevel {
  if (typeof priority === "number") {
    return getPriorityLevel(priority);
  }

  const normalized = priority.toLowerCase();
  const priorityMap: Record<string, PriorityLevel> = {
    critical: "critical",
    urgent: "critical",
    high: "high",
    important: "high",
    medium: "medium",
    moderate: "medium",
    normal: "normal",
    default: "normal",
    low: "low",
    minor: "low",
  };

  return priorityMap[normalized] || "normal";
}
