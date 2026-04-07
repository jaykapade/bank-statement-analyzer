import Link from "next/link";
import type { JobListItem } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";

export function JobsTable({ jobs }: { jobs: JobListItem[] }) {
  if (jobs.length === 0) {
    return (
      <div className="dashboard-surface rounded-[1.75rem] p-6 text-sm leading-6 text-[var(--color-mist)]">
        No jobs yet. Upload a statement to create the first processing run.
      </div>
    );
  }

  return (
    <div className="dashboard-surface overflow-hidden rounded-[1.75rem]">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-white/10">
          <thead className="bg-white/4">
            <tr>
              <th className="px-4 py-3 text-left text-xs uppercase tracking-[0.24em] text-[var(--color-mist)]">
                File
              </th>
              <th className="px-4 py-3 text-left text-xs uppercase tracking-[0.24em] text-[var(--color-mist)]">
                Status
              </th>
              <th className="px-4 py-3 text-left text-xs uppercase tracking-[0.24em] text-[var(--color-mist)]">
                Job ID
              </th>
              <th className="px-4 py-3 text-left text-xs uppercase tracking-[0.24em] text-[var(--color-mist)]">
                Open
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/8">
            {jobs.map((job) => (
              <tr key={job.job_id} className="transition hover:bg-white/4">
                <td className="px-4 py-4 text-sm text-[var(--color-paper)]">
                  {job.filename || "Unnamed upload"}
                </td>
                <td className="px-4 py-4 text-sm text-[var(--color-paper)]">
                  <StatusBadge status={job.status} />
                </td>
                <td className="px-4 py-4 font-mono text-xs text-[var(--color-mist)]">
                  {job.job_id}
                </td>
                <td className="px-4 py-4 text-sm">
                  <Link
                    className="text-[var(--color-cyan)] underline-offset-4 hover:underline"
                    href={`/jobs/${job.job_id}`}
                  >
                    Open job
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
