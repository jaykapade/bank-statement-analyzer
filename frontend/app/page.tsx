import Link from "next/link";
import { ErrorToast } from "@/components/error-toast";
import { ReceiptText, TrendingDown, TrendingUp, Wallet } from "lucide-react";
import { BudgetChart } from "@/components/charts/budget-chart";
import { SpendingChart } from "@/components/charts/spending-chart";
import {
  type JobListItem,
  type Transaction,
} from "@/lib/api";
import {
  getJobsServer,
  getTransactionsServer,
  requireCurrentUser,
} from "@/lib/server-auth";

type TrendPoint = {
  day: string;
  income: number;
  expenses: number;
  sortKey: number;
};

function formatCurrency(value: number) {
  const formatted = new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 0,
  }).format(value);
  return formatted;
}

function parseDateValue(value: string) {
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? null : parsed;
}

function sortTransactionsNewestFirst(transactions: Transaction[]) {
  return [...transactions].sort((left, right) => {
    const leftDate = parseDateValue(left.date);
    const rightDate = parseDateValue(right.date);

    if (leftDate !== null && rightDate !== null) {
      return rightDate - leftDate;
    }

    if (leftDate !== null) {
      return -1;
    }

    if (rightDate !== null) {
      return 1;
    }

    return 0;
  });
}

function buildTrendData(transactions: Transaction[]) {
  const buckets = new Map<string, TrendPoint>();

  for (const transaction of transactions) {
    const parsed = parseDateValue(transaction.date);
    const dayLabel =
      parsed !== null
        ? new Intl.DateTimeFormat("en-US", {
            month: "short",
            day: "2-digit",
          }).format(new Date(parsed))
        : transaction.date;
    const sortKey = parsed ?? Number.MAX_SAFE_INTEGER;
    const existing = buckets.get(dayLabel) ?? {
      day: dayLabel,
      income: 0,
      expenses: 0,
      sortKey,
    };

    if (transaction.amount >= 0) {
      existing.income += transaction.amount;
    } else {
      existing.expenses += Math.abs(transaction.amount);
    }

    buckets.set(dayLabel, existing);
  }

  return [...buckets.values()]
    .sort((left, right) => left.sortKey - right.sortKey)
    .slice(-8)
    .map((point) => ({
      day: point.day,
      income: point.income,
      expenses: point.expenses,
    }));
}

function buildBudgetData(transactions: Transaction[]) {
  const outgoing = transactions.filter(
    (transaction) => transaction.category && transaction.amount < 0,
  );
  const source =
    outgoing.length > 0 ? outgoing : transactions.filter((t) => t.category);
  const totals = new Map<string, number>();
  const palette = ["#818cf8", "#34d399", "#38bdf8", "#fbbf24", "#fb7185"];

  for (const transaction of source) {
    const category = transaction.category ?? "Uncategorized";
    const nextTotal =
      (totals.get(category) ?? 0) + Math.abs(transaction.amount);
    totals.set(category, nextTotal);
  }

  return [...totals.entries()]
    .sort((left, right) => right[1] - left[1])
    .slice(0, 5)
    .map(([name, value], index) => ({
      name,
      value,
      color: palette[index % palette.length],
    }));
}

async function loadDashboardData() {
  const jobsResponse = await getJobsServer();
  const jobs = jobsResponse.jobs;
  const transactionJobs = jobs.filter((job) => job.status !== "pending");
  const transactionResponses = await Promise.allSettled(
    transactionJobs.map((job) => getTransactionsServer(job.job_id)),
  );

  const allTransactions = transactionResponses.flatMap((result) =>
    result.status === "fulfilled" ? result.value.transactions : [],
  );

  return { jobs, allTransactions };
}

function EmptyDashboard({ jobs }: { jobs: JobListItem[] }) {
  const completedJobs = jobs.filter((job) => job.status === "completed").length;
  const pendingJobs = jobs.filter((job) =>
    ["pending", "extracting", "extracted", "categorizing"].includes(job.status),
  ).length;
  const failedJobs = jobs.filter((job) =>
    ["failed", "extract_failed", "categorize_failed"].includes(job.status),
  ).length;

  return (
    <section className="dashboard-surface rounded-[2rem] p-8">
      <p className="text-[11px] uppercase tracking-[0.28em] text-[var(--color-mist-strong)]">
        No transaction data yet
      </p>
      <h1 className="mt-3 font-mono text-3xl font-semibold text-white">
        Upload a statement to start populating the dashboard.
      </h1>
      <div className="mt-6 grid gap-4 sm:grid-cols-4">
        <div className="rounded-[1.35rem] border border-white/8 bg-white/4 px-4 py-4">
          <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--color-mist)]">
            Jobs
          </p>
          <p className="mt-3 font-mono text-2xl font-semibold text-white">
            {jobs.length}
          </p>
        </div>
        <div className="rounded-[1.35rem] border border-white/8 bg-white/4 px-4 py-4">
          <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--color-mist)]">
            Completed
          </p>
          <p className="mt-3 font-mono text-2xl font-semibold text-white">
            {completedJobs}
          </p>
        </div>
        <div className="rounded-[1.35rem] border border-white/8 bg-white/4 px-4 py-4">
          <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--color-mist)]">
            Pending
          </p>
          <p className="mt-3 font-mono text-2xl font-semibold text-white">
            {pendingJobs}
          </p>
        </div>
        <div className="rounded-[1.35rem] border border-white/8 bg-white/4 px-4 py-4">
          <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--color-mist)]">
            Failed
          </p>
          <p className="mt-3 font-mono text-2xl font-semibold text-white">
            {failedJobs}
          </p>
        </div>
      </div>
      <div className="mt-8 flex flex-wrap gap-3">
        <Link className="button-secondary" href="/jobs">
          View Jobs
        </Link>
      </div>
    </section>
  );
}

export default async function Home() {
  await requireCurrentUser();

  let jobs: JobListItem[] = [];
  let transactions: Transaction[] = [];
  let error: string | null = null;

  try {
    const data = await loadDashboardData();
    jobs = data.jobs;
    transactions = sortTransactionsNewestFirst(data.allTransactions);
  } catch (caughtError) {
    error =
      caughtError instanceof Error
        ? caughtError.message
        : "Unable to load dashboard data.";
  }

  if (error) {
    return (
      <>
        <ErrorToast message={error} />
        <section className="dashboard-surface rounded-[2rem] p-8">
          <p className="text-[11px] uppercase tracking-[0.28em] text-[var(--color-mist-strong)]">
            Dashboard unavailable
          </p>
          <h1 className="mt-3 font-mono text-3xl font-semibold text-white">
            Unable to load dashboard data.
          </h1>
          <div className="mt-8">
            <Link className="button-secondary" href="/upload">
              Go to upload
            </Link>
          </div>
        </section>
      </>
    );
  }

  if (transactions.length === 0) {
    return <EmptyDashboard jobs={jobs} />;
  }

  const totalIncome = transactions
    .filter((transaction) => transaction.amount > 0)
    .reduce((sum, transaction) => sum + transaction.amount, 0);
  const totalExpenses = transactions
    .filter((transaction) => transaction.amount < 0)
    .reduce((sum, transaction) => sum + Math.abs(transaction.amount), 0);
  const netFlow = totalIncome - totalExpenses;
  const completedJobs = jobs.filter((job) => job.status === "completed").length;
  const pendingJobs = jobs.filter((job) =>
    ["pending", "extracting", "extracted", "categorizing"].includes(job.status),
  ).length;
  const failedJobs = jobs.filter((job) =>
    ["failed", "extract_failed", "categorize_failed"].includes(job.status),
  ).length;
  const uncategorizedCount = transactions.filter(
    (transaction) => !transaction.category,
  ).length;
  const trendData = buildTrendData(transactions);
  const budgetData = buildBudgetData(transactions);
  const recentTransactions = transactions.slice(0, 5);

  const metricCards = [
    {
      label: "Net flow",
      value: formatCurrency(netFlow),
      detail: `${transactions.length} transactions`,
      icon: Wallet,
      tone: "from-cyan-400/24 via-cyan-300/10 to-transparent text-cyan-100 ring-cyan-400/20",
    },
    {
      label: "Money out",
      value: formatCurrency(totalExpenses),
      detail: `${uncategorizedCount} uncategorized`,
      icon: TrendingDown,
      tone: "from-rose-400/24 via-rose-300/10 to-transparent text-rose-100 ring-rose-400/20",
    },
    {
      label: "Money in",
      value: formatCurrency(totalIncome),
      detail: `${completedJobs} completed jobs`,
      icon: TrendingUp,
      tone: "from-emerald-400/24 via-emerald-300/10 to-transparent text-emerald-100 ring-emerald-400/20",
    },
  ];

  const quickStats = [
    { label: "Jobs", value: String(jobs.length) },
    { label: "Completed", value: String(completedJobs) },
    { label: "Pending", value: String(pendingJobs) },
    { label: "Failed", value: String(failedJobs) },
  ];

  return (
    <div className="space-y-6">
      <section className="dashboard-surface rounded-[2rem] p-4">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {quickStats.map((item) => (
            <div
              key={item.label}
              className="rounded-[1.35rem] border border-white/8 bg-white/4 px-4 py-4"
            >
              <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--color-mist)]">
                {item.label}
              </p>
              <p className="mt-3 font-mono text-2xl font-semibold text-white">
                {item.value}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        {metricCards.map((card) => {
          const Icon = card.icon;

          return (
            <article
              key={card.label}
              className={`metric-card relative overflow-hidden bg-gradient-to-br ${card.tone}`}
            >
              <div className="flex w-full items-start justify-between gap-4">
                <div>
                  <span>{card.label}</span>
                  <strong className="mt-4 block">{card.value}</strong>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/6 p-3 text-white">
                  <Icon className="h-5 w-5" />
                </div>
              </div>
            </article>
          );
        })}
      </section>

      <section className="grid gap-6 2xl:grid-cols-[2fr_1fr]">
        <article className="dashboard-surface flex min-h-[640px] flex-col rounded-[2rem] p-6">
          <div className="flex flex-col gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-[var(--color-mist-strong)]">
                Trend
              </p>
              <h2 className="mt-2 font-mono text-2xl font-semibold text-white">
                Income vs. expenses
              </h2>
            </div>
          </div>
          <div className="mt-6 flex-1">
            <SpendingChart data={trendData} />
          </div>
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            <div className="flex items-center justify-between rounded-[1.1rem] border border-white/8 bg-white/3 px-4 py-3">
              <div className="flex items-center gap-3">
                <span className="h-3 w-3 rounded-full bg-emerald-400 shadow-[0_0_18px_rgba(52,211,153,0.4)]" />
                <span className="text-sm text-white">Income</span>
              </div>
              <span className="font-mono text-sm text-emerald-300">
                {formatCurrency(totalIncome)}
              </span>
            </div>
            <div className="flex items-center justify-between rounded-[1.1rem] border border-white/8 bg-white/3 px-4 py-3">
              <div className="flex items-center gap-3">
                <span className="h-3 w-3 rounded-full bg-rose-400 shadow-[0_0_18px_rgba(251,113,133,0.35)]" />
                <span className="text-sm text-white">Expenses</span>
              </div>
              <span className="font-mono text-sm text-rose-300">
                {formatCurrency(totalExpenses)}
              </span>
            </div>
          </div>
        </article>

        <article className="dashboard-surface rounded-[2rem] p-6">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-[var(--color-mist-strong)]">
                Allocation
              </p>
              <h2 className="mt-2 font-mono text-2xl font-semibold text-white">
                Categories
              </h2>
            </div>
          </div>
          {budgetData.length > 0 ? (
            <>
              <BudgetChart data={budgetData} />
              <div className="grid gap-3">
                {budgetData.map((item) => (
                  <div
                    key={item.name}
                    className="flex items-center justify-between rounded-[1.1rem] border border-white/8 bg-white/3 px-4 py-3"
                  >
                    <div className="flex items-center gap-3">
                      <span
                        className="h-3 w-3 rounded-full"
                        style={{ backgroundColor: item.color }}
                      />
                      <span className="text-sm text-white">{item.name}</span>
                    </div>
                    <span className="text-sm text-[var(--color-mist)]">
                      {formatCurrency(item.value)}
                    </span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="mt-6 rounded-[1.25rem] border border-white/8 bg-white/4 px-4 py-6 text-sm text-[var(--color-mist)]">
              Categories will appear after extraction returns categorized
              transactions.
            </div>
          )}
        </article>
      </section>

      <section>
        <article className="dashboard-surface rounded-[2rem] p-6">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-[var(--color-mist-strong)]">
                Transactions
              </p>
              <h2 className="mt-2 font-mono text-2xl font-semibold text-white">
                Recent activity
              </h2>
            </div>
            <ReceiptText className="h-5 w-5 text-[var(--color-mist)]" />
          </div>
          <div className="mt-6 space-y-3">
            {recentTransactions.map((item) => (
              <div
                key={`${item.description}-${item.date}-${item.amount}`}
                className="flex items-center justify-between gap-4 rounded-[1.25rem] border border-white/8 bg-white/4 px-4 py-4"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium text-white">
                    {item.description}
                  </p>
                  <p className="mt-1 text-sm text-[var(--color-mist)]">
                    {item.category ?? "Uncategorized"} | {item.date}
                  </p>
                </div>
                <span
                  className={`shrink-0 rounded-full px-3 py-1 font-mono text-sm font-semibold ring-1 ${
                    item.amount >= 0
                      ? "bg-emerald-400/14 text-emerald-300 ring-emerald-400/20"
                      : "bg-red-400/14 text-red-300 ring-red-400/20"
                  }`}
                >
                  {formatCurrency(item.amount)}
                </span>
              </div>
            ))}
          </div>
        </article>
      </section>
    </div>
  );
}
