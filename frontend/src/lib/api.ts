/**
 * API Client for Flask Backend
 *
 * This client handles all communication with the Flask API backend.
 * In production, requests are proxied through Next.js rewrites.
 * In development, you can set FLASK_API_URL to point directly to Flask.
 */

import { getAuth } from "firebase/auth";

export interface ApiError {
  message: string;
  status: number;
  details?: unknown;
}

export interface ApiResponse<T> {
  data?: T;
  error?: ApiError;
  success: boolean;
}

// Base API URL - in production this is proxied through Next.js
const API_BASE = "/api";

// Tenant ID storage - can be set by auth context after login
let currentTenantId: string | null = null;

/**
 * Set the current tenant ID for API requests
 * This should be called by auth-context after successful login
 */
export function setApiTenantId(tenantId: string | null) {
  currentTenantId = tenantId;
}

/**
 * Get the current tenant ID
 * Falls back to localStorage if not set in memory
 */
export function getApiTenantId(): string | null {
  if (currentTenantId) return currentTenantId;
  // Fallback to localStorage for persistence across page refreshes
  if (typeof window !== "undefined") {
    return localStorage.getItem("tenantId");
  }
  return null;
}

/**
 * Get the current Firebase ID token for authenticated requests
 */
async function getAuthToken(): Promise<string | null> {
  try {
    const auth = getAuth();
    const user = auth.currentUser;
    if (user) {
      return await user.getIdToken();
    }
    return null;
  } catch (error) {
    console.error("Failed to get auth token:", error);
    return null;
  }
}

/**
 * Generic fetch wrapper with error handling
 */
async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const url = `${API_BASE}${endpoint}`;

  const defaultHeaders: HeadersInit = {
    "Content-Type": "application/json",
  };

  // Get auth token and add to headers if available
  const token = await getAuthToken();
  if (token) {
    (defaultHeaders as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  }

  // Add tenant ID header if available
  const tenantId = getApiTenantId();
  if (tenantId) {
    (defaultHeaders as Record<string, string>)["X-Tenant-ID"] = tenantId;
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
      credentials: "include", // Include cookies for session management
    });

    // Parse response
    let data: T | undefined;
    const contentType = response.headers.get("content-type");

    if (contentType?.includes("application/json")) {
      data = await response.json();
    }

    if (!response.ok) {
      return {
        success: false,
        error: {
          message:
            (data as { error?: string })?.error ||
            `Request failed with status ${response.status}`,
          status: response.status,
          details: data,
        },
      };
    }

    return {
      success: true,
      data,
    };
  } catch (error) {
    console.error("API request failed:", error);
    return {
      success: false,
      error: {
        message:
          error instanceof Error ? error.message : "Network error occurred",
        status: 0,
      },
    };
  }
}

/**
 * GET request
 */
export async function get<T>(endpoint: string): Promise<ApiResponse<T>> {
  return fetchApi<T>(endpoint, { method: "GET" });
}

/**
 * POST request
 */
export async function post<T>(
  endpoint: string,
  body?: unknown
): Promise<ApiResponse<T>> {
  return fetchApi<T>(endpoint, {
    method: "POST",
    body: body ? JSON.stringify(body) : undefined,
  });
}

/**
 * PUT request
 */
export async function put<T>(
  endpoint: string,
  body?: unknown
): Promise<ApiResponse<T>> {
  return fetchApi<T>(endpoint, {
    method: "PUT",
    body: body ? JSON.stringify(body) : undefined,
  });
}

/**
 * DELETE request
 */
export async function del<T>(endpoint: string): Promise<ApiResponse<T>> {
  return fetchApi<T>(endpoint, { method: "DELETE" });
}

/**
 * PATCH request
 */
export async function patch<T>(
  endpoint: string,
  body?: unknown
): Promise<ApiResponse<T>> {
  return fetchApi<T>(endpoint, {
    method: "PATCH",
    body: body ? JSON.stringify(body) : undefined,
  });
}

/**
 * Upload file(s)
 */
export async function upload<T>(
  endpoint: string,
  files: File | File[],
  additionalData?: Record<string, string>
): Promise<ApiResponse<T>> {
  const formData = new FormData();

  if (Array.isArray(files)) {
    files.forEach((file, index) => {
      formData.append(`file${index}`, file);
    });
  } else {
    formData.append("file", files);
  }

  if (additionalData) {
    Object.entries(additionalData).forEach(([key, value]) => {
      formData.append(key, value);
    });
  }

  const url = `${API_BASE}${endpoint}`;

  // Get auth token for authenticated uploads
  const token = await getAuthToken();
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Add tenant ID header if available
  const tenantId = getApiTenantId();
  if (tenantId) {
    headers["X-Tenant-ID"] = tenantId;
  }

  try {
    const response = await fetch(url, {
      method: "POST",
      headers,
      body: formData,
      credentials: "include",
      // Note: Don't set Content-Type header - browser will set it with boundary
    });

    const data = await response.json();

    if (!response.ok) {
      return {
        success: false,
        error: {
          message: data.error || `Upload failed with status ${response.status}`,
          status: response.status,
          details: data,
        },
      };
    }

    return {
      success: true,
      data,
    };
  } catch (error) {
    console.error("Upload failed:", error);
    return {
      success: false,
      error: {
        message: error instanceof Error ? error.message : "Upload failed",
        status: 0,
      },
    };
  }
}

// ============================================
// API Endpoints - Organized by Feature
// ============================================

// --- Homepage ---
export const homepage = {
  getContent: () => get<HomepageContent>("/homepage/content"),
  regenerate: () => post<HomepageContent>("/homepage/regenerate"),
  getData: () => get<HomepageData>("/homepage/data"),
  getKpis: () => get<HomepageKpis>("/homepage/kpis"),
};

// --- Transactions ---
export const transactions = {
  list: (params?: TransactionListParams) => {
    const query = new URLSearchParams(params as Record<string, string>);
    return get<TransactionListResponse>(`/transactions?${query}`);
  },
  get: (id: string) => get<Transaction>(`/transactions/${id}/details`),
  update: (id: string, data: Partial<Transaction>) =>
    post<Transaction>("/update_transaction", { transaction_id: id, ...data }),
  updateField: (id: string, field: string, value: string) =>
    post<{ success: boolean; updated_confidence?: number }>("/update_transaction", {
      transaction_id: id,
      field,
      value,
    }),
  enrich: (id: string) => post<Transaction>(`/transactions/${id}/enrich`),
  bulkEnrich: (ids: string[]) =>
    post<BulkEnrichResponse>("/transactions/enrich/bulk", { ids }),
  detectInternalTransfers: () =>
    post<InternalTransfersResponse>("/transactions/detect-internal-transfers"),
  applyInternalTransfer: (pairs: TransactionPair[]) =>
    post<ApplyInternalTransferResponse>("/transactions/apply-internal-transfer", {
      transaction_pairs: pairs,
    }),
  bulkUpdate: (updates: BulkUpdateItem[]) =>
    post<BulkUpdateResponse>("/bulk_update_transactions", { updates }),
  archive: (ids: string[]) =>
    post<{ archived_count: number }>("/archive_transactions", { transaction_ids: ids }),
  unarchive: (ids: string[]) =>
    post<{ unarchived_count: number }>("/unarchive_transactions", { transaction_ids: ids }),
  getStats: (params?: DashboardStatsParams) => {
    const query = params ? new URLSearchParams(params as Record<string, string>) : "";
    return get<DashboardStats>(`/stats?${query}`);
  },
};

// --- Invoices ---
export const invoices = {
  list: (params?: InvoiceListParams) => {
    const query = new URLSearchParams(params as Record<string, string>);
    return get<InvoiceListResponse>(`/invoices?${query}`);
  },
  get: (id: string) => get<Invoice>(`/invoices/${id}/details`),
  create: (data: CreateInvoiceData) => post<Invoice>("/invoices", data),
  update: (id: string, data: Partial<Invoice>) =>
    put<Invoice>(`/invoices/${id}`, data),
  delete: (id: string) => del<void>(`/invoices/${id}`),
  markPaid: (id: string, data: MarkPaidData) =>
    post<Invoice>(`/invoices/${id}/mark-paid`, data),
  findMatches: (id: string) =>
    get<MatchResult[]>(`/invoices/${id}/find-matching-transactions`),
  linkTransaction: (id: string, transactionId: string) =>
    post<void>(`/invoices/${id}/link-transaction`, {
      transaction_id: transactionId,
    }),
  // Attachments
  getAttachments: (id: string) =>
    get<InvoiceAttachment[]>(`/invoices/${id}/attachments`),
  uploadAttachment: (id: string, file: File) =>
    upload<InvoiceAttachment>(`/invoices/${id}/attachments`, file),
  deleteAttachment: (id: string, attachmentId: string) =>
    del<void>(`/invoices/${id}/attachments/${attachmentId}`),
  // Payments
  getPayments: (id: string) =>
    get<InvoicePayment[]>(`/invoices/${id}/payments`),
  addPayment: (id: string, data: AddPaymentData) =>
    post<InvoicePayment>(`/invoices/${id}/payments`, data),
  deletePayment: (id: string, paymentId: string) =>
    del<void>(`/invoices/${id}/payments/${paymentId}`),
  uploadPaymentReceipt: (id: string, paymentId: string, file: File) =>
    upload<PaymentReceipt>(`/invoices/${id}/payments/${paymentId}/receipt`, file),
};

// --- Revenue Matching ---
export const revenue = {
  runMatching: () => post<MatchingRunResult>("/revenue/run-matching"),
  getPendingMatches: (params?: PaginationParams) => {
    const query = new URLSearchParams(params as Record<string, string>);
    return get<PendingMatchesResponse>(`/revenue/pending-matches?${query}`);
  },
  confirmMatch: (invoiceId: string, transactionId: string) =>
    post<void>("/revenue/confirm-match", {
      invoice_id: invoiceId,
      transaction_id: transactionId,
    }),
  rejectMatch: (invoiceId: string, transactionId: string) =>
    post<void>("/revenue/reject-match", {
      invoice_id: invoiceId,
      transaction_id: transactionId,
    }),
  manualMatch: (invoiceId: string, transactionId: string) =>
    post<void>("/revenue/manual-match", {
      invoice_id: invoiceId,
      transaction_id: transactionId,
    }),
  getMatchedPairs: (params?: PaginationParams) => {
    const query = new URLSearchParams(params as Record<string, string>);
    return get<MatchedPairsResponse>(`/revenue/matched-pairs?${query}`);
  },
  unmatch: (invoiceId: string) =>
    post<void>("/revenue/unmatch", { invoice_id: invoiceId }),
  getStats: () => get<MatchingStats>("/revenue/stats"),
  getSyncNotification: () =>
    get<{
      has_notification: boolean;
      count?: number;
      timestamp?: string;
      changes?: Array<{ description: string; old_category: string; new_category: string }>;
    }>("/revenue/sync-notification"),
};

// --- Workforce ---
export const workforce = {
  list: (params?: PaginationParams) => {
    const query = new URLSearchParams(params as Record<string, string>);
    return get<WorkforceListResponse>(`/workforce?${query}`);
  },
  get: (id: string) => get<WorkforceMember>(`/workforce/${id}`),
  create: (data: CreateWorkforceMemberData) =>
    post<WorkforceMember>("/workforce", data),
  update: (id: string, data: Partial<WorkforceMember>) =>
    put<WorkforceMember>(`/workforce/${id}`, data),
  delete: (id: string) => del<void>(`/workforce/${id}`),
};

// --- Payslips ---
export const payslips = {
  list: (params?: PaginationParams) => {
    const query = new URLSearchParams(params as Record<string, string>);
    return get<PayslipListResponse>(`/payslips?${query}`);
  },
  get: (id: string) => get<Payslip>(`/payslips/${id}`),
  create: (data: CreatePayslipData) => post<Payslip>("/payslips", data),
  update: (id: string, data: Partial<Payslip>) =>
    put<Payslip>(`/payslips/${id}`, data),
  delete: (id: string) => del<void>(`/payslips/${id}`),
  markPaid: (id: string) => post<Payslip>(`/payslips/${id}/mark-paid`),
  findMatches: (id: string) =>
    get<MatchResult[]>(`/payslips/${id}/find-matching-transactions`),
  linkTransaction: (id: string, transactionId: string) =>
    post<void>(`/payslips/${id}/link-transaction`, {
      transaction_id: transactionId,
    }),
};

// --- Payroll Matching ---
export const payroll = {
  runMatching: () => post<MatchingRunResult>("/payroll/run-matching"),
  getMatchedPairs: (params?: PaginationParams) => {
    const query = new URLSearchParams(params as Record<string, string>);
    return get<MatchedPairsResponse>(`/payroll/matched-pairs?${query}`);
  },
  getStats: () => get<MatchingStats>("/payroll/stats"),
};

// --- Bank Accounts ---
export const bankAccounts = {
  list: () => get<BankAccount[]>("/bank-accounts"),
  create: (data: CreateBankAccountData) =>
    post<BankAccount>("/bank-accounts", data),
  update: (id: string, data: Partial<BankAccount>) =>
    put<BankAccount>(`/bank-accounts/${id}`, data),
  delete: (id: string) => del<void>(`/bank-accounts/${id}`),
};

// --- Crypto Wallets ---
export const wallets = {
  list: () => get<Wallet[]>("/wallets"),
  create: (data: CreateWalletData) => post<Wallet>("/wallets", data),
  update: (id: string, data: Partial<Wallet>) =>
    put<Wallet>(`/wallets/${id}`, data),
  delete: (id: string) => del<void>(`/wallets/${id}`),
};

// --- Shareholders ---
export const shareholders = {
  list: () => get<Shareholder[]>("/shareholders"),
  create: (data: CreateShareholderData) =>
    post<Shareholder>("/shareholders", data),
  update: (id: string, data: Partial<Shareholder>) =>
    put<Shareholder>(`/shareholders/${id}`, data),
  delete: (id: string) => del<void>(`/shareholders/${id}`),
  getChartData: () => get<ShareholderChartData>("/shareholders/chart-data"),
};

// --- Equity Contributions ---
export const equityContributions = {
  list: () => get<EquityContribution[]>("/equity-contributions"),
  create: (data: CreateEquityContributionData) =>
    post<EquityContribution>("/equity-contributions", data),
  delete: (id: string) => del<void>(`/equity-contributions/${id}`),
};

// --- Tenant ---
export const tenant = {
  getConfig: (type: string) => get<TenantConfig>(`/tenant/config/${type}`),
  updateConfig: (type: string, data: Partial<TenantConfig>) =>
    put<TenantConfig>(`/tenant/config/${type}`, data),
  getIndustries: () => get<Industry[]>("/tenant/industries"),
  applyIndustryTemplate: (key: string) =>
    post<void>(`/tenant/industries/${key}/apply`),
};

// --- Knowledge ---
export const knowledge = {
  list: () => get<ClassificationPattern[]>("/tenant-knowledge"),
  create: (data: CreatePatternData) =>
    post<ClassificationPattern>("/tenant-knowledge", data),
  update: (id: string, data: Partial<ClassificationPattern>) =>
    put<ClassificationPattern>(`/tenant-knowledge/${id}`, data),
  delete: (id: string) => del<void>(`/tenant-knowledge/${id}`),
  generate: () => post<GeneratedPatterns>("/knowledge-generator/run"),
};

// --- Suggestions ---
export interface SuggestionsParams {
  field_type: string;
  transaction_id?: string;
  current_value?: string;
  value?: string;
}

export interface SuggestionsResponse {
  suggestions: string[];
  has_learned_patterns?: boolean;
  error?: string;
}

export const suggestions = {
  get: (params: SuggestionsParams) => {
    const queryParams: Record<string, string> = {};
    if (params.field_type) queryParams.field_type = params.field_type;
    if (params.transaction_id) queryParams.transaction_id = params.transaction_id;
    if (params.current_value) queryParams.current_value = params.current_value;
    if (params.value) queryParams.value = params.value;
    const query = new URLSearchParams(queryParams);
    return get<SuggestionsResponse>(`/suggestions?${query}`);
  },
};

// --- Auth ---
export const auth = {
  login: (token: string) => post<AuthResponse>("/auth/login", { token }),
  register: (data: RegisterData) => post<AuthResponse>("/auth/register", data),
  getProfile: () => get<UserProfile>("/user/profile"),
  updateProfile: (data: Partial<UserProfile>) =>
    post<UserProfile>("/user/profile", data),
  updateLanguage: (language: string) =>
    post<void>("/user/language", { language }),
};

// --- Users ---
export const users = {
  list: (params?: PaginationParams) => {
    const query = new URLSearchParams(params as Record<string, string>);
    return get<UsersListResponse>(`/users?${query}`);
  },
  get: (id: string) => get<TenantUser>(`/users/${id}`),
  invite: (data: InviteUserData) => post<UserInvitation>("/users/invite", data),
  updateRole: (id: string, role: string, permissions: string[]) =>
    put<TenantUser>(`/users/${id}/role`, { role, permissions }),
  remove: (id: string) => del<void>(`/users/${id}`),
  resendInvitation: (id: string) =>
    post<void>(`/users/invitations/${id}/resend`),
  cancelInvitation: (id: string) =>
    del<void>(`/users/invitations/${id}`),
  getPendingInvitations: () =>
    get<UserInvitation[]>("/users/invitations/pending"),
};

// --- Month-End Close ---
export const monthEndClose = {
  // Periods
  listPeriods: (params?: PeriodListParams) => {
    const query = new URLSearchParams(params as Record<string, string>);
    return get<PeriodListResponse>(`/close/periods?${query}`);
  },
  getPeriod: (id: string) => get<AccountingPeriod>(`/close/periods/${id}`),
  createPeriod: (data: CreatePeriodData) =>
    post<AccountingPeriod>("/close/periods", data),
  updatePeriod: (id: string, data: Partial<AccountingPeriod>) =>
    put<AccountingPeriod>(`/close/periods/${id}`, data),

  // Period Workflow Actions
  startCloseProcess: (id: string) =>
    post<AccountingPeriod>(`/close/periods/${id}/start`),
  lockPeriod: (id: string) =>
    post<AccountingPeriod>(`/close/periods/${id}/lock`),
  unlockPeriod: (id: string, reason: string) =>
    post<AccountingPeriod>(`/close/periods/${id}/unlock`, { reason }),
  submitForApproval: (id: string) =>
    post<AccountingPeriod>(`/close/periods/${id}/submit`),
  approvePeriod: (id: string) =>
    post<AccountingPeriod>(`/close/periods/${id}/approve`),
  rejectPeriod: (id: string, reason: string) =>
    post<AccountingPeriod>(`/close/periods/${id}/reject`, { reason }),
  closePeriod: (id: string) =>
    post<AccountingPeriod>(`/close/periods/${id}/close`),

  // Checklist
  getChecklist: (periodId: string) =>
    get<ChecklistItem[]>(`/close/periods/${periodId}/checklist`),
  updateChecklistItem: (itemId: string, data: UpdateChecklistItemData) =>
    put<ChecklistItem>(`/close/checklist/${itemId}`, data),
  completeChecklistItem: (itemId: string) =>
    post<ChecklistItem>(`/close/checklist/${itemId}/complete`),
  skipChecklistItem: (itemId: string, reason: string) =>
    post<ChecklistItem>(`/close/checklist/${itemId}/skip`, { reason }),
  runAutoCheck: (itemId: string) =>
    post<ChecklistItem>(`/close/checklist/${itemId}/run-auto-check`),
  runAllAutoChecks: (periodId: string) =>
    post<{ results: AutoCheckResult[] }>(`/close/periods/${periodId}/run-auto-checks`),

  // Reconciliation Status
  getReconciliationStatus: (periodId: string) =>
    get<ReconciliationStatus>(`/close/periods/${periodId}/reconciliation-status`),
  getInvoiceStats: (periodId: string) =>
    get<InvoiceReconciliationStats>(`/close/periods/${periodId}/invoice-stats`),
  getPayslipStats: (periodId: string) =>
    get<PayslipReconciliationStats>(`/close/periods/${periodId}/payslip-stats`),
  getTransactionStats: (periodId: string) =>
    get<TransactionReconciliationStats>(`/close/periods/${periodId}/transaction-stats`),
  getUnmatchedItems: (periodId: string, type: string) =>
    get<UnmatchedItemsResponse>(`/close/periods/${periodId}/unmatched-items?type=${type}`),

  // Adjusting Entries
  listEntries: (periodId: string, params?: EntryListParams) => {
    const query = new URLSearchParams(params as Record<string, string>);
    return get<EntryListResponse>(`/close/periods/${periodId}/entries?${query}`);
  },
  getEntry: (entryId: string) =>
    get<AdjustingEntry>(`/close/entries/${entryId}`),
  createEntry: (periodId: string, data: CreateEntryData) =>
    post<AdjustingEntry>(`/close/periods/${periodId}/entries`, data),
  updateEntry: (entryId: string, data: Partial<AdjustingEntry>) =>
    put<AdjustingEntry>(`/close/entries/${entryId}`, data),
  deleteEntry: (entryId: string) =>
    del<void>(`/close/entries/${entryId}`),
  submitEntry: (entryId: string) =>
    post<AdjustingEntry>(`/close/entries/${entryId}/submit`),
  approveEntry: (entryId: string) =>
    post<AdjustingEntry>(`/close/entries/${entryId}/approve`),
  rejectEntry: (entryId: string, reason: string) =>
    post<AdjustingEntry>(`/close/entries/${entryId}/reject`, { reason }),
  postEntry: (entryId: string) =>
    post<AdjustingEntry>(`/close/entries/${entryId}/post`),
  revertEntry: (entryId: string) =>
    post<AdjustingEntry>(`/close/entries/${entryId}/revert`),
  getEntriesSummary: (periodId: string) =>
    get<EntriesSummary>(`/close/periods/${periodId}/entries-summary`),

  // Activity Log
  getActivityLog: (periodId: string, params?: PaginationParams) => {
    const query = new URLSearchParams(params as Record<string, string>);
    return get<ActivityLogResponse>(`/close/periods/${periodId}/activity-log?${query}`);
  },
};

// ============================================
// Type Definitions
// ============================================

// Common types
export interface PaginationParams {
  page?: string;
  per_page?: string;
}

// Homepage types
export interface HomepageContent {
  company_name: string;
  company_description: string;
  kpis: KpiData[];
  insights: string[];
  cached_at: string;
}

export interface HomepageData {
  entities: BusinessEntity[];
  stats: DashboardStats;
}

export interface HomepageKpis {
  total_revenue: number;
  total_expenses: number;
  net_income: number;
  transaction_count: number;
}

export interface KpiData {
  label: string;
  value: number;
  change?: number;
  format: "currency" | "number" | "percent";
}

export interface BusinessEntity {
  id: string;
  name: string;
  type: string;
  description?: string;
}

export interface DashboardStats {
  total_transactions: number;
  pending_matches: number;
  matched_invoices: number;
}

// Transaction types
export interface Transaction {
  id: string;
  date: string;
  description: string;
  amount: number;
  currency: string;
  usd_equivalent?: number;
  crypto_amount?: number;
  category?: string;
  subcategory?: string;
  entity_id?: string;
  entity_name?: string;
  confidence_score?: number;
  matched_invoice_id?: string;
  invoice_id?: string;
  notes?: string;
  origin?: string;
  destination?: string;
  justification?: string;
  source_file?: string;
  needs_review?: boolean;
  archived?: boolean;
  created_at: string;
  updated_at: string;
}

export interface TransactionListParams extends PaginationParams {
  start_date?: string;
  end_date?: string;
  category?: string;
  entity_id?: string;
  search?: string;
}

export interface TransactionListResponse {
  transactions: Transaction[];
  total: number;
  page: number;
  per_page: number;
}

export interface BulkEnrichResponse {
  enriched: number;
  failed: number;
}

// Dashboard Stats types
export interface DashboardStatsParams {
  start_date?: string;
  end_date?: string;
  category?: string;
  entity?: string;
}

export interface DashboardStats {
  total_transactions: number;
  total_revenue: number;
  total_expenses: number;
  needs_review: number;
  date_range: {
    min: string;
    max: string;
  };
}

// Internal Transfer types
export interface InternalTransferMatch {
  tx1: Transaction;
  tx2: Transaction;
  match_score: number;
  match_reasons: string[];
}

export interface InternalTransfersResponse {
  success: boolean;
  matches: InternalTransferMatch[];
  total_matches: number;
}

export interface TransactionPair {
  tx1_id: string;
  tx2_id: string;
}

export interface ApplyInternalTransferResponse {
  success: boolean;
  message: string;
  updated_count: number;
}

// Bulk Update types (for drag-fill)
export interface BulkUpdateItem {
  transaction_id: string;
  field: string;
  value: string;
}

export interface BulkUpdateResponse {
  success: boolean;
  updated_count: number;
  failed_count: number;
  errors: Array<{
    index: number;
    transaction_id: string;
    error: string;
  }>;
}

// Invoice types
export interface Invoice {
  id: string;
  invoice_number: string;
  vendor_name: string;
  client_name?: string;
  issue_date: string;
  due_date: string;
  total_amount: number;
  currency: string;
  status: "draft" | "sent" | "paid" | "overdue" | "partial";
  payment_status?: string;
  matched_transaction_id?: string;
  line_items: InvoiceLineItem[];
  attachments: InvoiceAttachment[];
  created_at: string;
  updated_at: string;
}

export interface InvoiceLineItem {
  description: string;
  quantity: number;
  unit_price: number;
  total: number;
}

export interface InvoiceAttachment {
  id: string;
  filename: string;
  url: string;
  file_size?: number;
  content_type?: string;
  uploaded_at: string;
}

export interface InvoicePayment {
  id: string;
  invoice_id: string;
  payment_date: string;
  amount: number;
  currency: string;
  payment_method?: string;
  reference_number?: string;
  notes?: string;
  receipt?: PaymentReceipt;
  created_at: string;
  updated_at: string;
}

export interface PaymentReceipt {
  id: string;
  filename: string;
  url: string;
  file_size?: number;
  content_type?: string;
  uploaded_at: string;
}

export interface AddPaymentData {
  payment_date: string;
  amount: number;
  currency?: string;
  payment_method?: string;
  reference_number?: string;
  notes?: string;
}

export interface InvoiceListParams extends PaginationParams {
  status?: string;
  vendor_name?: string;
  start_date?: string;
  end_date?: string;
  search?: string;
}

export interface InvoiceListResponse {
  invoices: Invoice[];
  total: number;
  page: number;
  per_page: number;
}

export interface CreateInvoiceData {
  invoice_number: string;
  vendor_name: string;
  client_name?: string;
  issue_date: string;
  due_date: string;
  total_amount: number;
  currency: string;
  line_items?: InvoiceLineItem[];
}

export interface MarkPaidData {
  payment_date: string;
  payment_amount: number;
  payment_method?: string;
  notes?: string;
}

// Matching types
export interface MatchResult {
  transaction_id: string;
  transaction: Transaction;
  confidence_score: number;
  match_reasons: string[];
}

export interface MatchingRunResult {
  matches_found: number;
  auto_confirmed: number;
  pending_review: number;
}

export interface PendingMatchesResponse {
  matches: PendingMatch[];
  total: number;
  page: number;
  per_page: number;
}

export interface PendingMatch {
  invoice: Invoice;
  transaction: Transaction;
  confidence_score: number;
  match_reasons: string[];
}

export interface MatchedPairsResponse {
  pairs: MatchedPair[];
  total: number;
  page: number;
  per_page: number;
}

export interface MatchedPair {
  invoice: Invoice;
  transaction: Transaction;
  matched_at: string;
  match_method: "auto" | "manual";
}

export interface MatchingStats {
  total_invoices: number;
  matched_invoices: number;
  pending_matches: number;
  unmatched_invoices: number;
  match_rate: number;
}

// Workforce types
export interface WorkforceMember {
  id: string;
  full_name: string;
  email: string;
  employment_type: "employee" | "contractor";
  job_title?: string;
  department?: string;
  date_of_hire: string;
  termination_date?: string;
  status: "active" | "inactive";
  pay_rate: number;
  pay_frequency: "monthly" | "biweekly" | "weekly";
  currency: string;
  phone?: string;
  address?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface WorkforceListResponse {
  members: WorkforceMember[];
  total: number;
  page: number;
  per_page: number;
}

export interface CreateWorkforceMemberData {
  full_name: string;
  email: string;
  employment_type: "employee" | "contractor";
  job_title?: string;
  department?: string;
  date_of_hire: string;
  pay_rate: number;
  pay_frequency: "monthly" | "biweekly" | "weekly";
  currency: string;
}

// Payslip types
export interface Payslip {
  id: string;
  workforce_member_id: string;
  workforce_member_name: string;
  payslip_number: string;
  pay_period_start: string;
  pay_period_end: string;
  payment_date: string;
  gross_amount: number;
  deductions: number;
  net_amount: number;
  currency: string;
  status: "draft" | "approved" | "paid";
  line_items: PayslipLineItem[];
  matched_transaction_id?: string;
  created_at: string;
  updated_at: string;
}

export interface PayslipLineItem {
  description: string;
  type: "earning" | "deduction";
  amount: number;
}

export interface PayslipListResponse {
  payslips: Payslip[];
  total: number;
  page: number;
  per_page: number;
}

export interface CreatePayslipData {
  workforce_member_id: string;
  payslip_number: string;
  pay_period_start: string;
  pay_period_end: string;
  payment_date: string;
  gross_amount: number;
  deductions: number;
  net_amount: number;
  currency: string;
  line_items?: PayslipLineItem[];
}

// Bank Account types
export interface BankAccount {
  id: string;
  account_name: string;
  bank_name: string;
  account_number: string;
  account_type: "checking" | "savings" | "credit" | "investment" | "loan";
  currency: string;
  status: "active" | "inactive";
  balance?: number;
  entity_id?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateBankAccountData {
  account_name: string;
  bank_name: string;
  account_number: string;
  account_type: "checking" | "savings" | "credit" | "investment" | "loan";
  currency: string;
  entity_id?: string;
  notes?: string;
}

// Wallet types
export interface Wallet {
  id: string;
  wallet_name: string;
  address: string;
  blockchain: string;
  status: "active" | "inactive";
  balance?: number;
  entity_id?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateWalletData {
  wallet_name: string;
  address: string;
  blockchain: string;
  entity_id?: string;
  notes?: string;
}

// Shareholder types
export interface Shareholder {
  id: string;
  name: string;
  email?: string;
  ownership_percentage: number;
  share_class?: string;
  investment_date?: string;
  total_invested: number;
  currency: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface ShareholderChartData {
  labels: string[];
  values: number[];
  colors: string[];
}

export interface CreateShareholderData {
  name: string;
  email?: string;
  ownership_percentage: number;
  share_class?: string;
  investment_date?: string;
  total_invested?: number;
  currency?: string;
}

// Equity Contribution types
export interface EquityContribution {
  id: string;
  shareholder_id: string;
  shareholder_name: string;
  amount: number;
  currency: string;
  contribution_date: string;
  contribution_type: string;
  notes?: string;
  created_at: string;
}

export interface CreateEquityContributionData {
  shareholder_id: string;
  amount: number;
  currency: string;
  contribution_date: string;
  contribution_type: string;
  notes?: string;
}

// Tenant types
export interface TenantConfig {
  id: string;
  tenant_id: string;
  company_name: string;
  company_description?: string;
  industry?: string;
  primary_currency: string;
  timezone: string;
  branding?: {
    logo_url?: string;
    primary_color?: string;
    secondary_color?: string;
  };
}

export interface Industry {
  key: string;
  name: string;
  description: string;
}

// Knowledge types
export interface ClassificationPattern {
  id: string;
  pattern: string;
  category: string;
  subcategory?: string;
  confidence: number;
  entity_id?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreatePatternData {
  pattern: string;
  category: string;
  subcategory?: string;
  confidence?: number;
  entity_id?: string;
}

export interface GeneratedPatterns {
  patterns: ClassificationPattern[];
  count: number;
}

// Auth types
export interface AuthResponse {
  success: boolean;
  user?: UserProfile;
  token?: string;
  error?: string;
}

export interface RegisterData {
  email: string;
  name: string;
  user_type: "fractional_cfo" | "tenant_admin" | "employee";
  company_name?: string;
}

export interface UserProfile {
  id: string;
  firebase_uid: string;
  email: string;
  name: string;
  user_type: string;
  language: string;
  tenants: UserTenant[];
  created_at: string;
  updated_at: string;
}

export interface UserTenant {
  tenant_id: string;
  tenant_name: string;
  role: string;
  permissions: string[];
}

// User management types
export interface TenantUser {
  id: string;
  user_id: string;
  tenant_id: string;
  email: string;
  name: string;
  user_type: "fractional_cfo" | "cfo_assistant" | "tenant_admin" | "employee";
  role: string;
  permissions: string[];
  status: "active" | "inactive" | "pending";
  last_login?: string;
  created_at: string;
  updated_at: string;
}

export interface UsersListResponse {
  users: TenantUser[];
  total: number;
  page: number;
  per_page: number;
}

export interface InviteUserData {
  email: string;
  name: string;
  user_type: "cfo_assistant" | "tenant_admin" | "employee";
  role: string;
  permissions: string[];
}

export interface UserInvitation {
  id: string;
  email: string;
  name: string;
  user_type: string;
  role: string;
  status: "pending" | "accepted" | "expired";
  expires_at: string;
  created_at: string;
}

// Chatbot types
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatbotRequest {
  message: string;
  history: ChatMessage[];
}

export interface ChatbotResponse {
  response: string;
  tenant_id: string;
}

/**
 * Chatbot API
 */
export const chatbot = {
  /**
   * Send a message to the AI CFO Assistant
   */
  sendMessage: (message: string, history: ChatMessage[] = []) =>
    post<ChatbotResponse>("/chatbot", { message, history }),
};

// --- Reports ---
/**
 * Download file helper for PDF/blob responses
 */
async function downloadFile(
  endpoint: string,
  filename: string,
  params?: Record<string, string>
): Promise<ApiResponse<Blob>> {
  const query = params ? `?${new URLSearchParams(params)}` : "";
  const url = `${API_BASE}${endpoint}${query}`;

  // Get auth token for authenticated downloads
  const token = await getAuthToken();
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Add tenant ID header if available
  const tenantId = getApiTenantId();
  if (tenantId) {
    headers["X-Tenant-ID"] = tenantId;
  }

  try {
    const response = await fetch(url, {
      method: "GET",
      headers,
      credentials: "include",
    });

    if (!response.ok) {
      const errorText = await response.text();
      return {
        success: false,
        error: {
          message: errorText || `Download failed with status ${response.status}`,
          status: response.status,
        },
      };
    }

    const blob = await response.blob();

    // Trigger browser download
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);

    return {
      success: true,
      data: blob,
    };
  } catch (error) {
    console.error("Download failed:", error);
    return {
      success: false,
      error: {
        message: error instanceof Error ? error.message : "Download failed",
        status: 0,
      },
    };
  }
}

export interface ReportParams {
  start_date?: string;
  end_date?: string;
  entity_id?: string;
  currency?: string;
}

export interface PlTrendData {
  labels: string[];
  revenue: number[];
  expenses: number[];
  net_income: number[];
}

export interface IncomeStatementData {
  period: string;
  revenue: {
    items: { name: string; amount: number }[];
    total: number;
  };
  expenses: {
    items: { name: string; amount: number }[];
    total: number;
  };
  net_income: number;
}

export interface DreData {
  period: string;
  sections: {
    name: string;
    items: { description: string; amount: number }[];
    subtotal: number;
  }[];
  totals: {
    gross_revenue: number;
    total_deductions: number;
    net_revenue: number;
    total_costs: number;
    gross_profit: number;
    total_expenses: number;
    operating_income: number;
    net_income: number;
  };
}

// Sankey diagram types
export interface SankeyNode {
  name: string;
  type: "revenue" | "expense" | "category" | "subcategory";
  value?: number;
}

export interface SankeyLink {
  source: number;
  target: number;
  value: number;
}

export interface SankeyFlowParams {
  start_date?: string;
  end_date?: string;
  min_amount?: string;
  max_categories?: string;
  keyword?: string;
  entity?: string;
  accounting_category?: string;
  accounting_subcategory?: string;
}

export interface SankeyFlowData {
  sankey: {
    nodes: SankeyNode[];
    links: SankeyLink[];
  };
  summary: {
    total_revenue: number;
    total_expenses: number;
    net_flow: number;
    revenue_categories: number;
    expense_categories: number;
    date_range?: {
      start_date: string;
      end_date: string;
    };
  };
  parameters: {
    min_amount: number;
    max_categories: number;
  };
}

export interface SankeyTransactionParams {
  subcategory: string;
  type: "revenue" | "expense";
  start_date?: string;
  end_date?: string;
  limit?: string;
}

export interface SankeyTransactionsData {
  transactions: Transaction[];
  summary: {
    total_amount: number;
    transaction_count: number;
    date_range?: {
      start_date: string;
      end_date: string;
    };
  };
}

export interface SankeyBreakdownParams {
  node_name: string;
  node_type: "revenue" | "expense";
  start_date?: string;
  end_date?: string;
}

export interface SankeyBreakdownItem {
  keyword: string;
  amount: number;
  count: number;
  percentage: number;
}

export interface SankeyBreakdownData {
  node_name: string;
  node_type: string;
  total_amount: number;
  transaction_count: number;
  breakdown: SankeyBreakdownItem[];
  top_transactions: Transaction[];
}

export const reports = {
  // PDF Downloads
  downloadDrePdf: (params?: ReportParams) =>
    downloadFile(
      "/reports/dre-pdf",
      `dre-${params?.start_date || "report"}.pdf`,
      params as Record<string, string>
    ),
  downloadBalanceSheetPdf: (params?: ReportParams) =>
    downloadFile(
      "/reports/balance-sheet-pdf",
      `balance-sheet-${params?.start_date || "report"}.pdf`,
      params as Record<string, string>
    ),
  downloadCashFlowPdf: (params?: ReportParams) =>
    downloadFile(
      "/reports/cash-flow-pdf",
      `cash-flow-${params?.start_date || "report"}.pdf`,
      params as Record<string, string>
    ),

  // JSON Data APIs
  getIncomeStatement: (params?: ReportParams) => {
    const query = params ? new URLSearchParams(params as Record<string, string>) : "";
    return get<IncomeStatementData>(`/reports/income-statement/simple?${query}`);
  },
  getPlTrend: (params?: { months?: string }) => {
    const query = params ? new URLSearchParams(params as Record<string, string>) : "";
    return get<PlTrendData>(`/reports/pl-trend?${query}`);
  },
  getDreData: (params?: ReportParams) => {
    const query = params ? new URLSearchParams(params as Record<string, string>) : "";
    return get<DreData>(`/reports/dre?${query}`);
  },

  // Sankey Flow Diagram APIs
  getSankeyFlow: (params?: SankeyFlowParams) => {
    const query = params ? new URLSearchParams(params as Record<string, string>) : "";
    return get<SankeyFlowData>(`/reports/sankey-flow?${query}`);
  },
  getSankeyTransactions: (params: SankeyTransactionParams) => {
    const query = new URLSearchParams(params as unknown as Record<string, string>);
    return get<SankeyTransactionsData>(`/reports/sankey-transactions?${query}`);
  },
  getSankeyBreakdown: (params: SankeyBreakdownParams) =>
    post<SankeyBreakdownData>("/reports/sankey-breakdown", params),
};

// --- Transaction Export ---
export interface ExportParams {
  start_date?: string;
  end_date?: string;
  category?: string;
  entity_id?: string;
  format?: "csv" | "xlsx";
}

export const exports = {
  transactions: (params?: ExportParams) => {
    const format = params?.format || "csv";
    const filename = `transactions-export.${format}`;
    return downloadFile("/transactions/export", filename, params as Record<string, string>);
  },
};

// --- File Management ---
export interface UploadedFileData {
  id: string;
  name: string;
  type: string;
  size: number;
  mime_type: string;
  uploaded_by: string | null;
  uploaded_at: string | null;
  hash: string | null;
}

export interface FilesListResponse {
  files: UploadedFileData[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface FilesListParams {
  page?: number;
  per_page?: number;
  type?: string;
}

export const files = {
  list: (params?: FilesListParams) => {
    const queryParams: Record<string, string> = {};
    if (params?.page) queryParams.page = String(params.page);
    if (params?.per_page) queryParams.per_page = String(params.per_page);
    if (params?.type) queryParams.type = params.type;
    const query = new URLSearchParams(queryParams);
    return get<FilesListResponse>(`/files?${query}`);
  },
};

// ============================================
// Month-End Close Types
// ============================================

export type PeriodStatus = "open" | "in_progress" | "pending_approval" | "locked" | "closed";
export type ChecklistItemStatus = "pending" | "in_progress" | "completed" | "skipped" | "blocked";
export type EntryStatus = "draft" | "pending_approval" | "approved" | "rejected" | "posted";
export type EntryType = "accrual" | "depreciation" | "prepaid" | "deferral" | "correction" | "reclassification" | "other";
export type HealthStatus = "excellent" | "good" | "warning" | "critical";

export interface AccountingPeriod {
  id: string;
  tenant_id: string;
  period_name: string;
  period_type: "monthly" | "quarterly" | "annual";
  start_date: string;
  end_date: string;
  status: PeriodStatus;
  notes?: string;
  checklist_progress?: number;
  started_by?: string;
  started_at?: string;
  locked_by?: string;
  locked_at?: string;
  submitted_by?: string;
  submitted_at?: string;
  approved_by?: string;
  approved_at?: string;
  closed_by?: string;
  closed_at?: string;
  rejection_reason?: string;
  created_at: string;
  updated_at: string;
}

export interface PeriodListParams extends PaginationParams {
  status?: PeriodStatus;
  year?: string;
}

export interface PeriodListResponse {
  periods: AccountingPeriod[];
  total: number;
  page: number;
  per_page: number;
}

export interface CreatePeriodData {
  period_name: string;
  period_type: "monthly" | "quarterly" | "annual";
  start_date: string;
  end_date: string;
  notes?: string;
}

export interface ChecklistItem {
  id: string;
  period_id: string;
  template_id?: string;
  category: string;
  name: string;
  description?: string;
  is_required: boolean;
  sequence: number;
  status: ChecklistItemStatus;
  auto_check_type?: string;
  auto_check_threshold?: number;
  auto_check_result?: AutoCheckResult;
  completed_by?: string;
  completed_at?: string;
  skip_reason?: string;
  skipped_by?: string;
  skipped_at?: string;
  blocker_notes?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface AutoCheckResult {
  passed: boolean;
  current_value: number;
  threshold: number;
  message: string;
  details?: Record<string, unknown>;
  checked_at: string;
}

export interface UpdateChecklistItemData {
  status?: ChecklistItemStatus;
  notes?: string;
  blocker_notes?: string;
}

export interface ReconciliationStatus {
  overall_health: HealthStatus;
  health_score: number;
  invoice_stats: InvoiceReconciliationStats;
  payslip_stats: PayslipReconciliationStats;
  transaction_stats: TransactionReconciliationStats;
}

export interface InvoiceReconciliationStats {
  total: number;
  matched: number;
  unmatched: number;
  match_percentage: number;
  threshold: number;
  passed: boolean;
}

export interface PayslipReconciliationStats {
  total: number;
  matched: number;
  unmatched: number;
  match_percentage: number;
  threshold: number;
  passed: boolean;
}

export interface TransactionReconciliationStats {
  total: number;
  classified: number;
  unclassified: number;
  needs_review: number;
  classification_percentage: number;
  threshold: number;
  passed: boolean;
}

export interface UnmatchedItemsResponse {
  items: UnmatchedItem[];
  total: number;
  type: string;
}

export interface UnmatchedItem {
  id: string;
  type: "invoice" | "payslip" | "transaction";
  description: string;
  amount: number;
  currency: string;
  date: string;
  status?: string;
}

export interface AdjustingEntry {
  id: string;
  period_id: string;
  tenant_id: string;
  entry_type: EntryType;
  description: string;
  entity_id?: string;
  entity_name?: string;
  debit_account: string;
  credit_account: string;
  amount: number;
  currency: string;
  reference_number?: string;
  status: EntryStatus;
  is_reversing: boolean;
  reverse_in_next_period: boolean;
  notes?: string;
  submitted_by?: string;
  submitted_at?: string;
  approved_by?: string;
  approved_at?: string;
  rejected_by?: string;
  rejected_at?: string;
  rejection_reason?: string;
  posted_by?: string;
  posted_at?: string;
  posted_transaction_id?: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface EntryListParams extends PaginationParams {
  status?: EntryStatus;
  entry_type?: EntryType;
}

export interface EntryListResponse {
  entries: AdjustingEntry[];
  total: number;
  page: number;
  per_page: number;
}

export interface CreateEntryData {
  entry_type: EntryType;
  description: string;
  entity_id?: string;
  debit_account: string;
  credit_account: string;
  amount: number;
  currency?: string;
  reference_number?: string;
  is_reversing?: boolean;
  reverse_in_next_period?: boolean;
  notes?: string;
}

export interface EntriesSummary {
  draft: number;
  pending_approval: number;
  approved: number;
  rejected: number;
  posted: number;
  total: number;
  total_amount: number;
}

export interface ActivityLogEntry {
  id: string;
  period_id: string;
  action: string;
  entity_type: string;
  entity_id?: string;
  user_id: string;
  user_name?: string;
  details?: Record<string, unknown>;
  old_value?: Record<string, unknown>;
  new_value?: Record<string, unknown>;
  created_at: string;
}

export interface ActivityLogResponse {
  entries: ActivityLogEntry[];
  total: number;
  page: number;
  per_page: number;
}

// ==============================================================================
// SUPER ADMIN DASHBOARD TYPES
// ==============================================================================

export interface DailyActiveUsers {
  date: string;
  count: number;
}

export interface UserActivityResponse {
  daily_active_users: DailyActiveUsers[];
  weekly_active_users: number;
  monthly_active_users: number;
  total_users: number;
}

export interface SessionsByDay {
  date: string;
  count: number;
}

export interface UserSessionsResponse {
  average_duration_minutes: number;
  median_duration_minutes: number;
  total_sessions: number;
  sessions_by_day: SessionsByDay[];
}

export interface RetentionCohort {
  week: string;
  users: number;
  retention: number[];
}

export interface UserRetentionResponse {
  cohorts: RetentionCohort[];
}

export interface SuperAdminUser {
  id: string;
  email: string;
  display_name: string;
  user_type: string;
  created_at: string | null;
  last_login_at: string | null;
  sessions_7d: number;
  actions_7d: number;
  tenant_ids: string[];
}

export interface UserListResponse {
  users: SuperAdminUser[];
  total: number;
  page: number;
  per_page: number;
}

export interface SuperAdminTenant {
  id: string;
  company_name: string;
  description: string | null;
  created_at: string | null;
  user_count: number;
  last_activity: string | null;
  transactions_30d: number;
  health_score: number;
  churn_risk: 'low' | 'medium' | 'high';
}

export interface TenantListResponse {
  tenants: SuperAdminTenant[];
  total: number;
  page: number;
  per_page: number;
}

export interface TenantFeatureUsage {
  feature: string;
  count: number;
}

export interface TenantUserActivity {
  email: string;
  display_name: string;
  sessions: number;
  actions: number;
}

export interface TenantActivityResponse {
  tenant: {
    id: string;
    company_name: string;
    description: string | null;
    created_at: string | null;
  };
  daily_sessions: SessionsByDay[];
  top_features: TenantFeatureUsage[];
  user_activity: TenantUserActivity[];
}

export interface TenantGrowthByWeek {
  week: string;
  count: number;
}

export interface TenantGrowthResponse {
  new_tenants_by_week: TenantGrowthByWeek[];
  total_tenants: number;
  active_tenants_30d: number;
}

export interface ChurnRiskTenant {
  tenant_id: string;
  company_name: string;
  last_login: string | null;
  transactions_30d: number;
  actions_7d: number;
  risk_level: 'medium' | 'high';
  risk_factors: string[];
}

export interface ChurnRiskResponse {
  at_risk_tenants: ChurnRiskTenant[];
  risk_summary: {
    high_risk: number;
    medium_risk: number;
    total_at_risk: number;
  };
}

export interface FeatureUsage {
  feature: string;
  total_uses: number;
  unique_users: number;
  adoption_rate: number;
}

export interface FeatureUsageResponse {
  features: FeatureUsage[];
  total_active_users: number;
}

export interface FeatureTrendDay {
  date: string;
  feature_counts: Record<string, number>;
}

export interface FeatureTrendsResponse {
  trends: FeatureTrendDay[];
}

export interface TenantFeatureUsageItem {
  tenant_id: string;
  company_name: string;
  feature: string;
  count: number;
}

export interface FeatureByTenantResponse {
  tenant_usage: TenantFeatureUsageItem[];
}

export interface SuperAdminError {
  id: string;
  error_type: string;
  error_code: string | null;
  message: string | null;
  stack_trace: string | null;
  endpoint: string | null;
  user_id: string | null;
  user_email: string | null;
  tenant_id: string | null;
  created_at: string | null;
}

export interface ErrorListResponse {
  errors: SuperAdminError[];
  total: number;
  page: number;
  per_page: number;
}

export interface DailyErrors {
  date: string;
  count: number;
}

export interface ErrorTrendsResponse {
  daily_errors: DailyErrors[];
  total_errors: number;
  by_type?: Record<string, number>;
}

export interface RecentError {
  id: string;
  error_type: string;
  message: string;
  endpoint?: string;
  user_email?: string;
  tenant_id?: string;
  stack_trace?: string;
  timestamp: string;
}

export interface RecentErrorsResponse {
  errors: RecentError[];
  total: number;
  page: number;
  per_page: number;
}

export interface ErrorByType {
  type: string;
  count: number;
}

export interface ErrorsByTypeResponse {
  error_types: ErrorByType[];
}

export interface ResponseTimeByHour {
  hour: string;
  avg_ms: number;
  p95_ms: number;
}

export interface EndpointStats {
  endpoint: string;
  count: number;
  avg_ms: number;
  p95_ms: number;
  max_ms: number;
}

export interface APIPerformanceResponse {
  avg_response_time_ms: number;
  p95_response_time_ms: number;
  requests_per_minute: number;
  total_requests: number;
  error_rate: number;
  overall_avg_ms?: number;
  p95_ms?: number;
  response_times_by_hour?: ResponseTimeByHour[];
  by_endpoint?: EndpointStats[];
  slow_endpoints?: EndpointStats[];
}

export interface SlowEndpoint {
  endpoint: string;
  method: string;
  avg_duration_ms: number;
  max_duration_ms: number;
  request_count: number;
}

export interface SlowEndpointsResponse {
  slow_endpoints: SlowEndpoint[];
}

export interface HealthOverviewResponse {
  status: 'healthy' | 'degraded' | 'critical';
  database: {
    status: 'healthy' | 'unhealthy';
  };
  recent_errors: number;
  active_users_24h: number;
  timestamp: string;
}

export interface TableStat {
  table_name: string;
  row_count: number;
  size_bytes: number;
  index_size_bytes: number;
  error?: string;
}

export interface DatabaseHealthResponse {
  table_stats: TableStat[];
  database_size_mb: number;
  connection_info: {
    status: string;
  };
}

export interface DatabaseStatsResponse {
  table_stats: TableStat[];
  database_size_bytes: number;
  active_connections: number;
}

// Super Admin Invitation types
export interface SuperAdminInvitation {
  id: string;
  email: string;
  user_type: 'fractional_cfo' | 'tenant_admin';
  company_name: string | null;
  status: 'pending' | 'accepted' | 'expired' | 'revoked';
  expires_at: string | null;
  created_at: string | null;
  invited_by_name: string | null;
  invited_by_email: string | null;
}

export interface SuperAdminInvitationListResponse {
  invitations: SuperAdminInvitation[];
  total: number;
  page: number;
  per_page: number;
}

export interface CreateSuperAdminInvitationData {
  email: string;
  user_type: 'fractional_cfo' | 'tenant_admin';
  company_name?: string;
}

export interface CreateSuperAdminInvitationResponse {
  success: boolean;
  invitation: SuperAdminInvitation;
  message: string;
}

// Super Admin API namespace
export const superAdmin = {
  // User Engagement
  getUserActivity: (days = 30) =>
    get<{ success: boolean; data: UserActivityResponse }>(
      `/super-admin/users/activity?days=${days}`
    ),

  getUserSessions: (days = 30) =>
    get<{ success: boolean; data: UserSessionsResponse }>(
      `/super-admin/users/sessions?days=${days}`
    ),

  getUserRetention: (weeks = 8) =>
    get<{ success: boolean; data: UserRetentionResponse }>(
      `/super-admin/users/retention?weeks=${weeks}`
    ),

  getUsers: (params: { page?: number; per_page?: number; search?: string; user_type?: string } = {}) => {
    const query = new URLSearchParams();
    if (params.page) query.set('page', String(params.page));
    if (params.per_page) query.set('per_page', String(params.per_page));
    if (params.search) query.set('search', params.search);
    if (params.user_type) query.set('user_type', params.user_type);
    return get<{ success: boolean; data: UserListResponse }>(
      `/super-admin/users/list?${query.toString()}`
    );
  },

  // Tenant Analytics
  getTenants: (params: { page?: number; per_page?: number; search?: string } = {}) => {
    const query = new URLSearchParams();
    if (params.page) query.set('page', String(params.page));
    if (params.per_page) query.set('per_page', String(params.per_page));
    if (params.search) query.set('search', params.search);
    return get<{ success: boolean; data: TenantListResponse }>(
      `/super-admin/tenants?${query.toString()}`
    );
  },

  getTenantActivity: (tenantId: string, days = 30) =>
    get<{ success: boolean; data: TenantActivityResponse }>(
      `/super-admin/tenants/${tenantId}/activity?days=${days}`
    ),

  getTenantGrowth: (days = 90) =>
    get<{ success: boolean; data: TenantGrowthResponse }>(
      `/super-admin/tenants/growth?days=${days}`
    ),

  getChurnRisk: () =>
    get<{ success: boolean; data: ChurnRiskResponse }>(
      '/super-admin/tenants/churn-risk'
    ),

  // Feature Usage
  getFeatureUsage: (days = 30) =>
    get<{ success: boolean; data: FeatureUsageResponse }>(
      `/super-admin/features/usage?days=${days}`
    ),

  getFeatureTrends: (days = 30, feature?: string) => {
    const query = new URLSearchParams();
    query.set('days', String(days));
    if (feature) query.set('feature', feature);
    return get<{ success: boolean; data: FeatureTrendsResponse }>(
      `/super-admin/features/trends?${query.toString()}`
    );
  },

  getFeatureByTenant: (days = 30, feature?: string) => {
    const query = new URLSearchParams();
    query.set('days', String(days));
    if (feature) query.set('feature', feature);
    return get<{ success: boolean; data: FeatureByTenantResponse }>(
      `/super-admin/features/by-tenant?${query.toString()}`
    );
  },

  // Errors
  getErrors: (params: { page?: number; per_page?: number; error_type?: string; days?: number } = {}) => {
    const query = new URLSearchParams();
    if (params.page) query.set('page', String(params.page));
    if (params.per_page) query.set('per_page', String(params.per_page));
    if (params.error_type) query.set('error_type', params.error_type);
    if (params.days) query.set('days', String(params.days));
    return get<{ success: boolean; data: ErrorListResponse }>(
      `/super-admin/errors?${query.toString()}`
    );
  },

  getErrorTrends: (days = 7) =>
    get<{ success: boolean; data: ErrorTrendsResponse }>(
      `/super-admin/errors/trends?days=${days}`
    ),

  getErrorsByType: (days = 7) =>
    get<{ success: boolean; data: ErrorsByTypeResponse }>(
      `/super-admin/errors/by-type?days=${days}`
    ),

  getRecentErrors: (params: { page?: number; per_page?: number; error_type?: string } = {}) => {
    const query = new URLSearchParams();
    if (params.page) query.set('page', String(params.page));
    if (params.per_page) query.set('per_page', String(params.per_page));
    if (params.error_type) query.set('error_type', params.error_type);
    return get<{ success: boolean; data: RecentErrorsResponse }>(
      `/super-admin/errors/recent?${query.toString()}`
    );
  },

  // Performance
  getAPIPerformance: (days = 7) =>
    get<{ success: boolean; data: APIPerformanceResponse }>(
      `/super-admin/performance/api?days=${days}`
    ),

  getSlowEndpoints: (days = 7, thresholdMs = 500) =>
    get<{ success: boolean; data: SlowEndpointsResponse }>(
      `/super-admin/performance/slow-endpoints?days=${days}&threshold_ms=${thresholdMs}`
    ),

  // System Health
  getHealthOverview: () =>
    get<{ success: boolean; data: HealthOverviewResponse }>(
      '/super-admin/health/overview'
    ),

  getDatabaseHealth: () =>
    get<{ success: boolean; data: DatabaseHealthResponse }>(
      '/super-admin/health/database'
    ),

  getDatabaseStats: () =>
    get<{ success: boolean; data: DatabaseStatsResponse }>(
      '/super-admin/health/database-stats'
    ),

  // Invitations
  getInvitations: (params: { page?: number; per_page?: number; status?: string } = {}) => {
    const query = new URLSearchParams();
    if (params.page) query.set('page', String(params.page));
    if (params.per_page) query.set('per_page', String(params.per_page));
    if (params.status) query.set('status', params.status);
    return get<{ success: boolean; data: SuperAdminInvitationListResponse }>(
      `/super-admin/invitations?${query.toString()}`
    );
  },

  createInvitation: (data: CreateSuperAdminInvitationData) =>
    post<CreateSuperAdminInvitationResponse>('/super-admin/invitations', data),

  revokeInvitation: (invitationId: string) =>
    del<{ success: boolean; message: string }>(`/super-admin/invitations/${invitationId}`),

  resendInvitation: (invitationId: string) =>
    post<{ success: boolean; message: string }>(`/super-admin/invitations/${invitationId}/resend`),
};

// Analytics tracking (for Phase 4)
export interface AnalyticsEvent {
  event_type: 'page_view' | 'feature' | 'error';
  page_path?: string;
  page_title?: string;
  session_id?: string;
  referrer?: string;
  feature_name?: string;
  action?: string;
  metadata?: Record<string, unknown>;
  error_type?: string;
  error_message?: string;
  error_code?: string;
  stack_trace?: string;
  user_id?: string;
  tenant_id?: string;
  timestamp?: string;
}

export const analytics = {
  trackBatch: (events: AnalyticsEvent[]) =>
    post<{ success: boolean; counts: { page_views: number; features: number; errors: number } }>(
      '/analytics/track',
      { events }
    ),
};
