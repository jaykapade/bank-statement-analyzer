"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { retryCategorization } from "@/lib/api";
import { Button } from "@/components/ui/button";

type RetryCategorizationButtonProps = {
  jobId: string;
  disabled?: boolean;
};

export function RetryCategorizationButton({
  jobId,
  disabled = false,
}: RetryCategorizationButtonProps) {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleRetry() {
    try {
      setIsSubmitting(true);
      await retryCategorization(jobId);
      toast.success("Categorization retry started.");
      router.refresh();
    } catch (caughtError) {
      const nextError =
        caughtError instanceof Error
          ? caughtError.message
          : "Retry failed. Please try again.";
      toast.error(nextError);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="space-y-3">
      <Button
        disabled={disabled || isSubmitting}
        onClick={handleRetry}
        type="button"
        variant="secondary"
      >
        {isSubmitting ? "Retrying..." : "Retry categorization"}
      </Button>
    </div>
  );
}
