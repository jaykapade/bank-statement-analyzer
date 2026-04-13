import type { PaginationMeta, Transaction } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";

function formatCurrency(amount: number) {
  const formatted = new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
  return amount > 0 ? `+${formatted}` : formatted;
}

export function TransactionsTable({
  transactions,
  pagination,
  buildHref,
}: {
  transactions: Transaction[];
  pagination?: PaginationMeta;
  buildHref?: (page: number) => string;
}) {
  if (transactions.length === 0) {
    return (
      <Card className="rounded-[1.5rem] bg-white/4">
        <CardContent className="p-6 text-sm leading-6 text-[var(--color-mist)]">
          Transactions will appear here once extraction has finished.
        </CardContent>
      </Card>
    );
  }

  const start = pagination ? (pagination.page - 1) * pagination.limit + 1 : 1;
  const end = pagination
    ? Math.min(pagination.page * pagination.limit, pagination.total)
    : transactions.length;

  return (
    <Card className="overflow-hidden rounded-[1.5rem] bg-white/4">
      <Table>
        <TableHeader className="bg-black/10">
          <TableRow className="hover:bg-black/10">
            <TableHead>Date</TableHead>
            <TableHead>Description</TableHead>
            <TableHead>Category</TableHead>
            <TableHead className="text-right">Amount</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {transactions.map((transaction, index) => (
            <TableRow
              key={`${transaction.date}-${transaction.description}-${index}`}
            >
              <TableCell>{transaction.date}</TableCell>
              <TableCell>{transaction.description}</TableCell>
              <TableCell>{transaction.category || "Uncategorized"}</TableCell>
              <TableCell className="text-right">
                <Badge
                  className="font-mono text-sm normal-case tracking-normal"
                  variant={transaction.amount >= 0 ? "success" : "destructive"}
                >
                  {formatCurrency(transaction.amount)}
                </Badge>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {pagination && buildHref ? (
        <CardFooter className="flex flex-col gap-3 border-t border-white/10 px-4 py-4 text-sm text-[var(--color-mist)] sm:flex-row sm:items-center sm:justify-between">
          <p>
            Showing {start}-{end} of {pagination.total} transactions
          </p>
          <Pagination className="mx-0 w-auto justify-start sm:justify-end">
            <PaginationContent>
              <PaginationItem>
                {pagination.has_prev ? (
                  <PaginationPrevious
                    href={buildHref(pagination.page - 1)}
                    size="default"
                  />
                ) : (
                  <span className="inline-flex h-10 items-center rounded-xl border border-white/10 px-3 text-white/40">
                    Previous
                  </span>
                )}
              </PaginationItem>
              <PaginationItem>
                <span className="inline-flex h-10 items-center rounded-xl border border-white/10 px-4 font-mono text-xs text-white">
                  Page {pagination.page} of {pagination.total_pages}
                </span>
              </PaginationItem>
              <PaginationItem>
                {pagination.has_next ? (
                  <PaginationNext
                    href={buildHref(pagination.page + 1)}
                    size="default"
                  />
                ) : (
                  <span className="inline-flex h-10 items-center rounded-xl border border-white/10 px-3 text-white/40">
                    Next
                  </span>
                )}
              </PaginationItem>
            </PaginationContent>
          </Pagination>
        </CardFooter>
      ) : null}
    </Card>
  );
}
