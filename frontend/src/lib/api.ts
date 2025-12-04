/**
 * API Client for Flask Backend
 *
 * This client handles all communication with the Flask API backend.
 * In production, requests are proxied through Next.js rewrites.
 * In development, you can set FLASK_API_URL to point directly to Flask.
 */

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

  try {
    const response = await fetch(url, {
      method: "POST",
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
    post<Transaction>("/update_transaction", { id, ...data }),
  enrich: (id: string) => post<Transaction>(`/transactions/${id}/enrich`),
  bulkEnrich: (ids: string[]) =>
    post<BulkEnrichResponse>("/transactions/enrich/bulk", { ids }),
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
  category?: string;
  subcategory?: string;
  entity_id?: string;
  entity_name?: string;
  confidence_score?: number;
  matched_invoice_id?: string;
  notes?: string;
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
  uploaded_at: string;
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
