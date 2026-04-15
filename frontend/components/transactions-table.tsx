"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Check, Pencil, Plus, Trash2, X } from "lucide-react";
import { toast } from "sonner";
import type { PaginationMeta, Transaction } from "@/lib/api";
import {
  createTransaction,
  deleteTransaction,
  updateTransaction,
} from "@/lib/api";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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

type TransactionDraft = {
  date: string;
  description: string;
  category: string;
  category_status: "pending" | "done" | "failed";
  amount: string;
};

export function TransactionsTable({
  transactions,
  pagination,
  pageHrefPrefix,
  editable = false,
  jobId,
}: {
  transactions: Transaction[];
  pagination?: PaginationMeta;
  pageHrefPrefix?: string;
  editable?: boolean;
  jobId?: string;
}) {
  const router = useRouter();
  const [editingRows, setEditingRows] = useState<Record<string, boolean>>({});
  const [submittingId, setSubmittingId] = useState<string | null>(null);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const [isAdding, setIsAdding] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [newDraft, setNewDraft] = useState<TransactionDraft>({
    date: "",
    description: "",
    category: "",
    category_status: "pending",
    amount: "",
  });
  const initialDrafts = useMemo(() => {
    return transactions.reduce<Record<string, TransactionDraft>>(
      (acc, item) => {
        acc[item.id] = {
          date: item.date,
          description: item.description,
          category: item.category ?? "",
          category_status: item.category_status,
          amount: String(item.amount),
        };
        return acc;
      },
      {},
    );
  }, [transactions]);
  const [drafts, setDrafts] =
    useState<Record<string, TransactionDraft>>(initialDrafts);

  useEffect(() => {
    setDrafts(initialDrafts);
  }, [initialDrafts]);

  function updateDraft(
    transactionId: string,
    field: keyof TransactionDraft,
    value: string,
  ) {
    setDrafts((prev) => ({
      ...prev,
      [transactionId]: {
        ...prev[transactionId],
        [field]: value,
      },
    }));
  }

  function beginEdit(transactionId: string) {
    if (submittingId) {
      return;
    }
    setEditingRows((prev) => ({ ...prev, [transactionId]: true }));
  }

  function cancelEdit(transactionId: string) {
    const original = transactions.find((item) => item.id === transactionId);
    if (original) {
      setDrafts((prev) => ({
        ...prev,
        [transactionId]: {
          date: original.date,
          description: original.description,
          category: original.category ?? "",
          category_status: original.category_status,
          amount: String(original.amount),
        },
      }));
    }
    setEditingRows((prev) => ({ ...prev, [transactionId]: false }));
  }

  async function saveRow(transactionId: string) {
    if (!editable || !jobId) {
      return;
    }
    const draft = drafts[transactionId];
    if (!draft) {
      return;
    }

    const amount = Number(draft.amount);
    if (!draft.date || !draft.description || Number.isNaN(amount)) {
      toast.error("Date, description, and a valid amount are required.");
      return;
    }

    try {
      setSubmittingId(transactionId);
      await updateTransaction(jobId, transactionId, {
        date: draft.date,
        description: draft.description,
        category: draft.category || null,
        category_status: draft.category_status,
        amount,
      });
      toast.success("Transaction updated.");
      setEditingRows((prev) => ({ ...prev, [transactionId]: false }));
      router.refresh();
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Unable to update transaction.",
      );
    } finally {
      setSubmittingId(null);
    }
  }

  async function removeRow(transactionId: string) {
    if (!editable || !jobId) {
      return;
    }

    try {
      setSubmittingId(transactionId);
      await deleteTransaction(jobId, transactionId);
      toast.success("Transaction deleted.");
      setPendingDeleteId(null);
      router.refresh();
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Unable to delete transaction.",
      );
    } finally {
      setSubmittingId(null);
    }
  }

  async function addRow() {
    if (!editable || !jobId) {
      return;
    }

    const amount = Number(newDraft.amount);
    if (!newDraft.date || !newDraft.description || Number.isNaN(amount)) {
      toast.error("Date, description, and a valid amount are required.");
      return;
    }

    try {
      setIsCreating(true);
      await createTransaction(jobId, {
        date: newDraft.date,
        description: newDraft.description,
        category: newDraft.category || null,
        category_status: newDraft.category_status,
        amount,
      });
      toast.success("Transaction added.");
      setIsAdding(false);
      setNewDraft({
        date: "",
        description: "",
        category: "",
        category_status: "pending",
        amount: "",
      });
      router.refresh();
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Unable to create transaction.",
      );
    } finally {
      setIsCreating(false);
    }
  }

  if (transactions.length === 0 && !editable) {
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
      {editable ? (
        <CardContent className="border-b border-white/10 p-4 flex justify-end">
          <Button
            disabled={Boolean(submittingId) || isCreating}
            onClick={() => setIsAdding(true)}
            size="sm"
            type="button"
            variant="secondary"
          >
            <Plus className="h-4 w-4" />
            Add transaction
          </Button>
        </CardContent>
      ) : null}
      <Table>
        <TableHeader className="bg-black/10">
          <TableRow className="hover:bg-black/10">
            <TableHead>Date</TableHead>
            <TableHead>Description</TableHead>
            <TableHead>Category</TableHead>
            <TableHead className="text-right">Amount</TableHead>
            {editable ? <TableHead>Actions</TableHead> : null}
          </TableRow>
        </TableHeader>
        <TableBody>
          {editable && isAdding ? (
            <TableRow>
              <TableCell>
                <Input
                  className="h-9 min-w-32"
                  onChange={(event) =>
                    setNewDraft((prev) => ({
                      ...prev,
                      date: event.target.value,
                    }))
                  }
                  placeholder="YYYY-MM-DD"
                  value={newDraft.date}
                />
              </TableCell>
              <TableCell>
                <Input
                  className="h-9 min-w-56"
                  onChange={(event) =>
                    setNewDraft((prev) => ({
                      ...prev,
                      description: event.target.value,
                    }))
                  }
                  placeholder="Description"
                  value={newDraft.description}
                />
              </TableCell>
              <TableCell>
                <Input
                  className="h-9 min-w-36"
                  onChange={(event) =>
                    setNewDraft((prev) => ({
                      ...prev,
                      category: event.target.value,
                    }))
                  }
                  placeholder="Category"
                  value={newDraft.category}
                />
              </TableCell>
              <TableCell className="text-right">
                <Input
                  className="ml-auto h-9 w-32 text-right"
                  onChange={(event) =>
                    setNewDraft((prev) => ({
                      ...prev,
                      amount: event.target.value,
                    }))
                  }
                  placeholder="0.00"
                  type="number"
                  value={newDraft.amount}
                />
              </TableCell>
              <TableCell>
                <div className="flex flex-wrap gap-2">
                  <Button
                    disabled={isCreating || Boolean(submittingId)}
                    onClick={() => void addRow()}
                    size="sm"
                    type="button"
                    variant="secondary"
                  >
                    <Check className="h-4 w-4" />
                    {isCreating ? "Adding..." : "Add"}
                  </Button>
                  <Button
                    disabled={isCreating || Boolean(submittingId)}
                    onClick={() => {
                      setIsAdding(false);
                      setNewDraft({
                        date: "",
                        description: "",
                        category: "",
                        category_status: "pending",
                        amount: "",
                      });
                    }}
                    size="sm"
                    type="button"
                    variant="outline"
                  >
                    <X className="h-4 w-4" />
                    Cancel
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ) : null}
          {transactions.map((transaction) => {
            const isEditing = Boolean(editingRows[transaction.id]);
            const isSubmitting = submittingId === transaction.id;
            const draft = drafts[transaction.id];
            return (
              <TableRow key={transaction.id}>
                <TableCell>
                  {isEditing && draft ? (
                    <Input
                      className="h-9 min-w-32"
                      onChange={(event) =>
                        updateDraft(transaction.id, "date", event.target.value)
                      }
                      value={draft.date}
                    />
                  ) : (
                    transaction.date
                  )}
                </TableCell>
                <TableCell>
                  {isEditing && draft ? (
                    <Input
                      className="h-9 min-w-56"
                      onChange={(event) =>
                        updateDraft(
                          transaction.id,
                          "description",
                          event.target.value,
                        )
                      }
                      value={draft.description}
                    />
                  ) : (
                    transaction.description
                  )}
                </TableCell>
                <TableCell>
                  {isEditing && draft ? (
                    <div className="flex flex-wrap gap-2">
                      <Input
                        className="h-9 min-w-36"
                        onChange={(event) =>
                          updateDraft(
                            transaction.id,
                            "category",
                            event.target.value,
                          )
                        }
                        value={draft.category}
                      />
                    </div>
                  ) : (
                    transaction.category || "Uncategorized"
                  )}
                </TableCell>
                <TableCell className="text-right">
                  {isEditing && draft ? (
                    <Input
                      className="ml-auto h-9 w-32 text-right"
                      onChange={(event) =>
                        updateDraft(
                          transaction.id,
                          "amount",
                          event.target.value,
                        )
                      }
                      type="number"
                      value={draft.amount}
                    />
                  ) : (
                    <Badge
                      className="font-mono text-sm normal-case tracking-normal"
                      variant={
                        transaction.amount >= 0 ? "success" : "destructive"
                      }
                    >
                      {formatCurrency(transaction.amount)}
                    </Badge>
                  )}
                </TableCell>
                {editable ? (
                  <TableCell>
                    <div className="flex flex-wrap gap-2">
                      {isEditing ? (
                        <>
                          <Button
                            disabled={isSubmitting}
                            onClick={() => saveRow(transaction.id)}
                            size="sm"
                            type="button"
                            variant="secondary"
                          >
                            <Check className="h-4 w-4" />
                            Save
                          </Button>
                          <Button
                            disabled={isSubmitting}
                            onClick={() => cancelEdit(transaction.id)}
                            size="sm"
                            type="button"
                            variant="outline"
                          >
                            <X className="h-4 w-4" />
                            Cancel
                          </Button>
                        </>
                      ) : (
                        <Button
                          disabled={Boolean(submittingId)}
                          onClick={() => beginEdit(transaction.id)}
                          size="sm"
                          type="button"
                          variant="secondary"
                        >
                          <Pencil className="h-4 w-4" />
                          Edit
                        </Button>
                      )}
                      <Button
                        disabled={Boolean(submittingId)}
                        onClick={() => setPendingDeleteId(transaction.id)}
                        size="sm"
                        type="button"
                        variant="destructive"
                      >
                        <Trash2 className="h-4 w-4" />
                        Delete
                      </Button>
                    </div>
                  </TableCell>
                ) : null}
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
      <AlertDialog
        open={Boolean(pendingDeleteId)}
        onOpenChange={(open) => {
          if (!open) {
            setPendingDeleteId(null);
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this transaction?</AlertDialogTitle>
            <AlertDialogDescription>
              This transaction will be permanently removed from the job.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={Boolean(submittingId)}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              disabled={Boolean(submittingId) || !pendingDeleteId}
              onClick={() => {
                if (pendingDeleteId) {
                  void removeRow(pendingDeleteId);
                }
              }}
            >
              {submittingId ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      {pagination && pageHrefPrefix ? (
        <CardFooter className="flex flex-col gap-3 border-t border-white/10 px-4 py-4 text-sm text-[var(--color-mist)] sm:flex-row sm:items-center sm:justify-between">
          <p>
            Showing {start}-{end} of {pagination.total} transactions
          </p>
          <Pagination className="mx-0 w-auto justify-start sm:justify-end">
            <PaginationContent>
              <PaginationItem>
                {pagination.has_prev ? (
                  <PaginationPrevious
                    href={`${pageHrefPrefix}${pagination.page - 1}`}
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
                    href={`${pageHrefPrefix}${pagination.page + 1}`}
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
