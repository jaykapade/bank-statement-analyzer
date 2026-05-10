import { InsightsPanel } from "@/components/insights-panel";
import { SectionCard } from "@/components/section-card";
import { getLatestInsightsRunServer, requireCurrentUser } from "@/lib/server-auth";

export default async function InsightsPage() {
  await requireCurrentUser();
  const initial = await getLatestInsightsRunServer();

  return (
    <div className="space-y-5">
      <SectionCard
        title="AI Insights"
        body="Run anomaly detection, spending forecast, and budget suggestions separately from your upload flow."
      >
        <InsightsPanel initial={initial} />
      </SectionCard>
    </div>
  );
}
