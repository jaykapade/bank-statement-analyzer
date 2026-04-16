"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Trash2 } from "lucide-react";
import { toast } from "sonner";
import type { JobListItem, PaginationMeta } from "@/lib/api";
import { deleteJob } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
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

type JobsTableProps = {
  jobs: JobListItem[];
  pagination?: PaginationMeta;
  pageHrefPrefix?: string;
};

export function JobsTable({ jobs, pagination, pageHrefPrefix }: JobsTableProps) {
  const router = useRouter();
  const [submittingId, setSubmittingId] = useState<string | null>(null);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

  async function removeJob(jobId: string) {
    try {
      setSubmittingId(jobId);
      await deleteJob(jobId);
      toast.success("Job deleted.");
      setPendingDeleteId(null);
      router.refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to delete job.");
    } finally {
      setSubmittingId(null);
    }
  }

  if (jobs.length === 0) {
    return (
      <Card>
        <CardContent className="p-6 text-sm leading-6 text-[var(--color-mist)]">
          No jobs yet. Upload a statement to create the first processing run.
        </CardContent>
      </Card>
    );
  }

  const start = pagination ? (pagination.page - 1) * pagination.limit + 1 : 1;
  const end = pagination
    ? Math.min(pagination.page * pagination.limit, pagination.total)
    : jobs.length;

  return (
    <Card className="overflow-hidden">
      <Table>
        <TableHeader className="bg-white/4">
          <TableRow className="hover:bg-white/4">
            <TableHead>File</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Job ID</TableHead>
            <TableHead>Open</TableHead>
            <TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {jobs.map((job) => (
            <TableRow key={job.job_id}>
              <TableCell>{job.filename || "Unnamed upload"}</TableCell>
              <TableCell>
                <StatusBadge status={job.status} />
              </TableCell>
              <TableCell className="font-mono text-xs text-[var(--color-mist)]">
                {job.job_id}
              </TableCell>
              <TableCell>
                <Link
                  className="text-[var(--color-cyan)] underline-offset-4 hover:underline"
                  href={`/jobs/${job.job_id}`}
                >
                  Open job
                </Link>
              </TableCell>
              <TableCell>
                <div className="flex flex-wrap gap-2">
                  <Button
                    disabled={Boolean(submittingId)}
                    onClick={() => setPendingDeleteId(job.job_id)}
                    size="sm"
                    type="button"
                    variant="destructive"
                  >
                    <Trash2 className="h-4 w-4" />
                    Delete
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
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
            <AlertDialogTitle>Delete this job?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently remove the job and all of its transactions.
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
                  void removeJob(pendingDeleteId);
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
            Showing {start}-{end} of {pagination.total} jobs
          </p>
          <Pagination className="mx-0 w-auto justify-start sm:justify-end">
            <PaginationContent>
              <PaginationItem>
                {pagination.has_prev ? (
                  <PaginationPrevious href={`${pageHrefPrefix}${pagination.page - 1}`} />
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
                  <PaginationNext href={`${pageHrefPrefix}${pagination.page + 1}`} />
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
