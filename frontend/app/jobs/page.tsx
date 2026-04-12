import Link from "next/link";
import { ErrorToast } from "@/components/error-toast";
import { JobsTable } from "@/components/jobs-table";
import { PaginationNav } from "@/components/pagination-nav";
import { SectionCard } from "@/components/section-card";
import { SummaryCard } from "@/components/summary-card";
import { type JobListItem, type PaginationMeta } from "@/lib/api";
import {
  getAnalysisSummaryServer,
  getJobsServer,
  requireCurrentUser,
} from "@/lib/server-auth";
import { Button } from "@/components/ui/button";

type JobsPageProps = {
  searchParams?: Promise<{ page?: string }>;
};

function parsePage(value: string | undefined) {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1;
}

export default async function JobsPage({ searchParams }: JobsPageProps) {
  await requireCurrentUser();

  const resolvedSearchParams = searchParams ? await searchParams : undefined;
  const page = parsePage(resolvedSearchParams?.page);
  let jobs: JobListItem[] = [];
  let pagination: PaginationMeta = {
    page,
    limit: 20,
    total: 0,
    total_pages: 1,
    has_next: false,
    has_prev: false,
  };
  let jobCounts = {
    total: 0,
    completed: 0,
    pending: 0,
    failed: 0,
  };
  let error: string | null = null;

  try {
    const [response, summary] = await Promise.all([
      getJobsServer(page, 20),
      getAnalysisSummaryServer(),
    ]);
    jobs = response.jobs;
    pagination = response.pagination;
    jobCounts = summary.jobs;
  } catch (caughtError) {
    error =
      caughtError instanceof Error
        ? caughtError.message
        : "Unable to load jobs right now.";
  }

  return (
    <div className="space-y-6">
      {error ? <ErrorToast message={error} /> : null}
      <SectionCard eyebrow="" title="Job history" body="">
        <div className="grid gap-3 md:grid-cols-4">
          <SummaryCard label="Total jobs" value={jobCounts.total} />
          <SummaryCard label="Active" value={jobCounts.pending} />
          <SummaryCard label="Completed" value={jobCounts.completed} />
          <SummaryCard label="Needs attention" value={jobCounts.failed} />
        </div>
      </SectionCard>

      {error ? (
        <SectionCard title="Jobs unavailable" body="Try again or upload a new statement.">
          <Button asChild variant="secondary">
            <Link href="/upload">Go to upload</Link>
          </Button>
        </SectionCard>
      ) : (
        <>
          <JobsTable jobs={jobs} />
          <PaginationNav
            buildHref={(nextPage) => `/jobs?page=${nextPage}`}
            label="jobs"
            pagination={pagination}
          />
        </>
      )}
    </div>
  );
}
