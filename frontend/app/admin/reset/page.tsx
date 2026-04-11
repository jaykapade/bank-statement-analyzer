import { SectionCard } from "@/components/section-card";
import { requireCurrentUser } from "@/lib/server-auth";

export default async function ResetPage() {
  await requireCurrentUser();

  return (
    <div className="space-y-6">
      <SectionCard
        eyebrow="/admin/reset"
        title="Local-only reset utility"
        body="The backend currently exposes `POST /reset`, which deletes all jobs and transactions. This should stay clearly marked as a development tool, not a normal user page."
      >
        <div className="rounded-[1.25rem] border border-[var(--color-coral)]/30 bg-[rgba(163,63,50,0.14)] p-5 text-sm leading-6 text-[var(--color-mist)]">
          <p>This route should only be reachable in local development.</p>
          <p className="mt-2">
            When we wire it up, the UI should require an explicit confirmation step
            before sending the request.
          </p>
        </div>
      </SectionCard>
    </div>
  );
}
