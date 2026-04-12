import Link from "next/link";
import type { JobListItem } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export function JobsTable({ jobs }: { jobs: JobListItem[] }) {
  if (jobs.length === 0) {
    return (
      <Card>
        <CardContent className="p-6 text-sm leading-6 text-[var(--color-mist)]">
          No jobs yet. Upload a statement to create the first processing run.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="overflow-hidden">
      <Table>
        <TableHeader className="bg-white/4">
          <TableRow className="hover:bg-white/4">
            <TableHead>File</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Job ID</TableHead>
            <TableHead>Open</TableHead>
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
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
}
