"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { resetAccount } from "@/lib/api";
import { Button } from "@/components/ui/button";

export function ResetButton() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleReset() {
    if (
      !confirm(
        "Are you sure you want to reset your account? This will delete all your jobs and transactions.",
      )
    ) {
      return;
    }

    try {
      setIsSubmitting(true);
      await resetAccount();
      toast.success("Account reset successfully.");
      router.push("/");
      router.refresh();
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Unable to reset account right now.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Button
      className="w-full"
      disabled={isSubmitting}
      onClick={handleReset}
      type="button"
      variant="destructive"
    >
      {isSubmitting ? "Resetting..." : "Reset Data"}
    </Button>
  );
}
