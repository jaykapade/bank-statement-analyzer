import Link from "next/link";
import { ErrorToast } from "@/components/error-toast";
import { RetryCategorizationButton } from "@/components/retry-categorization-button";
import { DeleteJobButton } from "@/components/delete-job-button";
import { JobDebugDialogs } from "@/components/job-debug-dialogs";
import { SectionCard } from "@/components/section-card";
import { StatusBadge } from "@/components/status-badge";
import { SummaryCard } from "@/components/summary-card";
import { TransactionsTable } from "@/components/transactions-table";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  getApiBaseUrl,
  type JobAnalysisSummary,
  type PaginationMeta,
  type Transaction,
} from "@/lib/api";
import {
  getJobAnalysisSummaryServer,
  getTransactionsServer,
  requireCurrentUser,
  serverApiText,
} from "@/lib/server-auth";

type JobDetailPageProps = {
  params: Promise<{ jobId: string }>;
  searchParams?: Promise<{ page?: string }>;
};

function formatAmount(value: number) {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function parsePage(value: string | undefined) {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1;
}

export default async function JobDetailPage({
  params,
  searchParams,
}: JobDetailPageProps) {
  await requireCurrentUser();

  const { jobId } = await params;
  const resolvedSearchParams = searchParams ? await searchParams : undefined;
  const page = parsePage(resolvedSearchParams?.page);
  let job: JobAnalysisSummary | null = null;
  let transactions: Transaction[] = [];
  let pagination: PaginationMeta = {
    page,
    limit: 50,
    total: 0,
    total_pages: 1,
    has_next: false,
    has_prev: false,
  };
  let markdownPreview: string | null = null;
  let error: string | null = null;

  try {
    const [jobResponse, transactionsResponse] = await Promise.all([
      getJobAnalysisSummaryServer(jobId),
      getTransactionsServer(jobId, page, 50).catch(() => ({
        job_id: jobId,
        transactions: [],
        pagination: {
          page,
          limit: 50,
          total: 0,
          total_pages: 1,
          has_next: false,
          has_prev: false,
        },
      })),
    ]);

    job = jobResponse;
    transactions = transactionsResponse.transactions;
    pagination = transactionsResponse.pagination;
  } catch (caughtError) {
    error =
      caughtError instanceof Error
        ? caughtError.message
        : "Unable to load this job.";
  }

  try {
    markdownPreview = await serverApiText(`/jobs/${jobId}/assets/markdown`);
  } catch {
  }

  const markdownLineCount = markdownPreview
    ? markdownPreview.split(/\r?\n/).length
    : 0;
  const markdownCharCount = markdownPreview?.length ?? 0;
  const canRetry =
    job?.status === "categorize_failed" && transactions.length > 0;
  const pdfPreviewUrl = `${getApiBaseUrl()}/jobs/${jobId}/assets/pdf`;
  const markdownPreviewUrl = `${getApiBaseUrl()}/jobs/${jobId}/assets/markdown`;

  return (
    <div className="space-y-5">
      {error ? <ErrorToast message={error} /> : null}
      <section className="grid gap-5 2xl:grid-cols-[1.12fr_0.88fr]">
        <SectionCard
          title="Job workspace"
          body="Processing status and extracted rows for this upload."
        >
          {error || !job ? (
            <Card className="rounded-[1.25rem] bg-white/4">
              <CardContent className="p-5 text-sm leading-6 text-[var(--color-mist)]">
                Return to the jobs list and try opening the workspace again.
              </CardContent>
            </Card>
          ) : (
            <>
              <div className="grid gap-3 xl:grid-cols-2">
                <div className="rounded-[1.25rem] border border-white/8 bg-black/15 p-4">
                  <p className="text-sm text-[var(--color-mist)]">Job ID</p>
                  <p className="mt-2 break-all font-mono text-sm leading-6 text-white">
                    {jobId}
                  </p>
                </div>
                <div className="rounded-[1.25rem] border border-white/8 bg-black/15 p-4">
                  <p className="text-sm text-[var(--color-mist)]">
                    Current status
                  </p>
                  <div className="mt-3">
                    <StatusBadge status={job.status} />
                  </div>
                </div>
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <SummaryCard label="Total rows" value={job.category_counts.total} />
                <SummaryCard label="Categorized" value={job.category_counts.done} />
                <SummaryCard label="Pending" value={job.category_counts.pending} />
                <SummaryCard label="Needs retry" value={job.category_counts.failed} />
              </div>

              <div className="mt-5 flex flex-wrap gap-3">
                <Button asChild>
                  <Link href={`/jobs/${jobId}/transactions`}>Open dedicated table</Link>
                </Button>
                {canRetry ? <RetryCategorizationButton jobId={jobId} /> : null}
                <Button asChild variant="secondary">
                  <Link href="/jobs">Back to jobs</Link>
                </Button>
                <DeleteJobButton jobId={jobId} />
              </div>
            </>
          )}
        </SectionCard>

        <SectionCard
          title="Rows extracted for this job"
          body="Transaction totals from the extracted rows."
        >
          <div className="grid gap-3 sm:grid-cols-1">
            <SummaryCard
              label="Rows extracted"
              value={job?.transaction_summary.count ?? transactions.length}
            />
            <SummaryCard
              label="Net flow"
              value={formatAmount(job?.transaction_summary.net_flow ?? 0)}
              valueClassName="text-[clamp(1.5rem,2.2vw,2rem)]"
            />
          </div>
        </SectionCard>
      </section>

      <JobDebugDialogs
        jobId={jobId}
        markdownCharCount={markdownCharCount}
        markdownLineCount={markdownLineCount}
        markdownPreview={markdownPreview}
        markdownPreviewUrl={markdownPreviewUrl}
        pdfPreviewUrl={pdfPreviewUrl}
      />

      <SectionCard
        title="Transaction table"
        body="A preview of extracted transactions for this job."
      >
        <TransactionsTable
          transactions={transactions}
          pagination={pagination}
          pageHrefPrefix={`/jobs/${jobId}?page=`}
        />
      </SectionCard>
    </div>
  );
}
