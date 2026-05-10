"use client";

import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";
import {
  deleteAnomalyTransaction,
  dismissAnomaly,
  getLatestInsightsRun,
  startInsightsRun,
  type InsightAnomaly,
  type InsightRunEnvelope,
} from "@/lib/api";
import { Button } from "@/components/ui/button";

type SeverityFilter = "all" | "high" | "medium" | "low";

const FORECAST_COLORS = [
  "#8a7cf2",
  "#d0703d",
  "#58a686",
  "#9ea09b",
  "#5f88d8",
  "#b58a2e",
];

function toInr(value: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(Math.abs(value));
}

function getSeverity(anomaly: InsightAnomaly): Exclude<SeverityFilter, "all"> {
  const amount = Math.abs(anomaly.amount);
  if (amount >= 5000) return "high";
  if (amount >= 2000) return "medium";
  return "low";
}

function severityAccent(severity: Exclude<SeverityFilter, "all">) {
  if (severity === "high") return "#d0703d";
  if (severity === "medium") return "#e2bd73";
  return "#b3d58b";
}

export function InsightsPanel({ initial }: { initial: InsightRunEnvelope }) {
  const [data, setData] = useState<InsightRunEnvelope>(initial);
  const [busy, setBusy] = useState(false);
  const [actionBusyId, setActionBusyId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("all");
  const [activeTab, setActiveTab] = useState<"insights" | "anomalies">(
    "insights",
  );

  const status = data.run?.status;
  const result = data.run?.result;

  async function refresh() {
    setData(await getLatestInsightsRun());
  }

  async function startRun() {
    setBusy(true);
    try {
      await startInsightsRun();
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (status !== "pending" && status !== "running") return;
    const timer = setInterval(() => {
      refresh().catch(() => undefined);
    }, 10000);
    return () => clearInterval(timer);
  }, [status]);

  const anomalies = useMemo(() => result?.anomalies ?? [], [result]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return anomalies.filter((a) => {
      const sev = getSeverity(a);
      if (severityFilter !== "all" && sev !== severityFilter) return false;
      if (!q) return true;
      return (
        a.description.toLowerCase().includes(q) ||
        (a.category ?? "").toLowerCase().includes(q) ||
        a.flag_reason.toLowerCase().includes(q)
      );
    });
  }, [anomalies, query, severityFilter]);

  const groupedAnomalies = useMemo(
    () => ({
      high: filtered.filter((a) => getSeverity(a) === "high"),
      medium: filtered.filter((a) => getSeverity(a) === "medium"),
      low: filtered.filter((a) => getSeverity(a) === "low"),
    }),
    [filtered],
  );

  const counts = useMemo(() => {
    const high = anomalies.filter((a) => getSeverity(a) === "high").length;
    const medium = anomalies.filter((a) => getSeverity(a) === "medium").length;
    const low = anomalies.filter((a) => getSeverity(a) === "low").length;
    return { all: anomalies.length, high, medium, low };
  }, [anomalies]);

  const suggestionRows = useMemo(
    () =>
      (result?.budget_suggestions ?? [])
        .slice(0, 6)
        .map((item) => {
          const current = Math.max(0, item.current_monthly_average);
          const suggested = Math.max(0, item.suggested_budget);
          const save = Math.max(0, current - suggested);
          return { ...item, current, suggested, save };
        })
        .sort((a, b) => b.current - a.current),
    [result?.budget_suggestions],
  );

  const maxForecast = useMemo(
    () =>
      suggestionRows.length === 0
        ? 1
        : Math.max(
            ...suggestionRows.map((s) => Math.max(s.current, s.suggested)),
            1,
          ),
    [suggestionRows],
  );

  const totalPotentialSavings = useMemo(
    () => suggestionRows.reduce((acc, s) => acc + s.save, 0),
    [suggestionRows],
  );

  const totalFlaggedSpend = useMemo(
    () => anomalies.reduce((acc, a) => acc + Math.abs(a.amount), 0),
    [anomalies],
  );

  async function handleDismiss(transactionId: string) {
    setActionBusyId(transactionId);
    try {
      await dismissAnomaly(transactionId);
      await refresh();
    } finally {
      setActionBusyId(null);
    }
  }

  async function handleDelete(transactionId: string) {
    setActionBusyId(transactionId);
    try {
      await deleteAnomalyTransaction(transactionId);
      await refresh();
    } finally {
      setActionBusyId(null);
    }
  }

  function handleDownloadPdf() {
    if (!result) return;
    const rows = suggestionRows
      .map(
        (s) =>
          `<tr><td>${s.category}</td><td>${toInr(s.current)}</td><td>${toInr(s.suggested)}</td><td>${toInr(s.save)}</td></tr>`,
      )
      .join("");
    const anomalyRows = anomalies
      .map(
        (a) =>
          `<tr><td>${getSeverity(a)}</td><td>${a.description}</td><td>${a.date}</td><td>${a.category ?? "Uncategorized"}</td><td>${toInr(a.amount)}</td></tr>`,
      )
      .join("");

    const html = `
      <html>
        <head>
          <title>Insights Report</title>
          <style>
            body{font-family:Segoe UI,Arial,sans-serif;padding:24px;color:#111}
            h1,h2{margin:0 0 12px 0}
            .meta{margin:0 0 20px 0;color:#555}
            .kpi{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-bottom:20px}
            .card{border:1px solid #ddd;border-radius:10px;padding:12px}
            table{width:100%;border-collapse:collapse;margin-top:8px}
            th,td{border:1px solid #ddd;padding:8px;text-align:left;font-size:12px}
            th{background:#f4f4f4}
          </style>
        </head>
        <body>
          <h1>Insights Report</h1>
          <p class="meta">Generated at: ${new Date(result.generated_at).toLocaleString()}</p>
          <div class="kpi">
            <div class="card"><strong>Est. next month</strong><br/>${toInr(result.forecast.next_month_expense_forecast)}</div>
            <div class="card"><strong>Potential savings</strong><br/>${toInr(totalPotentialSavings)}</div>
            <div class="card"><strong>Anomalies flagged</strong><br/>${counts.all}</div>
          </div>
          <h2>Smart Budget Suggestions</h2>
          <table>
            <thead><tr><th>Category</th><th>Current Avg</th><th>Suggested Budget</th><th>Potential Save</th></tr></thead>
            <tbody>${rows}</tbody>
          </table>
          <h2 style="margin-top:20px;">Anomalies</h2>
          <table>
            <thead><tr><th>Severity</th><th>Description</th><th>Date</th><th>Category</th><th>Amount</th></tr></thead>
            <tbody>${anomalyRows}</tbody>
          </table>
        </body>
      </html>`;

    const printWindow = window.open("", "_blank");
    if (!printWindow) return;
    printWindow.document.open();
    printWindow.document.write(html);
    printWindow.document.close();
    printWindow.focus();
    printWindow.print();
  }

  const renderAnomalySection = (title: string, rows: InsightAnomaly[]) => {
    if (rows.length === 0) return null;
    return (
      <div className="space-y-2">
        <h4 className="text-xl font-semibold text-[#dfd9c7]">{title}</h4>
        {rows.map((a) => {
          const sev = getSeverity(a);
          return (
            <div
              key={a.transaction_id}
              className="flex items-start justify-between gap-4 border-t border-white/10 py-4"
            >
              <div className="flex items-start gap-3">
                <div className="mt-0.5 h-11 w-11 rounded-xl bg-[#e9e4d8] text-[#6b5f48] grid place-items-center text-sm font-semibold">
                  {sev === "high" ? "!" : sev === "medium" ? "~" : "i"}
                </div>
                <div>
                  <p className="text-3xl font-semibold text-white leading-none">
                    {a.description}
                  </p>
                  <p className="mt-1 text-sm text-[#d7d1bf]">{a.flag_reason}</p>
                  <p className="mt-1 text-xs text-[var(--color-mist)]">
                    <span
                      className="mr-2 rounded-full border px-2 py-0.5 font-semibold capitalize"
                      style={{
                        borderColor: `${severityAccent(sev)}66`,
                        backgroundColor: `${severityAccent(sev)}22`,
                        color: severityAccent(sev),
                      }}
                    >
                      {sev}
                    </span>
                    {a.date} - {a.category ?? "Uncategorized"}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-3xl font-semibold text-white">
                  {toInr(a.amount)}
                </p>
                <div className="mt-3 flex justify-end gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={actionBusyId === a.transaction_id}
                    onClick={() => handleDismiss(a.transaction_id)}
                  >
                    Dismiss
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    disabled={actionBusyId === a.transaction_id}
                    onClick={() => handleDelete(a.transaction_id)}
                  >
                    Delete
                  </Button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  const extraSpendLabel = useMemo(
    () => toInr(totalFlaggedSpend),
    [totalFlaggedSpend],
  );

  const filterChipClass = (key: SeverityFilter) =>
    key === "all"
      ? "border-[#445267] text-white"
      : key === "high"
        ? "border-[#d0703d] text-[#ffd2ba] bg-[#d0703d22]"
        : key === "medium"
          ? "border-[#e2bd73] text-[#ffe9bb] bg-[#e2bd7320]"
          : "border-[#b3d58b] text-[#e3f6cf] bg-[#b3d58b22]";

  const renderAnomalyPanel = () => (
    <>
      <div className="flex items-center justify-between">
        <h3 className="text-2xl font-semibold text-white">Anomaly detection</h3>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-xl border border-white/15 bg-white/[0.04] p-4">
          <p className="text-sm text-[#d8d2c2]">Total flagged</p>
          <p className="text-4xl font-semibold text-[#d0703d]">{counts.all}</p>
          <p className="text-sm text-[var(--color-mist)]">this month</p>
        </div>
        <div className="rounded-xl border border-white/15 bg-white/[0.04] p-4">
          <p className="text-sm text-[#d8d2c2]">High severity</p>
          <p className="text-4xl font-semibold text-[#d0703d]">{counts.high}</p>
          <p className="text-sm text-[var(--color-mist)]">needs review</p>
        </div>
        <div className="rounded-xl border border-white/15 bg-white/[0.04] p-4">
          <p className="text-sm text-[#d8d2c2]">Extra spend</p>
          <p className="text-4xl font-semibold text-white">{extraSpendLabel}</p>
          <p className="text-sm text-[var(--color-mist)]">vs your baseline</p>
        </div>
      </div>

      <div className="rounded-xl border border-white/15 bg-white/[0.04] p-4">
        <div className="mb-3 flex items-center gap-2 rounded-lg border border-white/10 bg-black/20 px-3 py-2">
          <Search className="h-4 w-4 text-[var(--color-mist)]" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search transactions..."
            className="w-full bg-transparent text-sm text-white placeholder:text-[var(--color-mist)] focus:outline-none"
          />
        </div>

        <div className="mb-4 flex flex-wrap gap-2">
          {(
            [
              ["all", `All (${counts.all})`],
              ["high", `High (${counts.high})`],
              ["medium", `Medium (${counts.medium})`],
              ["low", `Low (${counts.low})`],
            ] as [SeverityFilter, string][]
          ).map(([value, label]) => (
            <button
              key={value}
              type="button"
              onClick={() => setSeverityFilter(value)}
              className={`rounded-full border px-3 py-1 text-sm ${
                severityFilter === value
                  ? filterChipClass(value)
                  : "border-white/20 text-[var(--color-mist)]"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="space-y-6">
          {filtered.length === 0 ? (
            <p className="text-sm text-[var(--color-mist)]">
              No anomalies found.
            </p>
          ) : (
            <>
              {renderAnomalySection("High severity", groupedAnomalies.high)}
              {renderAnomalySection("Medium severity", groupedAnomalies.medium)}
              {renderAnomalySection("Low severity", groupedAnomalies.low)}
            </>
          )}
        </div>
      </div>
    </>
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <Button
          onClick={startRun}
          disabled={busy || status === "pending" || status === "running"}
        >
          {status === "pending" || status === "running"
            ? "Running..."
            : "Run AI Insights"}
        </Button>
        <Button variant="secondary" onClick={refresh}>
          Refresh
        </Button>
        <span className="text-xs text-[var(--color-mist)]">
          Status: {status ?? "not started"}
        </span>
      </div>

      {data.run?.error ? (
        <p className="text-sm text-red-300">{data.run.error}</p>
      ) : null}

      {result ? (
        <div className="space-y-4 rounded-2xl border border-white/10 bg-[#0d0d0e] p-4 md:p-6">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-2xl font-semibold text-white">Insights</h2>
            <Button
              variant="outline"
              className="rounded-lg"
              onClick={handleDownloadPdf}
            >
              Download PDF report
            </Button>
          </div>
          <div className="flex gap-2 rounded-xl border border-white/10 bg-white/5 p-1">
            <button
              type="button"
              onClick={() => setActiveTab("insights")}
              className={`rounded-lg px-4 py-2 text-sm ${
                activeTab === "insights"
                  ? "bg-white/15 text-white"
                  : "text-[var(--color-mist)] hover:bg-white/10"
              }`}
            >
              Insights
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("anomalies")}
              className={`rounded-lg px-4 py-2 text-sm ${
                activeTab === "anomalies"
                  ? "bg-white/15 text-white"
                  : "text-[var(--color-mist)] hover:bg-white/10"
              }`}
            >
              Anomalies
            </button>
          </div>

          {activeTab === "insights" ? (
            <>
              <div className="grid gap-3 md:grid-cols-3">
                <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                  <p className="text-xs text-[var(--color-mist)]">
                    Est. next month
                  </p>
                  <p className="text-4xl font-semibold text-white">
                    {toInr(result.forecast.next_month_expense_forecast)}
                  </p>
                  <p className="text-xs text-[var(--color-mist)]">
                    {result.forecast.months_used} month(s) analysed
                  </p>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                  <p className="text-xs text-[var(--color-mist)]">
                    Anomalies flagged
                  </p>
                  <p className="text-4xl font-semibold text-[#d0703d]">
                    {counts.all}
                  </p>
                  <p className="text-xs text-[var(--color-mist)]">
                    {counts.high} high severity
                  </p>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                  <p className="text-xs text-[var(--color-mist)]">
                    Potential savings
                  </p>
                  <p className="text-4xl font-semibold text-[#5f9f35]">
                    {toInr(totalPotentialSavings)}
                  </p>
                  <p className="text-xs text-[var(--color-mist)]">
                    if tips applied
                  </p>
                </div>
              </div>

              <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                <div className="mb-4 flex items-center justify-between gap-3">
                  <h3 className="text-2xl font-semibold text-white">
                    Spending forecast
                  </h3>
                </div>
                <div className="space-y-3">
                  {suggestionRows.map((row, index) => {
                    const currentPct = Math.min(
                      100,
                      (row.current / maxForecast) * 100,
                    );
                    const suggestedPct = Math.min(
                      100,
                      (row.suggested / maxForecast) * 100,
                    );
                    const savingsPct = Math.min(
                      100,
                      (row.save / maxForecast) * 100,
                    );
                    const color =
                      FORECAST_COLORS[index % FORECAST_COLORS.length];
                    return (
                      <div
                        key={row.category}
                        className="grid grid-cols-[120px_1fr_90px] items-center gap-3 text-sm"
                      >
                        <div className="truncate text-white">
                          {row.category}
                        </div>
                        <div className="space-y-1">
                          <div className="relative h-6 rounded-md bg-black/30">
                            <div
                              className="absolute inset-y-0 left-0 rounded-md opacity-35"
                              style={{
                                width: `${suggestedPct}%`,
                                backgroundColor: color,
                              }}
                            />
                            <div
                              className="absolute inset-y-0 left-0 rounded-md"
                              style={{
                                width: `${currentPct}%`,
                                backgroundColor: color,
                              }}
                            />
                            <span className="absolute left-2 top-1 text-[11px] font-semibold text-white">
                              {toInr(row.current)}
                            </span>
                          </div>
                          <div className="relative h-2 rounded-full bg-black/25">
                            <div
                              className="absolute inset-y-0 left-0 rounded-full bg-[#cfe6a7]"
                              style={{ width: `${savingsPct}%` }}
                            />
                          </div>
                        </div>
                        <div className="text-right text-[var(--color-mist)]">
                          <div className="text-xs">
                            Budget {toInr(row.suggested)}
                          </div>
                          <div className="text-xs text-[#cfe6a7]">
                            Save {toInr(row.save)}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-white">
                    Smart budget suggestions
                  </h3>
                  <span className="text-sm text-[var(--color-mist)]">
                    {suggestionRows.length} tips - ranked by impact
                  </span>
                </div>
                <div className="space-y-4">
                  {suggestionRows.map((row, index) => (
                    <div
                      key={row.category}
                      className="border-t border-white/10 pt-4 first:border-t-0 first:pt-0"
                    >
                      <div className="mb-1 flex items-start gap-3">
                        <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-[#f0eadf] text-sm font-semibold text-[#2f2a20]">
                          {index + 1}
                        </span>
                        <div>
                          <p className="text-base font-semibold text-white">
                            Cap {row.category} spending
                          </p>
                          <p className="text-xs text-[var(--color-mist)]">
                            Current monthly average is {toInr(row.current)}.
                            Suggested cap is {toInr(row.suggested)}.
                          </p>
                        </div>
                      </div>
                      <div className="ml-10 inline-flex rounded-full bg-[#e6efcf] px-3 py-1 text-xs font-semibold text-[#2a4214]">
                        Save {toInr(row.save)}/mo
                      </div>
                    </div>
                  ))}
                  <div className="text-sm text-[var(--color-mist)]">
                    {result.summary}
                  </div>
                </div>
              </div>
            </>
          ) : null}

          {activeTab === "anomalies" ? renderAnomalyPanel() : null}
        </div>
      ) : null}
    </div>
  );
}
