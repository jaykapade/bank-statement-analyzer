import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import {
  type AnalysisSummary,
  getApiBaseUrl,
  type AuthResponse,
  type CategoryBreakdownResponse,
  type JobDetail,
  type JobAnalysisSummary,
  type JobListResponse,
  type SpendingTrendResponse,
  type TransactionsResponse,
} from "@/lib/api";

export async function serverApiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const headers = new Headers(init?.headers);
  const cookieStore = await cookies();
  const cookieHeader = cookieStore.toString();

  if (cookieHeader) {
    headers.set("Cookie", cookieHeader);
  }

  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    cache: "no-store",
    headers,
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;

    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        message = payload.detail;
      }
    } catch {}

    const error = new Error(message) as Error & { status?: number };
    error.status = response.status;
    throw error;
  }

  return (await response.json()) as T;
}

export async function serverApiText(
  path: string,
  init?: RequestInit,
): Promise<string> {
  const headers = new Headers(init?.headers);
  const cookieStore = await cookies();
  const cookieHeader = cookieStore.toString();

  if (cookieHeader) {
    headers.set("Cookie", cookieHeader);
  }

  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    cache: "no-store",
    headers,
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;

    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        message = payload.detail;
      }
    } catch {}

    const error = new Error(message) as Error & { status?: number };
    error.status = response.status;
    throw error;
  }

  return response.text();
}

export async function getCurrentUserServer() {
  try {
    const response = await serverApiFetch<AuthResponse>("/auth/me");
    return response.user;
  } catch (error) {
    const status =
      error instanceof Error && "status" in error
        ? Number(error.status)
        : undefined;

    if (status === 401) {
      return null;
    }

    throw error;
  }
}

export async function requireCurrentUser() {
  const user = await getCurrentUserServer();

  if (!user) {
    redirect("/login");
  }

  return user;
}

export async function redirectIfAuthenticated() {
  const user = await getCurrentUserServer();

  if (user) {
    redirect("/");
  }
}

export async function getJobsServer(page = 1, limit = 20) {
  return serverApiFetch<JobListResponse>(`/jobs?page=${page}&limit=${limit}`);
}

export async function getJobServer(jobId: string) {
  return serverApiFetch<JobDetail>(`/jobs/${jobId}`);
}

export async function getTransactionsServer(jobId: string, page = 1, limit = 50) {
  return serverApiFetch<TransactionsResponse>(
    `/transactions/${jobId}?page=${page}&limit=${limit}`,
  );
}

export async function getAnalysisSummaryServer() {
  return serverApiFetch<AnalysisSummary>("/analysis/summary");
}

export async function getSpendingTrendServer(
  groupBy: "day" | "week" | "month" = "day",
) {
  return serverApiFetch<SpendingTrendResponse>(
    `/analysis/spending-trend?group_by=${groupBy}`,
  );
}

export async function getCategoryBreakdownServer(
  type: "expense" | "income" | "all" = "expense",
  limit = 5,
) {
  return serverApiFetch<CategoryBreakdownResponse>(
    `/analysis/categories?type=${type}&limit=${limit}`,
  );
}

export async function getJobAnalysisSummaryServer(jobId: string) {
  return serverApiFetch<JobAnalysisSummary>(`/analysis/jobs/${jobId}/summary`);
}
