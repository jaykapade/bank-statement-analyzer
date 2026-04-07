import Link from "next/link";
import { ErrorToast } from "@/components/error-toast";
import { SectionCard } from "@/components/section-card";
import { SummaryCard } from "@/components/summary-card";
import { TransactionsTable } from "@/components/transactions-table";
import { getTransactions, type Transaction } from "@/lib/api";

type TransactionsPageProps = {
  params: Promise<{ jobId: string }>;
};

function formatAmount(value: number) {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export default async function TransactionsPage({
  params,
}: TransactionsPageProps) {
  const { jobId } = await params;
  let transactions: Transaction[] = [];
  let error: string | null = null;

  try {
    const response = await getTransactions(jobId);
    transactions = response.transactions;
  } catch (caughtError) {
    error =
      caughtError instanceof Error
        ? caughtError.message
        : "Unable to load transactions.";
  }

  const transactionTotal = transactions.reduce(
    (sum, transaction) => sum + transaction.amount,
    0,
  );
  const uncategorizedCount = transactions.filter(
    (transaction) => !transaction.category,
  ).length;

  return (
    <div className="space-y-5">
      {error ? <ErrorToast message={error} /> : null}
      <SectionCard
        title="Job-scoped transaction review"
        body="Full table view for extracted rows."
      >
        <div className="grid gap-3 lg:grid-cols-3">
          <SummaryCard label="Rows" value={transactions.length} />
          <SummaryCard
            label="Total amount"
            value={formatAmount(transactionTotal)}
            valueClassName="text-[clamp(1.5rem,2.2vw,2rem)]"
          />
          <SummaryCard label="Uncategorized" value={uncategorizedCount} />
        </div>
        <div className="mt-5">
          <Link className="button-secondary" href={`/jobs/${jobId}`}>
            Back to job summary
          </Link>
        </div>
      </SectionCard>

      {error ? (
        <SectionCard title="Transactions unavailable" body="Try returning to the job summary and opening this table again." />
      ) : (
        <TransactionsTable transactions={transactions} />
      )}
    </div>
  );
}
