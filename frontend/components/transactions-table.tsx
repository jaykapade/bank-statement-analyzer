import type { Transaction } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

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
      <Card className="rounded-[1.5rem] bg-white/4">
        <CardContent className="p-6 text-sm leading-6 text-[var(--color-mist)]">
          Transactions will appear here once extraction has finished.
        </CardContent>
      </Card>
    );
  }

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
            <TableRow key={`${transaction.date}-${transaction.description}-${index}`}>
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
    </Card>
  );
}
