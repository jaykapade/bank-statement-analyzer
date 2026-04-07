const statusStyles: Record<string, string> = {
  completed: "bg-emerald-400/16 text-emerald-300",
  categorizing: "bg-amber-400/16 text-amber-200",
  extracting: "bg-sky-400/16 text-sky-200",
  extracted: "bg-indigo-400/16 text-indigo-200",
  pending: "bg-white/10 text-white",
  failed: "bg-rose-400/16 text-rose-200",
  extract_failed: "bg-rose-400/16 text-rose-200",
  categorize_failed: "bg-rose-400/16 text-rose-200",
  "needs-attention": "bg-rose-400/16 text-rose-200",
  stable: "bg-emerald-400/16 text-emerald-300",
  active: "bg-amber-400/16 text-amber-200",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] ${
        statusStyles[status] ?? "bg-white/10 text-white"
      }`}
    >
      {status}
    </span>
  );
}
