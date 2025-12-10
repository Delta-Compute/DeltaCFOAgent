import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge Tailwind CSS classes with clsx and tailwind-merge
 * This is the standard utility used by shadcn/ui components
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format a number as currency
 */
export function formatCurrency(
  amount: number,
  currency: string = "USD",
  locale: string = "en-US"
): string {
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

/**
 * Format a date
 */
export function formatDate(
  date: Date | string,
  options: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "short",
    day: "numeric",
  },
  locale: string = "en-US"
): string {
  const d = typeof date === "string" ? new Date(date) : date;
  return new Intl.DateTimeFormat(locale, options).format(d);
}

/**
 * Format a number with thousands separators
 */
export function formatNumber(
  value: number,
  locale: string = "en-US"
): string {
  return new Intl.NumberFormat(locale).format(value);
}

/**
 * Format a percentage
 */
export function formatPercent(
  value: number,
  decimals: number = 1,
  locale: string = "en-US"
): string {
  return new Intl.NumberFormat(locale, {
    style: "percent",
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value / 100);
}

/**
 * Truncate text with ellipsis
 */
export function truncate(str: string, length: number): string {
  if (str.length <= length) return str;
  return str.slice(0, length) + "...";
}

/**
 * Generate initials from a name
 */
export function getInitials(name: string): string {
  return name
    .split(" ")
    .map((word) => word[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

/**
 * Delay execution for a specified time
 */
export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Check if a value is empty (null, undefined, empty string, or empty array)
 */
export function isEmpty(value: unknown): boolean {
  if (value === null || value === undefined) return true;
  if (typeof value === "string") return value.trim() === "";
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === "object") return Object.keys(value).length === 0;
  return false;
}

/**
 * Debounce a function
 */
export function debounce<T extends (...args: unknown[]) => unknown>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null;

  return function executedFunction(...args: Parameters<T>) {
    const later = () => {
      timeout = null;
      func(...args);
    };

    if (timeout) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(later, wait);
  };
}

/**
 * Get confidence level from score
 */
export function getConfidenceLevel(score: number): "high" | "medium" | "low" {
  if (score >= 0.8) return "high";
  if (score >= 0.55) return "medium";
  return "low";
}

/**
 * Get confidence color class
 */
export function getConfidenceColor(score: number): string {
  const level = getConfidenceLevel(score);
  switch (level) {
    case "high":
      return "text-green-600";
    case "medium":
      return "text-yellow-600";
    case "low":
      return "text-red-600";
  }
}

/**
 * Extract vendor/payee pattern from a transaction description
 * Used for smart-fill to find similar transactions
 *
 * Examples:
 * - "PIX TRANSF TIAGO D12/08" -> "PIX TRANSF TIAGO"
 * - "PAG BOLETO PORTO SEGURO SAU..." -> "PAG BOLETO PORTO SEGURO"
 * - "TED 123456789 EMPRESA XYZ" -> "TED EMPRESA XYZ"
 */
export function extractVendorPattern(description: string): string {
  if (!description) return "";

  return description
    // Remove date patterns: D12/08, 12/08, 12-08, 2024-01-01, etc.
    .replace(/\b[DI]?\d{1,2}[\/\-]\d{2,4}\b/g, "")
    .replace(/\b\d{4}[\/\-]\d{2}[\/\-]\d{2}\b/g, "")
    // Remove time patterns: 12:30, 12:30:45
    .replace(/\b\d{1,2}:\d{2}(:\d{2})?\b/g, "")
    // Remove long numbers (reference IDs, account numbers, amounts)
    .replace(/\b\d{6,}\b/g, "")
    // Remove currency amounts: R$1.234,56 or $1,234.56
    .replace(/[R$]+[\d.,]+/g, "")
    // Remove trailing numbers
    .replace(/\s+\d+$/g, "")
    // Remove common noise words
    .replace(/\b(REF|REFERENCIA|COD|CODIGO|NR|NUM|NUMERO)\b/gi, "")
    // Normalize whitespace
    .replace(/\s+/g, " ")
    .trim()
    // Take first 4 significant words (enough to identify vendor)
    .split(/\s+/)
    .filter(word => word.length > 1) // Remove single chars
    .slice(0, 4)
    .join(" ")
    .toUpperCase(); // Case-insensitive matching
}
