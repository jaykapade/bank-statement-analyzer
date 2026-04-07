import { SectionCard } from "@/components/section-card";
import { UploadForm } from "@/components/upload-form";

export default function UploadPage() {
  return (
    <div className="space-y-6">
      <section className="grid gap-6 md:grid-cols-3">
        <SectionCard
          eyebrow="Step 1"
          title="Upload"
          body="Choose one PDF statement and submit it with the new glassmorphic drop area."
        />
        <SectionCard
          eyebrow="Step 2"
          title="Track"
          body="The jobs view becomes the live status space while extraction and categorization run."
        />
        <SectionCard
          eyebrow="Step 3"
          title="Review"
          body="Once rows exist, the user can inspect transactions and continue the review flow."
        />
      </section>
      <section className="grid items-stretch gap-6 lg:grid-cols-[1.25fr_0.75fr]">
        <SectionCard
          title="Upload a bank statement"
          className="h-full min-h-[30rem]"
          contentClassName="flex h-full flex-1"
        >
          <UploadForm />
        </SectionCard>

        <SectionCard
          eyebrow="Summary"
          title="Upload flow"
          body="One statement becomes one processing job. After submission, the app sends you directly to the job page for status tracking and results."
          className="h-full"
        >
          <div className="grid gap-3">
            <div className="rounded-[1.25rem] border border-white/8 bg-white/4 px-4 py-4">
              <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--color-mist)]">
                File type
              </p>
              <p className="mt-2 text-sm font-medium text-white">
                Single PDF statement
              </p>
            </div>
            <div className="rounded-[1.25rem] border border-white/8 bg-white/4 px-4 py-4">
              <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--color-mist)]">
                Next screen
              </p>
              <p className="mt-2 text-sm font-medium text-white">
                Job status workspace
              </p>
            </div>
            <div className="rounded-[1.25rem] border border-white/8 bg-white/4 px-4 py-4">
              <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--color-mist)]">
                Processing
              </p>
              <p className="mt-2 text-sm font-medium text-white">
                Pending, extracting, categorizing, completed
              </p>
            </div>
          </div>
        </SectionCard>
      </section>
    </div>
  );
}
