import Link from "next/link";
import { ErrorToast } from "@/components/error-toast";
import { RetryCategorizationButton } from "@/components/retry-categorization-button";
import { JobDebugDialogs } from "@/components/job-debug-dialogs";
import { SectionCard } from "@/components/section-card";
import { StatusBadge } from "@/components/status-badge";
import { SummaryCard } from "@/components/summary-card";
import { TransactionsTable } from "@/components/transactions-table";
import {
  getApiBaseUrl,
  type JobDetail,
  type Transaction,
} from "@/lib/api";
import {
  getJobServer,
  serverApiText,
  getTransactionsServer,
  requireCurrentUser,
} from "@/lib/server-auth";

type JobDetailPageProps = {
  params: Promise<{ jobId: string }>;
};

function formatAmount(value: number) {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export default async function JobDetailPage({ params }: JobDetailPageProps) {
  await requireCurrentUser();

  const { jobId } = await params;
  let job: JobDetail | null = null;
  let transactions: Transaction[] = [];
  let markdownPreview: string | null = null;
  let error: string | null = null;

  try {
    const [jobResponse, transactionsResponse] = await Promise.all([
      getJobServer(jobId),
      getTransactionsServer(jobId).catch(() => ({
        job_id: jobId,
        transactions: [],
      })),
    ]);

    job = jobResponse;
    transactions = transactionsResponse.transactions;
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

  const transactionTotal = transactions.reduce(
    (sum, transaction) => sum + transaction.amount,
    0,
  );
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
            <div className="rounded-[1.25rem] border border-white/8 bg-white/4 p-5 text-sm leading-6 text-[var(--color-mist)]">
              Return to the jobs list and try opening the workspace again.
            </div>
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
                <SummaryCard label="Total rows" value={job.total} />
                <SummaryCard label="Categorized" value={job.done} />
                <SummaryCard label="Pending" value={job.pending} />
                <SummaryCard label="Needs retry" value={job.failed} />
              </div>

              <div className="mt-5 flex flex-wrap gap-3">
                <Link
                  className="button-primary"
                  href={`/jobs/${jobId}/transactions`}
                >
                  Open dedicated table
                </Link>
                {canRetry ? <RetryCategorizationButton jobId={jobId} /> : null}
                <Link className="button-secondary" href="/jobs">
                  Back to jobs
                </Link>
              </div>
            </>
          )}
        </SectionCard>

        <SectionCard
          title="Rows extracted for this job"
          body="Transaction totals from the extracted rows."
        >
          <div className="grid gap-3 sm:grid-cols-1">
            <SummaryCard label="Visible rows" value={transactions.length} />
            <SummaryCard
              label="Amount total"
              value={formatAmount(transactionTotal)}
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
        body="All extracted transactions for this job."
      >
        <TransactionsTable transactions={transactions} />
      </SectionCard>
    </div>
  );
}
