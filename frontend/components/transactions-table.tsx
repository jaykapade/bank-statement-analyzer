import type { Transaction } from "@/lib/api";

function formatCurrency(amount: number) {
  const formatted = new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
  return amount > 0 ? `+${formatted}` : formatted;
}

export function TransactionsTable({
  transactions,
}: {
  transactions: Transaction[];
}) {
  if (transactions.length === 0) {
    return (
      <div className="rounded-[1.5rem] border border-white/10 bg-white/4 p-6 text-sm leading-6 text-[var(--color-mist)]">
        Transactions will appear here once extraction has finished.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-[1.5rem] border border-white/10 bg-white/4">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-white/10">
          <thead className="bg-black/10">
            <tr>
              <th className="px-4 py-3 text-left text-xs uppercase tracking-[0.24em] text-[var(--color-mist)]">
                Date
              </th>
              <th className="px-4 py-3 text-left text-xs uppercase tracking-[0.24em] text-[var(--color-mist)]">
                Description
              </th>
              <th className="px-4 py-3 text-left text-xs uppercase tracking-[0.24em] text-[var(--color-mist)]">
                Category
              </th>
              <th className="px-4 py-3 text-right text-xs uppercase tracking-[0.24em] text-[var(--color-mist)]">
                Amount
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/8">
            {transactions.map((transaction, index) => (
              <tr key={`${transaction.date}-${transaction.description}-${index}`}>
                <td className="px-4 py-4 text-sm text-[var(--color-paper)]">
                  {transaction.date}
                </td>
                <td className="px-4 py-4 text-sm text-[var(--color-paper)]">
                  {transaction.description}
                </td>
                <td className="px-4 py-4 text-sm text-[var(--color-paper)]">
                  {transaction.category || "Uncategorized"}
                </td>
                <td
                  className="px-4 py-4 text-right"
                >
                  <span
                    className={`inline-flex rounded-full px-3 py-1 font-mono text-sm font-semibold ${
                      transaction.amount >= 0
                        ? "bg-emerald-400/14 text-emerald-300 ring-1 ring-emerald-400/20"
                        : "bg-red-400/14 text-red-300 ring-1 ring-red-400/20"
                    }`}
                  >
                    {formatCurrency(transaction.amount)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
