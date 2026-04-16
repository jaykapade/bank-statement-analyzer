export type JobStatus =
  | "pending"
  | "extracting"
  | "extracted"
  | "categorizing"
  | "completed"
  | "extract_failed"
  | "categorize_failed"
  | "failed";

export type JobListItem = {
  job_id: string;
  status: JobStatus;
  filename: string | null;
};

export type PaginationMeta = {
  page: number;
  limit: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
};

export type JobListResponse = {
  jobs: JobListItem[];
  pagination: PaginationMeta;
};

export type JobDetail = {
  job_id: string;
  status: JobStatus;
  total: number;
  done: number;
  failed: number;
  pending: number;
};

export type Transaction = {
  id: string;
  amount: number;
  category: string | null;
  category_status: "pending" | "done" | "failed";
  description: string;
  date: string;
};

export type TransactionsResponse = {
  job_id: string;
  transactions: Transaction[];
  pagination: PaginationMeta;
};

export type AnalysisSummary = {
  total_income: number;
  total_expenses: number;
  net_flow: number;
  transaction_count: number;
  uncategorized_count: number;
  date_range: {
    from: string | null;
    to: string | null;
  };
  jobs: {
    total: number;
    completed: number;
    pending: number;
    failed: number;
  };
};

export type SpendingTrendPoint = {
  period: string;
  income: number;
  expenses: number;
};

export type SpendingTrendResponse = {
  trend: SpendingTrendPoint[];
  group_by: "day" | "week" | "month";
};

export type CategoryBreakdownItem = {
  name: string;
  amount: number;
  count: number;
};

export type CategoryBreakdownResponse = {
  categories: CategoryBreakdownItem[];
  type: "expense" | "income" | "all";
};

export type JobAnalysisSummary = {
  job_id: string;
  status: JobStatus;
  filename: string | null;
  category_counts: {
    total: number;
    done: number;
    pending: number;
    failed: number;
  };
  transaction_summary: {
    count: number;
    total_income: number;
    total_expenses: number;
    net_flow: number;
  };
};

export type AuthUser = {
  id: string;
  email: string;
};

export type AuthResponse = {
  user: AuthUser;
};

type ApiErrorShape = {
  detail?: string;
};

export function getApiBaseUrl() {
  if (typeof window === "undefined") {
    return process.env.API_BASE_URL ?? "http://localhost:8000";
  }

  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    cache: "no-store",
    credentials: "include",
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;

    try {
      const errorBody = (await response.json()) as ApiErrorShape;
      if (errorBody.detail) {
        message = errorBody.detail;
      }
    } catch {}

    throw new Error(message);
  }

  return (await response.json()) as T;
}

export async function getJobs(page = 1, limit = 20) {
  return apiFetch<JobListResponse>(`/jobs?page=${page}&limit=${limit}`);
}

export async function getJob(jobId: string) {
  return apiFetch<JobDetail>(`/jobs/${jobId}`);
}

export async function getTransactions(jobId: string, page = 1, limit = 50) {
  return apiFetch<TransactionsResponse>(
    `/jobs/${jobId}/transactions?page=${page}&limit=${limit}`,
  );
}

export async function createJob(filename: string | null = null) {
  return apiFetch<JobListItem>("/jobs", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ filename }),
  });
}

export async function updateJob(
  jobId: string,
  payload: Partial<Pick<JobListItem, "filename" | "status">>,
) {
  return apiFetch<JobListItem>(`/jobs/${jobId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export async function deleteJob(jobId: string) {
  return apiFetch<{ message: string; job_id: string; deleted_transactions: number }>(
    `/jobs/${jobId}`,
    {
      method: "DELETE",
    },
  );
}

export type CreateTransactionPayload = {
  date: string;
  description: string;
  amount: number;
  category?: string | null;
  category_status?: "pending" | "done" | "failed";
};

export async function createTransaction(jobId: string, payload: CreateTransactionPayload) {
  return apiFetch<Transaction>(`/jobs/${jobId}/transactions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export type UpdateTransactionPayload = Partial<
  Pick<Transaction, "date" | "description" | "amount" | "category" | "category_status">
>;

export async function updateTransaction(
  jobId: string,
  transactionId: string,
  payload: UpdateTransactionPayload,
) {
  return apiFetch<Transaction>(`/jobs/${jobId}/transactions/${transactionId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export async function deleteTransaction(jobId: string, transactionId: string) {
  return apiFetch<{ message: string; id: string; job_id: string }>(
    `/jobs/${jobId}/transactions/${transactionId}`,
    {
      method: "DELETE",
    },
  );
}

export async function getAnalysisSummary() {
  return apiFetch<AnalysisSummary>("/analysis/summary");
}

export async function getSpendingTrend(groupBy: "day" | "week" | "month" = "day") {
  return apiFetch<SpendingTrendResponse>(
    `/analysis/spending-trend?group_by=${groupBy}`,
  );
}

export async function getCategoryBreakdown(
  type: "expense" | "income" | "all" = "expense",
  limit = 5,
) {
  return apiFetch<CategoryBreakdownResponse>(
    `/analysis/categories?type=${type}&limit=${limit}`,
  );
}

export async function getJobAnalysisSummary(jobId: string) {
  return apiFetch<JobAnalysisSummary>(`/analysis/jobs/${jobId}/summary`);
}


export async function retryCategorization(jobId: string) {
  return apiFetch<{ message: string; job_id: string }>(
    `/categorize/retry/${jobId}`,
  );
}

export async function register(email: string, password: string) {
  return apiFetch<AuthResponse>("/auth/register", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });
}

export async function login(email: string, password: string) {
  return apiFetch<AuthResponse>("/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });
}

export async function logout() {
  return apiFetch<{ message: string }>("/auth/logout", {
    method: "POST",
  });
}

export async function resetAccount() {
  return apiFetch<{ message: string }>("/admin/reset", {
    method: "POST",
  });
}
