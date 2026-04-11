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

export type JobListResponse = {
  jobs: JobListItem[];
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
  amount: number;
  category: string | null;
  description: string;
  date: string;
};

export type TransactionsResponse = {
  job_id: string;
  transactions: Transaction[];
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
  return (
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    process.env.API_BASE_URL ??
    "http://localhost:8000"
  );
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

export async function getJobs() {
  return apiFetch<JobListResponse>("/jobs");
}

export async function getJob(jobId: string) {
  return apiFetch<JobDetail>(`/jobs/${jobId}`);
}

export async function getTransactions(jobId: string) {
  return apiFetch<TransactionsResponse>(`/transactions/${jobId}`);
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
