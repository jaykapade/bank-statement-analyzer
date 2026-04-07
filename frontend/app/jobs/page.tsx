import Link from "next/link";
import { ErrorToast } from "@/components/error-toast";
import { JobsTable } from "@/components/jobs-table";
import { SectionCard } from "@/components/section-card";
import { SummaryCard } from "@/components/summary-card";
import { getJobs, type JobListItem } from "@/lib/api";

export default async function JobsPage() {
  let jobs: JobListItem[] = [];
  let error: string | null = null;

  try {
    const response = await getJobs();
    jobs = response.jobs;
  } catch (caughtError) {
    error =
      caughtError instanceof Error
        ? caughtError.message
        : "Unable to load jobs right now.";
  }

  const completedCount = jobs.filter(
    (job) => job.status === "completed",
  ).length;
  const activeCount = jobs.filter((job) =>
    ["pending", "extracting", "categorizing"].includes(job.status),
  ).length;
  const failedCount = jobs.filter((job) =>
    ["failed", "extract_failed", "categorize_failed"].includes(job.status),
  ).length;

  return (
    <div className="space-y-6">
      {error ? <ErrorToast message={error} /> : null}
      <SectionCard eyebrow="" title="Job history" body="">
        <div className="grid gap-3 md:grid-cols-4">
          <SummaryCard label="Total jobs" value={jobs.length} />
          <SummaryCard label="Active" value={activeCount} />
          <SummaryCard label="Completed" value={completedCount} />
          <SummaryCard label="Needs attention" value={failedCount} />
        </div>
      </SectionCard>

      {error ? (
        <SectionCard title="Jobs unavailable" body="Try again or upload a new statement.">
          <Link className="button-secondary" href="/upload">
            Go to upload
          </Link>
        </SectionCard>
      ) : (
        <JobsTable jobs={jobs} />
      )}
    </div>
  );
}
