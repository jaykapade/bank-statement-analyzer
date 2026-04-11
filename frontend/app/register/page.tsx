import { AuthForm } from "@/components/auth-form";
import { SectionCard } from "@/components/section-card";
import { redirectIfAuthenticated } from "@/lib/server-auth";

export default async function RegisterPage() {
  await redirectIfAuthenticated();

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <SectionCard
        eyebrow="Authentication"
        title="Create your finance tracker account"
        body="Use email and password for the first release, then we can layer in password reset or social login later if you want."
      >
        <AuthForm mode="register" />
      </SectionCard>
    </div>
  );
}
