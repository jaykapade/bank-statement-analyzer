import Link from "next/link";
import type { PaginationMeta } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

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
    <Card className="mt-5 rounded-[1.25rem] bg-white/4">
      <CardContent className="flex flex-col gap-3 px-4 py-4 text-sm text-[var(--color-mist)] sm:flex-row sm:items-center sm:justify-between">
        <p>
          Showing {start}-{end} of {pagination.total} {label}
        </p>
        <div className="flex flex-wrap gap-2">
        {pagination.has_prev ? (
          <Button asChild variant="secondary">
            <Link href={buildHref(pagination.page - 1)}>Previous</Link>
          </Button>
        ) : (
          <Button
            aria-disabled="true"
            className="pointer-events-none opacity-50"
            variant="secondary"
          >
            Previous
          </Button>
        )}
        <span
          className={cn(
            "inline-flex h-11 items-center rounded-xl border border-white/10 px-4 font-mono text-xs text-white",
          )}
        >
          Page {pagination.page} of {pagination.total_pages}
        </span>
        {pagination.has_next ? (
          <Button asChild variant="secondary">
            <Link href={buildHref(pagination.page + 1)}>Next</Link>
          </Button>
        ) : (
          <Button
            aria-disabled="true"
            className="pointer-events-none opacity-50"
            variant="secondary"
          >
            Next
          </Button>
        )}
        </div>
      </CardContent>
    </Card>
  );
}
