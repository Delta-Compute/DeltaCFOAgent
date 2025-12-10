"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Receipt,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Filter,
  Download,
  RefreshCw,
  Search,
  Calendar,
  Building2,
  Tag,
  MoreHorizontal,
  Eye,
  Edit,
  Sparkles,
  ArrowRightFromLine,
  ArrowRightToLine,
  MessageSquare,
  FileText,
  ChevronDown,
  ChevronUp,
  Layers,
  X,
  Zap,
  FileSearch,
  Link2,
  Copy,
  Coins,
  CheckCircle,
  DollarSign,
  Loader2,
  Archive,
  ArchiveRestore,
  Columns,
  ArrowLeftRight,
  Undo2,
  Redo2,
} from "lucide-react";
import { toast } from "sonner";

import { transactions, revenue, type Transaction, get, post } from "@/lib/api";
import { useAuth } from "@/context/auth-context";
import { formatCurrency, formatDate, cn, extractVendorPattern } from "@/lib/utils";
import { validateField } from "@/lib/validation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuCheckboxItem,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";
import { Card, CardContent } from "@/components/ui/card";
import { DataTable, type Column } from "@/components/dashboard/data-table";
import { StatsCard, StatsGrid } from "@/components/dashboard/stats-card";
import { ErrorState } from "@/components/ui/empty-state";
import { InvoiceMatchingModal } from "@/components/dashboard/invoice-matching-modal";
import { AISuggestionsModal } from "@/components/dashboard/ai-suggestions-modal";
import { DuplicateDetectionModal } from "@/components/dashboard/duplicate-detection-modal";
import { BulkEditModal } from "@/components/dashboard/bulk-edit-modal";
import { SimilarTransactionsModal } from "@/components/dashboard/similar-transactions-modal";
import { TransactionDetailDrawer } from "@/components/dashboard/transaction-detail-drawer";
import { InternalTransfersModal } from "@/components/dashboard/internal-transfers-modal";
import { SmartFillCell } from "@/components/dashboard/smart-fill-cell";
import { SmartCombobox } from "@/components/dashboard/smart-combobox";
import { useUndoRedo } from "@/hooks/use-undo-redo";

// Stats interface
interface DashboardStats {
  totalTransactions: number;
  totalIncome: number;
  totalExpenses: number;
  needsReview: number;
}

// Sync notification interface
interface SyncNotification {
  count: number;
  timestamp: string;
  changes?: Array<{ description: string; old_category: string; new_category: string }>;
}

export default function TransactionsDashboardPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated, isLoading: authLoading, currentTenant } = useAuth();

  // State
  const [transactionData, setTransactionData] = useState<Transaction[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  // Pagination - initialize from URL
  const [page, setPage] = useState(() => {
    const p = searchParams.get("page");
    return p ? parseInt(p, 10) : 1;
  });
  const [totalItems, setTotalItems] = useState(0);
  const [pageSize, setPageSize] = useState(() => {
    const ps = searchParams.get("per_page");
    return ps ? parseInt(ps, 10) : 50;
  });

  // Filters - initialize from URL
  const [search, setSearch] = useState(() => searchParams.get("search") || "");
  const [category, setCategory] = useState<string>(() => searchParams.get("category") || "all");
  const [dateRange, setDateRange] = useState<string>(() => searchParams.get("dateRange") || "all");
  const [entity, setEntity] = useState<string>(() => searchParams.get("entity") || "all");
  const [transactionType, setTransactionType] = useState<string>(() => searchParams.get("type") || "all");
  const [source, setSource] = useState<string>(() => searchParams.get("source") || "all");
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [minAmount, setMinAmount] = useState<string>(() => searchParams.get("minAmount") || "");
  const [maxAmount, setMaxAmount] = useState<string>(() => searchParams.get("maxAmount") || "");
  const [startDate, setStartDate] = useState<string>(() => searchParams.get("startDate") || "");
  const [endDate, setEndDate] = useState<string>(() => searchParams.get("endDate") || "");
  const [needsReviewOnly, setNeedsReviewOnly] = useState(() => searchParams.get("needsReview") === "true");
  const [showArchived, setShowArchived] = useState(() => searchParams.get("showArchived") === "true");
  const [showOriginalCurrency, setShowOriginalCurrency] = useState(() => searchParams.get("originalCurrency") === "true");

  // Sorting state
  const [sortKey, setSortKey] = useState<string>(() => searchParams.get("sortBy") || "date");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">(() => (searchParams.get("sortOrder") as "asc" | "desc") || "desc");

  // Column visibility - default visible columns
  const [visibleColumns, setVisibleColumns] = useState<Set<string>>(
    new Set(["date", "description", "entity", "category", "subcategory", "confidence_score", "amount", "actions"])
  );

  // Dynamic filter options from API
  const [entityOptions, setEntityOptions] = useState<Array<{ name: string; count: number }>>([]);
  const [sourceOptions, setSourceOptions] = useState<Array<{ name: string; count: number }>>([]);
  const [categoryOptionsFromApi, setCategoryOptionsFromApi] = useState<Array<{ name: string; count: number }>>([]);
  const [subcategoryOptionsFromApi, setSubcategoryOptionsFromApi] = useState<Array<{ name: string; count: number }>>([]);

  // Sync notification
  const [syncNotification, setSyncNotification] = useState<SyncNotification | null>(null);

  // Quick filters (toggle buttons) - initialize from URL
  const [quickFilter, setQuickFilter] = useState<string | null>(() => searchParams.get("quickFilter"));

  // Cell-level quick filters (click on cell value to filter)
  const [cellCategoryFilter, setCellCategoryFilter] = useState<string | null>(null);
  const [cellSubcategoryFilter, setCellSubcategoryFilter] = useState<string | null>(null);
  const [cellEntityFilter, setCellEntityFilter] = useState<string | null>(null);
  const [cellMinAmountFilter, setCellMinAmountFilter] = useState<number | null>(null);

  // Selection
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());

  // Undo/Redo system
  const {
    pushEdit,
    undo,
    redo,
    canUndo,
    canRedo,
    isProcessing: isUndoRedoProcessing,
  } = useUndoRedo();

  // Build filter params (shared between loadTransactions and loadStats)
  const buildFilterParams = useCallback(() => {
    const params: Record<string, string> = {};

    // Search/keyword filter
    if (search) params.keyword = search;

    // Category filter (maps to transaction_type for Revenue/Expense)
    if (category !== "all") {
      if (category === "revenue") params.transaction_type = "Revenue";
      else if (category === "expense") params.transaction_type = "Expense";
      else params.category = category;
    }

    // Entity filter
    if (entity !== "all") params.entity = entity;

    // Transaction type filter (income/expense from advanced filters)
    if (transactionType !== "all") {
      params.transaction_type = transactionType === "income" ? "Revenue" : "Expense";
    }

    // Source filter
    if (source !== "all") params.source_file = source;

    // Amount range filters
    if (minAmount) params.min_amount = minAmount;
    if (maxAmount) params.max_amount = maxAmount;

    // Cell-level quick filters (override general filters when set)
    if (cellCategoryFilter) params.category = cellCategoryFilter;
    if (cellSubcategoryFilter) params.subcategory = cellSubcategoryFilter;
    if (cellEntityFilter) params.entity = cellEntityFilter;
    if (cellMinAmountFilter !== null) params.min_amount = String(cellMinAmountFilter);

    // Needs review filter
    if (needsReviewOnly) params.needs_review = "true";

    // Show archived filter
    if (showArchived) params.show_archived = "true";

    // Custom date range (takes precedence over dateRange preset)
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;

    // Date range preset filter - only if custom dates not set
    if (!startDate && !endDate && dateRange !== "all") {
      const now = new Date();
      let computedStartDate: Date | null = null;

      switch (dateRange) {
        case "today":
          computedStartDate = now;
          break;
        case "week":
          computedStartDate = new Date(now.setDate(now.getDate() - 7));
          break;
        case "month":
          computedStartDate = new Date(now.setMonth(now.getMonth() - 1));
          break;
        case "quarter":
          computedStartDate = new Date(now.setMonth(now.getMonth() - 3));
          break;
        case "year":
          computedStartDate = new Date(now.setFullYear(now.getFullYear() - 1));
          break;
      }

      if (computedStartDate) {
        params.start_date = computedStartDate.toISOString().split("T")[0];
      }
    }

    // Quick filter presets
    if (quickFilter) {
      const currentYear = new Date().getFullYear();
      switch (quickFilter) {
        case "todos":
          params.needs_review = "true";
          break;
        case "noTransfers":
          params.exclude_internal = "true";
          break;
        case "2025":
          params.start_date = "2025-01-01";
          params.end_date = "2025-12-31";
          break;
        case "2024":
          params.start_date = "2024-01-01";
          params.end_date = "2024-12-31";
          break;
        case "ytd":
          params.start_date = `${currentYear}-01-01`;
          params.end_date = new Date().toISOString().split("T")[0];
          break;
      }
    }

    return params;
  }, [search, category, entity, transactionType, source, dateRange, quickFilter, minAmount, maxAmount, startDate, endDate, needsReviewOnly, showArchived, cellCategoryFilter, cellSubcategoryFilter, cellEntityFilter, cellMinAmountFilter]);

  // Load stats from backend (independent of pagination)
  const loadStats = useCallback(async () => {
    try {
      const filterParams = buildFilterParams();
      const queryString = new URLSearchParams(filterParams).toString();
      // Use authenticated API client to ensure tenant context is set
      const result = await get<{
        total_transactions?: number;
        total_revenue?: number;
        total_expenses?: number;
        needs_review?: number;
        entities?: [string, number][];
        source_files?: [string, number][];
        categories?: [string, number][];
        subcategories?: [string, number][];
        error?: string;
      }>(`/stats${queryString ? `?${queryString}` : ""}`);

      if (result.success && result.data && !result.data.error) {
        const data = result.data;
        setStats({
          totalTransactions: data.total_transactions || 0,
          totalIncome: data.total_revenue || 0,
          totalExpenses: data.total_expenses || 0,
          needsReview: data.needs_review || 0,
        });
        // Also extract filter options from stats response
        if (data.entities) {
          setEntityOptions(
            data.entities.map((e: [string, number]) => ({
              name: e[0],
              count: e[1],
            }))
          );
        }
        if (data.source_files) {
          setSourceOptions(
            data.source_files.map((s: [string, number]) => ({
              name: s[0],
              count: s[1],
            }))
          );
        }
        if (data.categories) {
          setCategoryOptionsFromApi(
            data.categories.map((c: [string, number]) => ({
              name: c[0],
              count: c[1],
            }))
          );
        }
        if (data.subcategories) {
          setSubcategoryOptionsFromApi(
            data.subcategories.map((s: [string, number]) => ({
              name: s[0],
              count: s[1],
            }))
          );
        }
      }
    } catch (err) {
      console.error("Failed to load stats:", err);
    }
  }, [buildFilterParams]);

  // Load transactions
  const loadTransactions = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const filterParams = buildFilterParams();
      const params: Record<string, string> = {
        ...filterParams,
        page: String(page),
        per_page: String(pageSize),
        sort_by: sortKey,
        sort_order: sortDirection,
      };

      const result = await transactions.list(params);

      if (result.success && result.data) {
        // Flask returns { transactions: [], pagination: { total, page, per_page, pages } }
        const data = result.data as { transactions: Transaction[]; pagination?: { total: number } };
        const txns = data.transactions || [];
        const total = data.pagination?.total || txns.length;

        setTransactionData(txns);
        setTotalItems(total);
        // Stats are loaded separately via loadStats (not dependent on pagination)
      } else {
        throw new Error(result.error?.message || "Failed to load transactions");
      }
    } catch (err) {
      console.error("Failed to load transactions:", err);
      setError(err instanceof Error ? err.message : "Failed to load transactions");
    } finally {
      setIsLoading(false);
    }
  }, [page, pageSize, sortKey, sortDirection, buildFilterParams]);

  // Load transactions and stats when filters change (only after auth is ready)
  useEffect(() => {
    // Wait for auth to complete and have a tenant before loading data
    if (authLoading || !currentTenant) {
      return;
    }
    loadTransactions();
    loadStats();
  }, [loadTransactions, loadStats, authLoading, currentTenant]);

  // Sync filter state to URL (debounced to avoid excessive updates)
  useEffect(() => {
    // Skip on initial render
    if (!isInitialized) {
      setIsInitialized(true);
      return;
    }

    const params = new URLSearchParams();

    // Only add non-default values to URL
    if (page > 1) params.set("page", String(page));
    if (pageSize !== 50) params.set("per_page", String(pageSize));
    if (search) params.set("search", search);
    if (category !== "all") params.set("category", category);
    if (dateRange !== "all") params.set("dateRange", dateRange);
    if (entity !== "all") params.set("entity", entity);
    if (transactionType !== "all") params.set("type", transactionType);
    if (source !== "all") params.set("source", source);
    if (minAmount) params.set("minAmount", minAmount);
    if (maxAmount) params.set("maxAmount", maxAmount);
    if (startDate) params.set("startDate", startDate);
    if (endDate) params.set("endDate", endDate);
    if (needsReviewOnly) params.set("needsReview", "true");
    if (showArchived) params.set("showArchived", "true");
    if (showOriginalCurrency) params.set("originalCurrency", "true");
    if (quickFilter) params.set("quickFilter", quickFilter);
    if (sortKey !== "date") params.set("sortBy", sortKey);
    if (sortDirection !== "desc") params.set("sortOrder", sortDirection);

    // Update URL without causing navigation
    const newUrl = params.toString() ? `?${params.toString()}` : window.location.pathname;
    window.history.replaceState({}, "", newUrl);
  }, [page, pageSize, search, category, dateRange, entity, transactionType, source, minAmount, maxAmount, startDate, endDate, needsReviewOnly, showArchived, showOriginalCurrency, quickFilter, sortKey, sortDirection, isInitialized]);

  // Check for sync notification on load (only after auth is ready)
  useEffect(() => {
    async function checkSyncNotification() {
      // Wait for auth to complete before checking notifications
      if (authLoading || !currentTenant) {
        return;
      }
      try {
        const response = await revenue.getSyncNotification();
        if (response.success && response.data?.has_notification && response.data.count && response.data.timestamp) {
          setSyncNotification({
            count: response.data.count,
            timestamp: response.data.timestamp,
            changes: response.data.changes,
          });
        }
      } catch (err) {
        // Silently ignore - sync notification is optional
        console.debug("Sync notification check skipped:", err);
      }
    }
    checkSyncNotification();
  }, [authLoading, currentTenant]);

  // Auto-dismiss sync notification after 30 seconds
  useEffect(() => {
    if (syncNotification) {
      const timer = setTimeout(() => {
        setSyncNotification(null);
      }, 30000);
      return () => clearTimeout(timer);
    }
  }, [syncNotification]);

  // Keyboard shortcuts
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // Don't trigger shortcuts when typing in inputs
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        // Only handle Escape in inputs
        if (e.key === "Escape") {
          setEditingCell(null);
          (e.target as HTMLElement).blur();
        }
        return;
      }

      // Escape - close modals and clear editing
      if (e.key === "Escape") {
        setEditingCell(null);
        setInvoiceMatchModalOpen(false);
        setAiSuggestionsModalOpen(false);
        setDuplicateModalOpen(false);
        setInternalTransfersModalOpen(false);
        setBulkEditModalOpen(false);
      }

      // Ctrl/Cmd + Z - Undo
      if ((e.ctrlKey || e.metaKey) && e.key === "z" && !e.shiftKey) {
        e.preventDefault();
        if (canUndo) {
          undo().then((success) => {
            if (success) loadTransactions();
          });
        } else {
          toast.info("Nothing to undo");
        }
      }

      // Ctrl/Cmd + Y or Ctrl/Cmd + Shift + Z - Redo
      if ((e.ctrlKey || e.metaKey) && (e.key === "y" || (e.key === "z" && e.shiftKey))) {
        e.preventDefault();
        if (canRedo) {
          redo().then((success) => {
            if (success) loadTransactions();
          });
        } else {
          toast.info("Nothing to redo");
        }
      }

      // Ctrl/Cmd + A - Select all visible transactions
      if ((e.ctrlKey || e.metaKey) && e.key === "a") {
        e.preventDefault();
        const allIds = new Set(transactionData.map((t) => t.id));
        setSelectedKeys(allIds);
        toast.success(`Selected ${allIds.size} transactions`);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [transactionData, canUndo, canRedo, undo, redo, loadTransactions]);

  // Dismiss sync notification
  async function dismissSyncNotification() {
    setSyncNotification(null);
    try {
      await fetch("/api/revenue/dismiss-sync-notification", { method: "POST" });
    } catch (err) {
      console.error("Error dismissing notification:", err);
    }
  }

  // Handle sort
  function handleSort(key: string) {
    if (sortKey === key) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDirection("desc");
    }
  }

  // Handle quick filter toggle
  function handleQuickFilter(filter: string) {
    // Toggle: if already active, deactivate; otherwise activate
    if (quickFilter === filter) {
      setQuickFilter(null);
    } else {
      setQuickFilter(filter);
    }
    setPage(1); // Reset to first page when filter changes
  }

  // Handle row click
  function handleRowClick(transaction: Transaction) {
    router.push(`/transactions/${transaction.id}`);
  }

  // Handle bulk enrich
  async function handleBulkEnrich() {
    if (selectedKeys.size === 0) {
      toast.error("Please select transactions to enrich");
      return;
    }

    try {
      const result = await transactions.bulkEnrich(Array.from(selectedKeys));
      if (result.success) {
        toast.success(`Enriched ${result.data?.enriched || 0} transactions`);
        loadTransactions();
        setSelectedKeys(new Set());
      }
    } catch {
      toast.error("Failed to enrich transactions");
    }
  }

  // Handle export
  function handleExport() {
    const params = new URLSearchParams();

    // Apply same filters as loadTransactions (without pagination)
    if (search) params.set("keyword", search);

    if (category !== "all") {
      if (category === "revenue") params.set("transaction_type", "Revenue");
      else if (category === "expense") params.set("transaction_type", "Expense");
      else params.set("category", category);
    }

    if (entity !== "all") params.set("entity", entity);
    if (transactionType !== "all") {
      params.set("transaction_type", transactionType === "income" ? "Revenue" : "Expense");
    }
    if (source !== "all") params.set("source_file", source);

    if (minAmount) params.set("min_amount", minAmount);
    if (maxAmount) params.set("max_amount", maxAmount);
    if (needsReviewOnly) params.set("needs_review", "true");
    if (startDate) params.set("start_date", startDate);
    if (endDate) params.set("end_date", endDate);

    // Quick filter presets
    if (quickFilter) {
      const currentYear = new Date().getFullYear();
      switch (quickFilter) {
        case "todos":
          params.set("needs_review", "true");
          break;
        case "noTransfers":
          params.set("exclude_internal", "true");
          break;
        case "2025":
          params.set("start_date", "2025-01-01");
          params.set("end_date", "2025-12-31");
          break;
        case "2024":
          params.set("start_date", "2024-01-01");
          params.set("end_date", "2024-12-31");
          break;
        case "ytd":
          params.set("start_date", `${currentYear}-01-01`);
          params.set("end_date", new Date().toISOString().split("T")[0]);
          break;
      }
    }

    // Date range preset filter
    if (!startDate && !endDate && dateRange !== "all" && !quickFilter) {
      const now = new Date();
      let computedStartDate: Date | null = null;

      switch (dateRange) {
        case "today":
          computedStartDate = now;
          break;
        case "week":
          computedStartDate = new Date(now.setDate(now.getDate() - 7));
          break;
        case "month":
          computedStartDate = new Date(now.setMonth(now.getMonth() - 1));
          break;
        case "quarter":
          computedStartDate = new Date(now.setMonth(now.getMonth() - 3));
          break;
        case "year":
          computedStartDate = new Date(now.setFullYear(now.getFullYear() - 1));
          break;
      }

      if (computedStartDate) {
        params.set("start_date", computedStartDate.toISOString().split("T")[0]);
      }
    }

    // Build export URL and trigger download
    const exportUrl = `/api/transactions/export${params.toString() ? `?${params.toString()}` : ""}`;
    window.open(exportUrl, "_blank");
    toast.success("Exporting transactions to CSV...");
  }

  // Handle invoice matching
  const [isMatchingInvoices, setIsMatchingInvoices] = useState(false);
  const [invoiceMatchModalOpen, setInvoiceMatchModalOpen] = useState(false);
  const [invoiceMatches, setInvoiceMatches] = useState<Array<{
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
  }>>([]);

  async function handleRunInvoiceMatching() {
    setIsMatchingInvoices(true);
    // Open modal immediately to show loading state
    setInvoiceMatchModalOpen(true);
    setInvoiceMatches([]);

    try {
      const response = await fetch("/api/revenue/run-robust-matching", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ auto_apply: false }),
      });
      const data = await response.json();
      if (data.success) {
        // Store the matches in state for the modal
        const matches = data.matches || [];
        setInvoiceMatches(matches);
        if (matches.length === 0) {
          toast.info("No new matches found");
        }
      } else {
        toast.error(data.error || "Failed to run invoice matching");
        setInvoiceMatchModalOpen(false);
      }
    } catch {
      toast.error("Failed to run invoice matching");
      setInvoiceMatchModalOpen(false);
    } finally {
      setIsMatchingInvoices(false);
    }
  }

  // Callback when a match is accepted or rejected
  function handleMatchUpdated() {
    // Re-run matching to get updated list
    handleRunInvoiceMatching();
    // Also refresh the main transaction list
    loadTransactions();
  }

  // Handle blockchain enrichment
  const [isEnrichingBlockchain, setIsEnrichingBlockchain] = useState(false);
  async function handleEnrichBlockchain() {
    setIsEnrichingBlockchain(true);
    try {
      const response = await fetch("/api/transactions/enrich/all-pending", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ batch_size: 100 }),
      });
      const data = await response.json();
      if (data.success) {
        const enriched = data.summary?.successful || data.successful || 0;
        toast.success(`Blockchain enrichment complete: ${enriched} transactions enriched`);
        loadTransactions();
      } else {
        toast.error(data.error || "Failed to enrich blockchain transactions");
      }
    } catch {
      toast.error("Failed to enrich blockchain transactions");
    } finally {
      setIsEnrichingBlockchain(false);
    }
  }

  // Inline editing state
  const [editingCell, setEditingCell] = useState<{
    id: string;
    field: string;
    value: string;
  } | null>(null);

  // AI Suggestions modal state
  const [aiSuggestionsModalOpen, setAiSuggestionsModalOpen] = useState(false);
  const [selectedTransactionForAI, setSelectedTransactionForAI] = useState<Transaction | null>(null);

  // Open AI Suggestions modal for a transaction
  function handleOpenAISuggestions(transaction: Transaction) {
    setSelectedTransactionForAI(transaction);
    setAiSuggestionsModalOpen(true);
  }

  async function handleInlineEdit(
    transactionId: string,
    field: string,
    value: string
  ) {
    // Validate the field value before updating
    const validation = validateField(field, value);
    if (!validation.valid) {
      toast.error(validation.error || "Invalid value");
      setEditingCell(null);
      return;
    }

    // Get the old value for undo
    const transaction = transactionData.find((t) => t.id === transactionId);
    const oldValue = transaction ? String((transaction as unknown as Record<string, unknown>)[field] || "") : "";

    // Optimistically update local state
    setTransactionData((prev) =>
      prev.map((t) =>
        t.id === transactionId ? { ...t, [field]: value } : t
      )
    );

    // Clear editing state
    setEditingCell(null);

    try {
      const result = await transactions.updateField(transactionId, field, value);
      if (result.success) {
        toast.success("Field updated");
        // Push to undo stack
        pushEdit(transactionId, field, oldValue, value);
        // For entity changes, check for similar transactions
        if (field === "entity_name" && value) {
          setSimilarTxTransactionId(transactionId);
          setSimilarTxNewEntity(value);
          setSimilarTxModalOpen(true);
        }
      } else {
        // Revert on failure
        toast.error("Failed to update field");
        loadTransactions();
      }
    } catch {
      toast.error("Failed to update field");
      loadTransactions();
    }
  }

  // Smart fill - applies value to all transactions with matching description pattern
  async function handleSmartFill(
    description: string,
    field: string,
    value: string
  ) {
    const sourcePattern = extractVendorPattern(description);
    if (!sourcePattern) {
      toast.error("Could not extract pattern from description");
      return;
    }

    // Find all transactions with matching patterns that don't already have this value
    const matchingTransactions = transactionData.filter((t) => {
      const pattern = extractVendorPattern(t.description);
      const currentValue = (t as unknown as Record<string, string>)[field];
      return pattern === sourcePattern && currentValue !== value;
    });

    if (matchingTransactions.length === 0) {
      toast.info("No similar transactions found to update");
      return;
    }

    // Build updates array for bulk update
    const updates = matchingTransactions.map((t) => ({
      transaction_id: t.id,
      field: field,
      value: value,
    }));

    // Optimistically update local state
    setTransactionData((prev) =>
      prev.map((t) => {
        const update = updates.find((u) => u.transaction_id === t.id);
        return update ? { ...t, [update.field]: update.value } : t;
      })
    );

    try {
      const result = await transactions.bulkUpdate(updates);
      if (result.success) {
        toast.success(`Updated ${matchingTransactions.length} similar transactions`);
      } else {
        toast.error("Failed to update similar transactions");
        loadTransactions();
      }
    } catch {
      toast.error("Failed to update similar transactions");
      loadTransactions();
    }
  }

  // Handle find duplicates - opens the modal
  const [duplicateModalOpen, setDuplicateModalOpen] = useState(false);
  function handleFindDuplicates() {
    setDuplicateModalOpen(true);
  }

  // Internal transfers detection modal
  const [internalTransfersModalOpen, setInternalTransfersModalOpen] = useState(false);
  function handleDetectInternalTransfers() {
    setInternalTransfersModalOpen(true);
  }

  // Bulk edit modal
  const [bulkEditModalOpen, setBulkEditModalOpen] = useState(false);

  // Similar transactions modal
  const [similarTxModalOpen, setSimilarTxModalOpen] = useState(false);
  const [similarTxTransactionId, setSimilarTxTransactionId] = useState<string | null>(null);
  const [similarTxNewEntity, setSimilarTxNewEntity] = useState<string>("");

  // Transaction detail drawer
  const [detailDrawerOpen, setDetailDrawerOpen] = useState(false);
  const [selectedTransaction, setSelectedTransaction] = useState<Transaction | null>(null);

  // Stats refresh
  const [isRefreshingStats, setIsRefreshingStats] = useState(false);
  async function handleRefreshStats() {
    setIsRefreshingStats(true);
    await loadStats();
    setIsRefreshingStats(false);
    toast.success("Stats refreshed");
  }

  // Compute date range from visible transactions
  const dataDateRange = useMemo(() => {
    if (transactionData.length === 0) return null;
    const dates = transactionData.map((t) => new Date(t.date).getTime());
    const minDate = new Date(Math.min(...dates));
    const maxDate = new Date(Math.max(...dates));
    return {
      min: minDate.toISOString().split("T")[0],
      max: maxDate.toISOString().split("T")[0],
    };
  }, [transactionData]);

  // Use category and subcategory options from API (loaded from all transactions, not just current page)
  const categoryOptions = useMemo(() => {
    return categoryOptionsFromApi.map(c => c.name).sort();
  }, [categoryOptionsFromApi]);

  const subcategoryOptions = useMemo(() => {
    return subcategoryOptionsFromApi.map(s => s.name).sort();
  }, [subcategoryOptionsFromApi]);

  // Count active advanced filters
  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (entity !== "all") count++;
    if (transactionType !== "all") count++;
    if (source !== "all") count++;
    if (minAmount) count++;
    if (maxAmount) count++;
    if (startDate) count++;
    if (endDate) count++;
    if (needsReviewOnly) count++;
    return count;
  }, [entity, transactionType, source, minAmount, maxAmount, startDate, endDate, needsReviewOnly]);

  // Clear all filters function
  function clearAllFilters() {
    setSearch("");
    setCategory("all");
    setDateRange("all");
    setEntity("all");
    setTransactionType("all");
    setSource("all");
    setMinAmount("");
    setMaxAmount("");
    setStartDate("");
    setEndDate("");
    setNeedsReviewOnly(false);
    setQuickFilter(null);
    // Also clear cell filters
    setCellCategoryFilter(null);
    setCellSubcategoryFilter(null);
    setCellEntityFilter(null);
    setCellMinAmountFilter(null);
    setPage(1);
    toast.success("All filters cleared");
  }

  // Clear cell-level quick filters
  function clearCellFilters() {
    setCellCategoryFilter(null);
    setCellSubcategoryFilter(null);
    setCellEntityFilter(null);
    setCellMinAmountFilter(null);
  }

  // Check if any cell filters are active
  const hasCellFilters = cellCategoryFilter || cellSubcategoryFilter || cellEntityFilter || cellMinAmountFilter !== null;

  // Table columns
  const columns: Column<Transaction>[] = [
    {
      key: "date",
      header: "Date",
      sortable: true,
      width: "120px",
      render: (item) => (
        <span className="text-sm">{formatDate(item.date)}</span>
      ),
    },
    {
      key: "description",
      header: "Description",
      render: (item) => (
        <div className="max-w-[300px]">
          <div className="flex items-center gap-2">
            <span className="font-medium truncate" title={item.description}>
              {item.description}
            </span>
            {item.archived && (
              <Badge variant="secondary" className="text-xs bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400">
                Archived
              </Badge>
            )}
          </div>
        </div>
      ),
    },
    {
      key: "entity",
      header: "Entity",
      render: (item) => {
        const isEditingEntity =
          editingCell?.id === item.id && editingCell?.field === "entity_name";

        return (
          <SmartFillCell
            rowId={item.id}
            field="entity_name"
            value={item.entity_name || ""}
            description={item.description}
            onSmartFill={handleSmartFill}
          >
            {isEditingEntity ? (
              <SmartCombobox
                value={editingCell.value}
                options={entityOptions.map((opt) => opt.name)}
                placeholder="Type entity..."
                fieldType="entity_name"
                transactionId={item.id}
                onSelect={(value) => {
                  if (value !== item.entity_name) {
                    handleInlineEdit(item.id, "entity_name", value);
                  } else {
                    setEditingCell(null);
                  }
                }}
                onCancel={() => setEditingCell(null)}
                onOpenAISuggestions={() => {
                  setEditingCell(null);
                  handleOpenAISuggestions(item);
                }}
              />
            ) : (
              <div className="group flex items-center gap-1">
                {/* Filter icon - appears on hover, left side */}
                {item.entity_name && (
                  <button
                    className={cn(
                      "p-0.5 rounded transition-opacity",
                      cellEntityFilter === item.entity_name
                        ? "opacity-100 text-primary"
                        : "opacity-0 group-hover:opacity-100 hover:bg-muted text-muted-foreground"
                    )}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (cellEntityFilter === item.entity_name) {
                        setCellEntityFilter(null);
                        toast.info("Entity filter cleared");
                      } else {
                        setCellEntityFilter(item.entity_name || null);
                        toast.info(`Filtering by entity: ${item.entity_name}`);
                      }
                    }}
                    title={`Filter by ${item.entity_name}`}
                  >
                    <Filter className="h-3 w-3" />
                  </button>
                )}
                {/* Text - click to edit */}
                <span
                  className={cn(
                    "text-sm cursor-pointer hover:text-foreground transition-colors truncate max-w-[120px]",
                    item.entity_name ? "text-foreground" : "text-muted-foreground/50 italic",
                    cellEntityFilter === item.entity_name && item.entity_name && "text-primary font-medium"
                  )}
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditingCell({
                      id: item.id,
                      field: "entity_name",
                      value: item.entity_name || "",
                    });
                  }}
                  title="Click to edit"
                >
                  {item.entity_name || "Set entity..."}
                </span>
              </div>
            )}
          </SmartFillCell>
        );
      },
    },
    {
      key: "category",
      header: "Category",
      sortable: true,
      render: (item) => {
        const isEditingCategory =
          editingCell?.id === item.id && editingCell?.field === "category";

        return (
          <SmartFillCell
            rowId={item.id}
            field="category"
            value={item.category || ""}
            description={item.description}
            onSmartFill={handleSmartFill}
          >
            {isEditingCategory ? (
              <SmartCombobox
                value={editingCell.value}
                options={categoryOptions}
                placeholder="Type category..."
                fieldType="category"
                transactionId={item.id}
                onSelect={(value) => {
                  if (value !== item.category) {
                    handleInlineEdit(item.id, "category", value);
                  } else {
                    setEditingCell(null);
                  }
                }}
                onCancel={() => setEditingCell(null)}
                onOpenAISuggestions={() => {
                  setEditingCell(null);
                  handleOpenAISuggestions(item);
                }}
              />
            ) : (
              <div className="group flex items-center gap-1">
                {/* Filter icon - appears on hover, left side */}
                {item.category && (
                  <button
                    className={cn(
                      "p-0.5 rounded transition-opacity",
                      cellCategoryFilter === item.category
                        ? "opacity-100 text-primary"
                        : "opacity-0 group-hover:opacity-100 hover:bg-muted text-muted-foreground"
                    )}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (cellCategoryFilter === item.category) {
                        setCellCategoryFilter(null);
                        toast.info("Category filter cleared");
                      } else {
                        setCellCategoryFilter(item.category || null);
                        toast.info(`Filtering by category: ${item.category}`);
                      }
                    }}
                    title={`Filter by ${item.category}`}
                  >
                    <Filter className="h-3 w-3" />
                  </button>
                )}
                {/* Badge - click to edit */}
                <div
                  className={cn(
                    "cursor-pointer hover:opacity-80",
                    cellCategoryFilter === item.category && "ring-2 ring-primary ring-offset-1 rounded"
                  )}
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditingCell({
                      id: item.id,
                      field: "category",
                      value: item.category || "",
                    });
                  }}
                  title="Click to edit"
                >
                  {item.category ? (
                    <Badge variant="secondary" className="w-fit">
                      {item.category}
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="w-fit text-muted-foreground">
                      Uncategorized
                    </Badge>
                  )}
                </div>
              </div>
            )}
          </SmartFillCell>
        );
      },
    },
    {
      key: "subcategory",
      header: "Subcategory",
      render: (item) => {
        const isEditingSubcategory =
          editingCell?.id === item.id && editingCell?.field === "subcategory";

        return (
          <SmartFillCell
            rowId={item.id}
            field="subcategory"
            value={item.subcategory || ""}
            description={item.description}
            onSmartFill={handleSmartFill}
          >
            {isEditingSubcategory ? (
              <SmartCombobox
                value={editingCell.value}
                options={subcategoryOptions}
                placeholder="Type subcategory..."
                fieldType="subcategory"
                transactionId={item.id}
                onSelect={(value) => {
                  if (value !== item.subcategory) {
                    handleInlineEdit(item.id, "subcategory", value);
                  } else {
                    setEditingCell(null);
                  }
                }}
                onCancel={() => setEditingCell(null)}
                onOpenAISuggestions={() => {
                  setEditingCell(null);
                  handleOpenAISuggestions(item);
                }}
              />
            ) : (
              <div className="group flex items-center gap-1">
                {/* Filter icon - appears on hover, left side */}
                {item.subcategory && (
                  <button
                    className={cn(
                      "p-0.5 rounded transition-opacity",
                      cellSubcategoryFilter === item.subcategory
                        ? "opacity-100 text-primary"
                        : "opacity-0 group-hover:opacity-100 hover:bg-muted text-muted-foreground"
                    )}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (cellSubcategoryFilter === item.subcategory) {
                        setCellSubcategoryFilter(null);
                        toast.info("Subcategory filter cleared");
                      } else {
                        setCellSubcategoryFilter(item.subcategory || null);
                        toast.info(`Filtering by subcategory: ${item.subcategory}`);
                      }
                    }}
                    title={`Filter by ${item.subcategory}`}
                  >
                    <Filter className="h-3 w-3" />
                  </button>
                )}
                {/* Text - click to edit */}
                <span
                  className={cn(
                    "text-sm cursor-pointer hover:text-foreground transition-colors",
                    item.subcategory ? "text-muted-foreground" : "text-muted-foreground/50 italic",
                    cellSubcategoryFilter === item.subcategory && item.subcategory && "text-primary font-medium"
                  )}
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditingCell({
                      id: item.id,
                      field: "subcategory",
                      value: item.subcategory || "",
                    });
                  }}
                  title="Click to edit"
                >
                  {item.subcategory || "Set subcategory..."}
                </span>
              </div>
            )}
          </SmartFillCell>
        );
      },
    },
    {
      key: "confidence_score",
      header: "Confidence",
      sortable: true,
      width: "100px",
      render: (item) => {
        if (!item.confidence_score) return null;
        const score = item.confidence_score * 100;
        return (
          <div
            className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity"
            onClick={(e) => {
              e.stopPropagation();
              handleOpenAISuggestions(item);
            }}
            title="Click for AI suggestions"
          >
            <div className="confidence-bar w-16">
              <div
                className={cn(
                  "confidence-bar-fill",
                  score >= 80 && "confidence-bar-high",
                  score >= 55 && score < 80 && "confidence-bar-medium",
                  score < 55 && "confidence-bar-low"
                )}
                style={{ width: `${score}%` }}
              />
            </div>
            <span className="text-xs text-muted-foreground">
              {score.toFixed(0)}%
            </span>
            <Sparkles className="h-3 w-3 text-muted-foreground" />
          </div>
        );
      },
    },
    {
      key: "amount",
      header: showOriginalCurrency ? "Amount (Original)" : "Amount (USD)",
      sortable: true,
      align: "right",
      render: (item) => (
        <span
          className={cn(
            "font-medium cursor-pointer hover:underline",
            item.amount >= 0 ? "text-green-600" : "text-red-600",
            cellMinAmountFilter !== null && Math.abs(item.amount) >= cellMinAmountFilter && "ring-2 ring-primary ring-offset-1 rounded px-1"
          )}
          onClick={(e) => {
            e.stopPropagation();
            const absAmount = Math.abs(item.amount);
            // Toggle amount filter: if same amount, clear; otherwise set new filter
            if (cellMinAmountFilter === absAmount) {
              setCellMinAmountFilter(null);
              toast.info("Amount filter cleared");
            } else {
              setCellMinAmountFilter(absAmount);
              toast.info(`Filtering amounts >= ${formatCurrency(absAmount)}`);
            }
          }}
          title={`Click to filter amounts >= ${formatCurrency(Math.abs(item.amount))}`}
        >
          {formatCurrency(item.amount, showOriginalCurrency ? item.currency : "USD")}
        </span>
      ),
    },
    {
      key: "origin",
      header: "Origin",
      render: (item) => {
        const isEditingOrigin =
          editingCell?.id === item.id && editingCell?.field === "origin";

        // Truncate wallet address for display (show first 6 and last 4 chars)
        const truncateAddress = (addr: string) => {
          if (!addr || addr.length <= 12) return addr;
          return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
        };

        return (
          <div className="flex items-center gap-1 text-sm">
            {isEditingOrigin ? (
              <div onClick={(e) => e.stopPropagation()}>
                <Input
                  autoFocus
                  defaultValue={editingCell.value}
                  className="h-7 w-32 text-xs"
                  placeholder="Wallet address"
                  onBlur={(e) => {
                    if (e.target.value !== item.origin) {
                      handleInlineEdit(item.id, "origin", e.target.value);
                    } else {
                      setEditingCell(null);
                    }
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      const value = (e.target as HTMLInputElement).value;
                      if (value !== item.origin) {
                        handleInlineEdit(item.id, "origin", value);
                      } else {
                        setEditingCell(null);
                      }
                    } else if (e.key === "Escape") {
                      setEditingCell(null);
                    }
                  }}
                />
              </div>
            ) : (
              <div
                className="flex items-center gap-1 cursor-pointer hover:text-foreground transition-colors"
                onDoubleClick={(e) => {
                  e.stopPropagation();
                  setEditingCell({
                    id: item.id,
                    field: "origin",
                    value: item.origin || "",
                  });
                }}
                title={item.origin ? `${item.origin} (double-click to edit, click to copy)` : "Double-click to set origin"}
              >
                <ArrowRightFromLine className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                {item.origin ? (
                  <span
                    className="truncate max-w-[100px] hover:underline"
                    onClick={(e) => {
                      e.stopPropagation();
                      navigator.clipboard.writeText(item.origin || "");
                      toast.success("Address copied");
                    }}
                  >
                    {truncateAddress(item.origin)}
                  </span>
                ) : (
                  <span className="text-muted-foreground italic">Set...</span>
                )}
              </div>
            )}
          </div>
        );
      },
    },
    {
      key: "destination",
      header: "Destination",
      render: (item) => {
        const isEditingDestination =
          editingCell?.id === item.id && editingCell?.field === "destination";

        // Truncate wallet address for display
        const truncateAddress = (addr: string) => {
          if (!addr || addr.length <= 12) return addr;
          return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
        };

        return (
          <div className="flex items-center gap-1 text-sm">
            {isEditingDestination ? (
              <div onClick={(e) => e.stopPropagation()}>
                <Input
                  autoFocus
                  defaultValue={editingCell.value}
                  className="h-7 w-32 text-xs"
                  placeholder="Wallet address"
                  onBlur={(e) => {
                    if (e.target.value !== item.destination) {
                      handleInlineEdit(item.id, "destination", e.target.value);
                    } else {
                      setEditingCell(null);
                    }
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      const value = (e.target as HTMLInputElement).value;
                      if (value !== item.destination) {
                        handleInlineEdit(item.id, "destination", value);
                      } else {
                        setEditingCell(null);
                      }
                    } else if (e.key === "Escape") {
                      setEditingCell(null);
                    }
                  }}
                />
              </div>
            ) : (
              <div
                className="flex items-center gap-1 cursor-pointer hover:text-foreground transition-colors"
                onDoubleClick={(e) => {
                  e.stopPropagation();
                  setEditingCell({
                    id: item.id,
                    field: "destination",
                    value: item.destination || "",
                  });
                }}
                title={item.destination ? `${item.destination} (double-click to edit, click to copy)` : "Double-click to set destination"}
              >
                <ArrowRightToLine className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                {item.destination ? (
                  <span
                    className="truncate max-w-[100px] hover:underline"
                    onClick={(e) => {
                      e.stopPropagation();
                      navigator.clipboard.writeText(item.destination || "");
                      toast.success("Address copied");
                    }}
                  >
                    {truncateAddress(item.destination)}
                  </span>
                ) : (
                  <span className="text-muted-foreground italic">Set...</span>
                )}
              </div>
            )}
          </div>
        );
      },
    },
    {
      key: "justification",
      header: "Justification",
      render: (item) => {
        const invoiceId = item.invoice_id || item.matched_invoice_id;
        return (
          <div className="max-w-[200px]">
            {item.justification ? (
              <div className="flex items-start gap-1">
                <MessageSquare className="h-3 w-3 text-muted-foreground mt-0.5 flex-shrink-0" />
                <span className="text-sm truncate" title={item.justification}>{item.justification}</span>
                {invoiceId && (
                  <a
                    href={`/invoices?highlight=${invoiceId}`}
                    className="flex-shrink-0 text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                    title="View linked invoice"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <FileText className="h-3 w-3" />
                  </a>
                )}
              </div>
            ) : (
              <span className="text-muted-foreground text-sm">-</span>
            )}
          </div>
        );
      },
    },
    {
      key: "source_file",
      header: "Source",
      render: (item) => (
        <div className="flex items-center gap-1 text-sm">
          {item.source_file ? (
            <>
              <FileText className="h-3 w-3 text-muted-foreground" />
              <span className="truncate max-w-[100px]">{item.source_file}</span>
            </>
          ) : (
            <span className="text-muted-foreground">-</span>
          )}
        </div>
      ),
    },
    {
      key: "actions",
      header: "",
      width: "50px",
      render: (item) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => {
              setSelectedTransaction(item);
              setDetailDrawerOpen(true);
            }}>
              <Eye className="mr-2 h-4 w-4" />
              View Details
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Edit className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={async (e) => {
                e.stopPropagation();
                const result = await transactions.enrich(item.id);
                if (result.success) {
                  toast.success("Transaction enriched");
                  loadTransactions();
                }
              }}
            >
              <Sparkles className="mr-2 h-4 w-4" />
              AI Enrich
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            {item.archived ? (
              <DropdownMenuItem
                className="text-green-600 focus:text-green-600"
                onClick={async (e) => {
                  e.stopPropagation();
                  const result = await transactions.unarchive([item.id]);
                  if (result.success) {
                    toast.success("Transaction restored");
                    loadTransactions();
                  } else {
                    toast.error(result.error?.message || "Failed to restore");
                  }
                }}
              >
                <ArchiveRestore className="mr-2 h-4 w-4" />
                Restore
              </DropdownMenuItem>
            ) : (
              <DropdownMenuItem
                className="text-red-600 focus:text-red-600"
                onClick={async (e) => {
                  e.stopPropagation();
                  const result = await transactions.archive([item.id]);
                  if (result.success) {
                    toast.success("Transaction archived");
                    loadTransactions();
                  } else {
                    toast.error(result.error?.message || "Failed to archive");
                  }
                }}
              >
                <Archive className="mr-2 h-4 w-4" />
                Archive
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  // Column visibility definitions for the dropdown
  const columnOptions = [
    { key: "date", label: "Date" },
    { key: "description", label: "Description" },
    { key: "entity", label: "Entity" },
    { key: "category", label: "Category" },
    { key: "subcategory", label: "Subcategory" },
    { key: "confidence_score", label: "Confidence" },
    { key: "amount", label: "Amount" },
    { key: "origin", label: "Origin" },
    { key: "destination", label: "Destination" },
    { key: "justification", label: "Justification" },
    { key: "source_file", label: "Source" },
  ];

  // Filter columns based on visibility
  const filteredColumns = useMemo(() => {
    return columns.filter((col) => visibleColumns.has(col.key));
  }, [columns, visibleColumns]);

  // Toggle column visibility
  function toggleColumnVisibility(key: string) {
    setVisibleColumns((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }

  if (error) {
    return <ErrorState title={error} onRetry={loadTransactions} />;
  }

  return (
    <div className="space-y-6">
      {/* Revenue Sync Notification Banner */}
      {syncNotification && (
        <div className="flex items-center justify-between gap-4 rounded-lg border border-green-200 bg-green-50 px-4 py-3 dark:border-green-800 dark:bg-green-950">
          <div className="flex items-center gap-3">
            <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />
            <div>
              <p className="font-medium text-green-800 dark:text-green-200">
                Revenue transactions synced
              </p>
              <p className="text-sm text-green-600 dark:text-green-400">
                {syncNotification.count} transactions have been reclassified as Revenue.
                Updated {new Date(syncNotification.timestamp).toLocaleString()}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="text-green-700 hover:bg-green-100 dark:text-green-300 dark:hover:bg-green-900"
              onClick={() => toast.info(`${syncNotification.count} transactions reclassified as Revenue`)}
            >
              View Details
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="text-green-700 hover:bg-green-100 dark:text-green-300 dark:hover:bg-green-900"
              onClick={dismissSyncNotification}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Page Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold font-heading">Transactions</h1>
          <p className="text-muted-foreground">
            View and manage all your financial transactions
          </p>
        </div>
        <div className="flex items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button size="sm" className="gap-1">
                <Zap className="h-4 w-4" />
                Quick Actions
                <ChevronDown className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuItem onClick={handleBulkEnrich}>
                <Sparkles className="mr-2 h-4 w-4" />
                AI Suggestions
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleRunInvoiceMatching}>
                <Link2 className="mr-2 h-4 w-4" />
                Match Invoices
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleFindDuplicates}>
                <FileSearch className="mr-2 h-4 w-4" />
                Find Duplicates
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleDetectInternalTransfers}>
                <ArrowLeftRight className="mr-2 h-4 w-4" />
                Detect Internal Transfers
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Copy className="mr-2 h-4 w-4" />
                Bulk Categorize
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <div className="flex items-center border rounded-md">
            <Button
              variant="ghost"
              size="sm"
              onClick={async () => {
                const success = await undo();
                if (success) loadTransactions();
              }}
              disabled={!canUndo || isUndoRedoProcessing}
              className="rounded-r-none border-r"
              title="Undo (Ctrl+Z)"
            >
              <Undo2 className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={async () => {
                const success = await redo();
                if (success) loadTransactions();
              }}
              disabled={!canRedo || isUndoRedoProcessing}
              className="rounded-l-none"
              title="Redo (Ctrl+Y)"
            >
              <Redo2 className="h-4 w-4" />
            </Button>
          </div>
          <Button variant="outline" size="sm" onClick={loadTransactions}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                <Columns className="mr-2 h-4 w-4" />
                Columns
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuLabel>Toggle columns</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {columnOptions.map((col) => (
                <DropdownMenuCheckboxItem
                  key={col.key}
                  checked={visibleColumns.has(col.key)}
                  onCheckedChange={() => toggleColumnVisibility(col.key)}
                >
                  {col.label}
                </DropdownMenuCheckboxItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Stats */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-muted-foreground">Overview</h3>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRefreshStats}
            disabled={isRefreshingStats}
            className="h-7 px-2"
          >
            <RefreshCw className={cn("h-4 w-4", isRefreshingStats && "animate-spin")} />
          </Button>
        </div>
        <StatsGrid>
          <StatsCard
            title="Total Transactions"
            value={stats?.totalTransactions?.toLocaleString() || "0"}
            icon={Receipt}
            isLoading={isLoading || isRefreshingStats}
          />
          <StatsCard
            title="Total Income"
            value={formatCurrency(stats?.totalIncome || 0)}
            icon={TrendingUp}
            trend={{ value: 5.2, label: "vs last month" }}
            isLoading={isLoading || isRefreshingStats}
          />
          <StatsCard
            title="Total Expenses"
            value={formatCurrency(stats?.totalExpenses || 0)}
            icon={TrendingDown}
            trend={{ value: -2.3, label: "vs last month" }}
            isLoading={isLoading || isRefreshingStats}
          />
          <StatsCard
            title="Needs Review"
            value={String(stats?.needsReview || 0)}
            icon={AlertTriangle}
            isLoading={isLoading || isRefreshingStats}
          />
        </StatsGrid>
      </div>

      {/* AI Enhancement Actions */}
      <div className="flex flex-wrap gap-3">
        <Button
          variant="outline"
          size="sm"
          className="gap-2"
          onClick={handleRunInvoiceMatching}
          disabled={isMatchingInvoices}
        >
          {isMatchingInvoices ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Link2 className="h-4 w-4" />
          )}
          Run Invoice Matching
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="gap-2"
          onClick={handleEnrichBlockchain}
          disabled={isEnrichingBlockchain}
        >
          {isEnrichingBlockchain ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Coins className="h-4 w-4" />
          )}
          Enrich Blockchain Transactions
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="gap-2"
          onClick={handleFindDuplicates}
        >
          <FileSearch className="h-4 w-4" />
          Find Duplicates
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="gap-2"
          onClick={handleDetectInternalTransfers}
        >
          <ArrowLeftRight className="h-4 w-4" />
          Detect Internal Transfers
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="space-y-4">
            {/* Quick Filter Buttons */}
            <div className="flex items-center gap-3 flex-wrap">
              <span className="text-sm font-medium text-muted-foreground">
                Quick Filters:
              </span>
              <Button
                variant={quickFilter === "todos" ? "default" : "outline"}
                size="sm"
                onClick={() => handleQuickFilter("todos")}
              >
                To Do&apos;s
              </Button>
              <Button
                variant={quickFilter === "noTransfers" ? "default" : "outline"}
                size="sm"
                onClick={() => handleQuickFilter("noTransfers")}
              >
                No Transfers
              </Button>
              <span className="text-muted-foreground">|</span>
              <Button
                variant={quickFilter === "2025" ? "default" : "outline"}
                size="sm"
                onClick={() => handleQuickFilter("2025")}
              >
                2025
              </Button>
              <Button
                variant={quickFilter === "2024" ? "default" : "outline"}
                size="sm"
                onClick={() => handleQuickFilter("2024")}
              >
                2024
              </Button>
              <Button
                variant={quickFilter === "ytd" ? "default" : "outline"}
                size="sm"
                onClick={() => handleQuickFilter("ytd")}
              >
                YTD
              </Button>
              <span className="text-muted-foreground">|</span>
              <Button
                variant={showArchived ? "default" : "outline"}
                size="sm"
                onClick={() => setShowArchived(!showArchived)}
              >
                <Archive className="mr-2 h-4 w-4" />
                {showArchived ? "Hide Archived" : "Show Archived"}
              </Button>
              <Button
                variant={showOriginalCurrency ? "default" : "outline"}
                size="sm"
                onClick={() => setShowOriginalCurrency(!showOriginalCurrency)}
              >
                <Coins className="mr-2 h-4 w-4" />
                {showOriginalCurrency ? "Original" : "USD"}
              </Button>
            </div>

            {/* Cell-Level Quick Filters Indicator */}
            {hasCellFilters && (
              <div className="flex items-center gap-2 flex-wrap py-2 px-3 bg-primary/5 rounded-lg border border-primary/20">
                <span className="text-sm font-medium text-primary">
                  Cell Filters:
                </span>
                {cellCategoryFilter && (
                  <Badge variant="secondary" className="gap-1">
                    <Tag className="h-3 w-3" />
                    Category: {cellCategoryFilter}
                    <button
                      onClick={() => setCellCategoryFilter(null)}
                      className="ml-1 hover:text-destructive"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                )}
                {cellSubcategoryFilter && (
                  <Badge variant="secondary" className="gap-1">
                    <Layers className="h-3 w-3" />
                    Subcategory: {cellSubcategoryFilter}
                    <button
                      onClick={() => setCellSubcategoryFilter(null)}
                      className="ml-1 hover:text-destructive"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                )}
                {cellEntityFilter && (
                  <Badge variant="secondary" className="gap-1">
                    <Building2 className="h-3 w-3" />
                    Entity: {cellEntityFilter}
                    <button
                      onClick={() => setCellEntityFilter(null)}
                      className="ml-1 hover:text-destructive"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                )}
                {cellMinAmountFilter !== null && (
                  <Badge variant="secondary" className="gap-1">
                    <DollarSign className="h-3 w-3" />
                    Amount {">="} {formatCurrency(cellMinAmountFilter)}
                    <button
                      onClick={() => setCellMinAmountFilter(null)}
                      className="ml-1 hover:text-destructive"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearCellFilters}
                  className="h-6 px-2 text-xs"
                >
                  Clear All Cell Filters
                </Button>
              </div>
            )}

            {/* Primary Filters Row */}
            <div className="flex flex-col gap-4 md:flex-row md:items-center">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search transactions..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
              <div className="flex items-center gap-2">
                <Select value={category} onValueChange={setCategory}>
                  <SelectTrigger className="w-[180px]">
                    <Tag className="mr-2 h-4 w-4" />
                    <SelectValue placeholder="Category" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Categories</SelectItem>
                    <SelectItem value="revenue">Revenue</SelectItem>
                    <SelectItem value="expense">Expense</SelectItem>
                    <SelectItem value="transfer">Transfer</SelectItem>
                    <SelectItem value="payroll">Payroll</SelectItem>
                  </SelectContent>
                </Select>

                <Select value={dateRange} onValueChange={setDateRange}>
                  <SelectTrigger className="w-[150px]">
                    <Calendar className="mr-2 h-4 w-4" />
                    <SelectValue placeholder="Date Range" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Time</SelectItem>
                    <SelectItem value="today">Today</SelectItem>
                    <SelectItem value="week">This Week</SelectItem>
                    <SelectItem value="month">This Month</SelectItem>
                    <SelectItem value="quarter">This Quarter</SelectItem>
                    <SelectItem value="year">This Year</SelectItem>
                  </SelectContent>
                </Select>

                <Button
                  variant={activeFilterCount > 0 ? "default" : "outline"}
                  size="sm"
                  onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
                  className="gap-1"
                >
                  <Filter className="h-4 w-4" />
                  Advanced
                  {activeFilterCount > 0 && (
                    <Badge variant="secondary" className="ml-1 h-5 px-1.5 text-xs">
                      {activeFilterCount}
                    </Badge>
                  )}
                  {showAdvancedFilters ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                </Button>
                {activeFilterCount > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={clearAllFilters}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    <X className="mr-1 h-4 w-4" />
                    Clear Filters
                  </Button>
                )}
              </div>
            </div>

            {/* Advanced Filters Row */}
            {showAdvancedFilters && (
              <div className="flex flex-col gap-4 md:flex-row md:items-center border-t pt-4">
                <Select value={entity} onValueChange={setEntity}>
                  <SelectTrigger className="w-[180px]">
                    <Building2 className="mr-2 h-4 w-4" />
                    <SelectValue placeholder="Entity" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Entities</SelectItem>
                    {entityOptions.map((opt) => (
                      <SelectItem key={opt.name} value={opt.name}>
                        {opt.name} ({opt.count})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select value={transactionType} onValueChange={setTransactionType}>
                  <SelectTrigger className="w-[150px]">
                    <Layers className="mr-2 h-4 w-4" />
                    <SelectValue placeholder="Type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Types</SelectItem>
                    <SelectItem value="income">Income</SelectItem>
                    <SelectItem value="expense">Expense</SelectItem>
                  </SelectContent>
                </Select>

                <Select value={source} onValueChange={setSource}>
                  <SelectTrigger className="w-[180px]">
                    <FileText className="mr-2 h-4 w-4" />
                    <SelectValue placeholder="Source" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Sources</SelectItem>
                    {sourceOptions.map((opt) => (
                      <SelectItem key={opt.name} value={opt.name}>
                        {opt.name.length > 20
                          ? opt.name.substring(0, 20) + "..."
                          : opt.name}{" "}
                        ({opt.count})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <div className="flex items-center gap-2">
                  <DollarSign className="h-4 w-4 text-muted-foreground" />
                  <Input
                    type="number"
                    placeholder="Min"
                    value={minAmount}
                    onChange={(e) => setMinAmount(e.target.value)}
                    className="w-[100px]"
                  />
                  <span className="text-muted-foreground">-</span>
                  <Input
                    type="number"
                    placeholder="Max"
                    value={maxAmount}
                    onChange={(e) => setMaxAmount(e.target.value)}
                    className="w-[100px]"
                  />
                </div>

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setEntity("all");
                    setTransactionType("all");
                    setSource("all");
                    setCategory("all");
                    setDateRange("all");
                    setSearch("");
                    setMinAmount("");
                    setMaxAmount("");
                    setStartDate("");
                    setEndDate("");
                    setNeedsReviewOnly(false);
                    setQuickFilter(null);
                  }}
                  className="gap-1 text-muted-foreground"
                >
                  <X className="h-4 w-4" />
                  Clear Filters
                </Button>
              </div>
            )}

            {/* Second Advanced Filters Row - Date Range & Needs Review */}
            {showAdvancedFilters && (
              <div className="flex flex-col gap-4 md:flex-row md:items-center border-t pt-4">
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <Input
                    type="date"
                    placeholder="Start Date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="w-[150px]"
                  />
                  <span className="text-muted-foreground">to</span>
                  <Input
                    type="date"
                    placeholder="End Date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="w-[150px]"
                  />
                </div>

                <div className="flex items-center gap-2">
                  <label
                    htmlFor="needsReview"
                    className="flex items-center gap-2 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      id="needsReview"
                      checked={needsReviewOnly}
                      onChange={(e) => setNeedsReviewOnly(e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300"
                    />
                    <AlertTriangle className="h-4 w-4 text-amber-500" />
                    <span className="text-sm">Needs Review Only</span>
                  </label>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Selection Toolbar */}
      {selectedKeys.size > 0 && (
        <div className="flex items-center justify-between rounded-lg border bg-muted/50 px-4 py-2">
          <span className="text-sm text-muted-foreground">
            {selectedKeys.size} transaction(s) selected
          </span>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleBulkEnrich}>
              <Sparkles className="mr-2 h-4 w-4" />
              AI Enrich Selected
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setBulkEditModalOpen(true)}
            >
              <Edit className="mr-2 h-4 w-4" />
              Bulk Edit
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="border-red-200 bg-red-50 text-red-700 hover:bg-red-100 hover:text-red-800 dark:border-red-800 dark:bg-red-950/50 dark:text-red-400 dark:hover:bg-red-950"
              onClick={async () => {
                try {
                  const result = await transactions.archive(Array.from(selectedKeys));
                  if (result.success) {
                    toast.success(`Archived ${result.data?.archived_count || selectedKeys.size} transaction(s)`);
                    setSelectedKeys(new Set());
                    loadTransactions();
                  } else {
                    toast.error(result.error?.message || "Failed to archive");
                  }
                } catch {
                  toast.error("Failed to archive transactions");
                }
              }}
            >
              <Archive className="mr-2 h-4 w-4" />
              Archive Selected
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelectedKeys(new Set())}
            >
              Clear Selection
            </Button>
          </div>
        </div>
      )}

      {/* Per-Page Selector and Table Controls */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          {totalItems > 0 && (
            <>
              {`${totalItems.toLocaleString()} transaction(s)`}
              {dataDateRange && (
                <span className="ml-2 text-xs">
                  ({dataDateRange.min} to {dataDateRange.max})
                </span>
              )}
            </>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Per page:</span>
          <Select
            value={String(pageSize)}
            onValueChange={(value) => {
              setPageSize(Number(value));
              setPage(1);
            }}
          >
            <SelectTrigger className="w-[80px] h-8">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="50">50</SelectItem>
              <SelectItem value="100">100</SelectItem>
              <SelectItem value="250">250</SelectItem>
              <SelectItem value="500">500</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Data Table */}
      <DataTable
        columns={filteredColumns}
        data={transactionData}
        keyField="id"
        isLoading={isLoading}
        sortKey={sortKey}
        sortDirection={sortDirection}
        onSort={handleSort}
        selectable
        selectedKeys={selectedKeys}
        onSelectionChange={setSelectedKeys}
        page={page}
        pageSize={pageSize}
        totalItems={totalItems}
        onPageChange={setPage}
        onRowClick={handleRowClick}
        emptyMessage="No transactions found"
      />

      {/* Invoice Matching Modal */}
      <InvoiceMatchingModal
        open={invoiceMatchModalOpen}
        onOpenChange={setInvoiceMatchModalOpen}
        matches={invoiceMatches}
        isLoading={isMatchingInvoices}
        onMatchUpdated={handleMatchUpdated}
      />

      {/* AI Suggestions Modal */}
      <AISuggestionsModal
        open={aiSuggestionsModalOpen}
        onOpenChange={setAiSuggestionsModalOpen}
        transactionId={selectedTransactionForAI?.id || null}
        transaction={selectedTransactionForAI}
        onSuggestionsApplied={loadTransactions}
        entityOptions={entityOptions.map((e) => e.name)}
      />

      {/* Duplicate Detection Modal */}
      <DuplicateDetectionModal
        open={duplicateModalOpen}
        onOpenChange={setDuplicateModalOpen}
        onDuplicatesResolved={loadTransactions}
      />

      {/* Internal Transfers Detection Modal */}
      <InternalTransfersModal
        open={internalTransfersModalOpen}
        onOpenChange={setInternalTransfersModalOpen}
        onTransfersApplied={loadTransactions}
      />

      {/* Bulk Edit Modal */}
      <BulkEditModal
        open={bulkEditModalOpen}
        onOpenChange={setBulkEditModalOpen}
        selectedIds={Array.from(selectedKeys)}
        entityOptions={entityOptions.map((e) => e.name)}
        onUpdated={() => {
          loadTransactions();
          setSelectedKeys(new Set());
        }}
      />

      {/* Similar Transactions Modal */}
      <SimilarTransactionsModal
        open={similarTxModalOpen}
        onOpenChange={setSimilarTxModalOpen}
        transactionId={similarTxTransactionId}
        newEntity={similarTxNewEntity}
        onUpdated={loadTransactions}
      />

      {/* Transaction Detail Drawer */}
      <TransactionDetailDrawer
        open={detailDrawerOpen}
        onOpenChange={setDetailDrawerOpen}
        transaction={selectedTransaction}
      />
    </div>
  );
}
