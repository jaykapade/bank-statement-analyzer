import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import {
  getApiBaseUrl,
  type AuthResponse,
  type JobDetail,
  type JobListResponse,
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

export async function getJobsServer() {
  return serverApiFetch<JobListResponse>("/jobs");
}

export async function getJobServer(jobId: string) {
  return serverApiFetch<JobDetail>(`/jobs/${jobId}`);
}

export async function getTransactionsServer(jobId: string) {
  return serverApiFetch<TransactionsResponse>(`/transactions/${jobId}`);
}
