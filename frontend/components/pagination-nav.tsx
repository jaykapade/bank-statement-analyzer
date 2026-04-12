import Link from "next/link";
import type { PaginationMeta } from "@/lib/api";

type PaginationNavProps = {
  pagination: PaginationMeta;
  buildHref: (page: number) => string;
  label?: string;
};

export function PaginationNav({
  pagination,
  buildHref,
  label = "results",
}: PaginationNavProps) {
  if (pagination.total_pages <= 1) {
    return null;
  }

  const start = (pagination.page - 1) * pagination.limit + 1;
  const end = Math.min(pagination.page * pagination.limit, pagination.total);

  return (
    <div className="mt-5 flex flex-col gap-3 rounded-[1.25rem] border border-white/8 bg-white/4 px-4 py-4 text-sm text-[var(--color-mist)] sm:flex-row sm:items-center sm:justify-between">
      <p>
        Showing {start}-{end} of {pagination.total} {label}
      </p>
      <div className="flex flex-wrap gap-2">
        {pagination.has_prev ? (
          <Link className="button-secondary" href={buildHref(pagination.page - 1)}>
            Previous
          </Link>
        ) : (
          <span className="button-secondary pointer-events-none opacity-50">
            Previous
          </span>
        )}
        <span className="rounded-full border border-white/10 px-4 py-2 font-mono text-xs text-white">
          Page {pagination.page} of {pagination.total_pages}
        </span>
        {pagination.has_next ? (
          <Link className="button-secondary" href={buildHref(pagination.page + 1)}>
            Next
          </Link>
        ) : (
          <span className="button-secondary pointer-events-none opacity-50">
            Next
          </span>
        )}
      </div>
    </div>
  );
}
