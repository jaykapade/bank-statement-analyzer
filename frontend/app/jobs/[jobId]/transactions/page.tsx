import Link from "next/link";
import { ErrorToast } from "@/components/error-toast";
import { SectionCard } from "@/components/section-card";
import { SummaryCard } from "@/components/summary-card";
import { TransactionsTable } from "@/components/transactions-table";
import { Button } from "@/components/ui/button";
import { type PaginationMeta, type Transaction } from "@/lib/api";
import {
  getJobAnalysisSummaryServer,
  getTransactionsServer,
  requireCurrentUser,
} from "@/lib/server-auth";

type TransactionsPageProps = {
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

export default async function TransactionsPage({
  params,
  searchParams,
}: TransactionsPageProps) {
  await requireCurrentUser();

  const { jobId } = await params;
  const resolvedSearchParams = searchParams ? await searchParams : undefined;
  const page = parsePage(resolvedSearchParams?.page);
  let transactions: Transaction[] = [];
  let pagination: PaginationMeta = {
    page,
    limit: 50,
    total: 0,
    total_pages: 1,
    has_next: false,
    has_prev: false,
  };
  let transactionCount = 0;
  let totalAmount = 0;
  let uncategorizedCount = 0;
  let error: string | null = null;

  try {
    const [transactionsResponse, analysisSummary] = await Promise.all([
      getTransactionsServer(jobId, page, 50),
      getJobAnalysisSummaryServer(jobId),
    ]);
    transactions = transactionsResponse.transactions;
    pagination = transactionsResponse.pagination;
    transactionCount = analysisSummary.transaction_summary.count;
    totalAmount = analysisSummary.transaction_summary.net_flow;
    uncategorizedCount =
      analysisSummary.category_counts.total - analysisSummary.category_counts.done;
  } catch (caughtError) {
    error =
      caughtError instanceof Error
        ? caughtError.message
        : "Unable to load transactions.";
  }

  return (
    <div className="space-y-5">
      {error ? <ErrorToast message={error} /> : null}
      <SectionCard
        title="Job-scoped transaction review"
        body="Full table view for extracted rows."
      >
        <div className="grid gap-3 lg:grid-cols-3">
          <SummaryCard label="Rows" value={transactionCount} />
          <SummaryCard
            label="Net flow"
            value={formatAmount(totalAmount)}
            valueClassName="text-[clamp(1.5rem,2.2vw,2rem)]"
          />
          <SummaryCard label="Needs category" value={uncategorizedCount} />
        </div>
        <div className="mt-5">
          <Button asChild variant="secondary">
            <Link href={`/jobs/${jobId}`}>Back to job summary</Link>
          </Button>
        </div>
      </SectionCard>

      {error ? (
        <SectionCard title="Transactions unavailable" body="Try returning to the job summary and opening this table again." />
      ) : (
        <>
          <TransactionsTable
            transactions={transactions}
            buildHref={(nextPage) => `/jobs/${jobId}/transactions?page=${nextPage}`}
            pagination={pagination}
          />
        </>
      )}
    </div>
  );
}
