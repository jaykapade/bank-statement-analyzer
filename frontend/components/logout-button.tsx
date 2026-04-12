"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { logout } from "@/lib/api";
import { Button } from "@/components/ui/button";

export function LogoutButton() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleLogout() {
    try {
      setIsSubmitting(true);
      await logout();
      toast.success("Signed out.");
      router.push("/login");
      router.refresh();
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Unable to sign out right now.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Button
      className="w-full"
      disabled={isSubmitting}
      onClick={handleLogout}
      type="button"
      variant="secondary"
    >
      {isSubmitting ? "Signing out..." : "Sign out"}
    </Button>
  );
}
