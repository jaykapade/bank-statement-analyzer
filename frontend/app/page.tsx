import Link from "next/link";
import { ReceiptText, TrendingDown, TrendingUp, Wallet } from "lucide-react";
import { BudgetChart } from "@/components/charts/budget-chart";
import { SpendingChart } from "@/components/charts/spending-chart";
import { ErrorToast } from "@/components/error-toast";
import {
  getAnalysisSummaryServer,
  getCategoryBreakdownServer,
  getSpendingTrendServer,
  requireCurrentUser,
} from "@/lib/server-auth";

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 0,
  }).format(value);
}

function EmptyDashboard({
  jobs,
  transactionCount,
}: {
  jobs: {
    total: number;
    completed: number;
    pending: number;
    failed: number;
  };
  transactionCount: number;
}) {
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
            {jobs.total}
          </p>
        </div>
        <div className="rounded-[1.35rem] border border-white/8 bg-white/4 px-4 py-4">
          <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--color-mist)]">
            Completed
          </p>
          <p className="mt-3 font-mono text-2xl font-semibold text-white">
            {jobs.completed}
          </p>
        </div>
        <div className="rounded-[1.35rem] border border-white/8 bg-white/4 px-4 py-4">
          <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--color-mist)]">
            Pending
          </p>
          <p className="mt-3 font-mono text-2xl font-semibold text-white">
            {jobs.pending}
          </p>
        </div>
        <div className="rounded-[1.35rem] border border-white/8 bg-white/4 px-4 py-4">
          <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--color-mist)]">
            Transactions
          </p>
          <p className="mt-3 font-mono text-2xl font-semibold text-white">
            {transactionCount}
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

  let error: string | null = null;
  let summary:
    | Awaited<ReturnType<typeof getAnalysisSummaryServer>>
    | null = null;
  let trend:
    | Awaited<ReturnType<typeof getSpendingTrendServer>>
    | null = null;
  let categories:
    | Awaited<ReturnType<typeof getCategoryBreakdownServer>>
    | null = null;

  try {
    [summary, trend, categories] = await Promise.all([
      getAnalysisSummaryServer(),
      getSpendingTrendServer("day"),
      getCategoryBreakdownServer("expense", 5),
    ]);
  } catch (caughtError) {
    error =
      caughtError instanceof Error
        ? caughtError.message
        : "Unable to load dashboard data.";
  }

  if (error || !summary || !trend || !categories) {
    return (
      <>
        {error ? <ErrorToast message={error} /> : null}
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

  if (summary.transaction_count === 0) {
    return (
      <EmptyDashboard
        jobs={summary.jobs}
        transactionCount={summary.transaction_count}
      />
    );
  }

  const metricCards = [
    {
      label: "Net flow",
      value: formatCurrency(summary.net_flow),
      detail: `${summary.transaction_count} transactions`,
      icon: Wallet,
      tone: "from-cyan-400/24 via-cyan-300/10 to-transparent text-cyan-100 ring-cyan-400/20",
    },
    {
      label: "Money out",
      value: formatCurrency(summary.total_expenses),
      detail: `${summary.uncategorized_count} uncategorized`,
      icon: TrendingDown,
      tone: "from-rose-400/24 via-rose-300/10 to-transparent text-rose-100 ring-rose-400/20",
    },
    {
      label: "Money in",
      value: formatCurrency(summary.total_income),
      detail: `${summary.jobs.completed} completed jobs`,
      icon: TrendingUp,
      tone: "from-emerald-400/24 via-emerald-300/10 to-transparent text-emerald-100 ring-emerald-400/20",
    },
  ];

  const quickStats = [
    { label: "Jobs", value: String(summary.jobs.total) },
    { label: "Completed", value: String(summary.jobs.completed) },
    { label: "Pending", value: String(summary.jobs.pending) },
    { label: "Failed", value: String(summary.jobs.failed) },
  ];

  const trendData = trend.trend.map((point) => ({
    day: point.period,
    income: point.income,
    expenses: point.expenses,
  }));

  const palette = ["#818cf8", "#34d399", "#38bdf8", "#fbbf24", "#fb7185"];
  const budgetData = categories.categories.map((item, index) => ({
    name: item.name,
    value: item.amount,
    color: palette[index % palette.length],
  }));

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
                  <p className="mt-3 text-sm text-[var(--color-mist)]">
                    {card.detail}
                  </p>
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
                {formatCurrency(summary.total_income)}
              </span>
            </div>
            <div className="flex items-center justify-between rounded-[1.1rem] border border-white/8 bg-white/3 px-4 py-3">
              <div className="flex items-center gap-3">
                <span className="h-3 w-3 rounded-full bg-rose-400 shadow-[0_0_18px_rgba(251,113,133,0.35)]" />
                <span className="text-sm text-white">Expenses</span>
              </div>
              <span className="font-mono text-sm text-rose-300">
                {formatCurrency(summary.total_expenses)}
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
                {categories.categories.map((item, index) => (
                  <div
                    key={item.name}
                    className="flex items-center justify-between rounded-[1.1rem] border border-white/8 bg-white/3 px-4 py-3"
                  >
                    <div className="flex items-center gap-3">
                      <span
                        className="h-3 w-3 rounded-full"
                        style={{ backgroundColor: palette[index % palette.length] }}
                      />
                      <span className="text-sm text-white">{item.name}</span>
                    </div>
                    <span className="text-sm text-[var(--color-mist)]">
                      {formatCurrency(item.amount)}
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
                Analysis
              </p>
              <h2 className="mt-2 font-mono text-2xl font-semibold text-white">
                Snapshot
              </h2>
            </div>
            <ReceiptText className="h-5 w-5 text-[var(--color-mist)]" />
          </div>
          <div className="mt-6 grid gap-3 md:grid-cols-3">
            <div className="rounded-[1.25rem] border border-white/8 bg-white/4 px-4 py-4">
              <p className="text-sm text-[var(--color-mist)]">Top categories</p>
              <p className="mt-2 font-mono text-2xl text-white">
                {categories.categories.length}
              </p>
            </div>
            <div className="rounded-[1.25rem] border border-white/8 bg-white/4 px-4 py-4">
              <p className="text-sm text-[var(--color-mist)]">Trend buckets</p>
              <p className="mt-2 font-mono text-2xl text-white">
                {trend.trend.length}
              </p>
            </div>
            <div className="rounded-[1.25rem] border border-white/8 bg-white/4 px-4 py-4">
              <p className="text-sm text-[var(--color-mist)]">Needs category</p>
              <p className="mt-2 font-mono text-2xl text-white">
                {summary.uncategorized_count}
              </p>
            </div>
          </div>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link className="button-secondary" href="/jobs">
              Browse jobs
            </Link>
            <Link className="button-secondary" href="/upload">
              Upload another statement
            </Link>
          </div>
        </article>
      </section>
    </div>
  );
}
