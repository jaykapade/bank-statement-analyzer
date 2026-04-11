import { AuthForm } from "@/components/auth-form";
import { SectionCard } from "@/components/section-card";
import { redirectIfAuthenticated } from "@/lib/server-auth";

export default async function LoginPage() {
  await redirectIfAuthenticated();

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <SectionCard
        eyebrow="Authentication"
        title="Sign in to your finance workspace"
        body="Your account keeps uploaded statements, job history, and transaction views scoped to you."
      >
        <AuthForm mode="login" />
      </SectionCard>
    </div>
  );
}
