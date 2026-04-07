"use client";

import { useEffect } from "react";
import { toast } from "sonner";

type ErrorToastProps = {
  message: string;
};

export function ErrorToast({ message }: ErrorToastProps) {
  useEffect(() => {
    toast.error(message, {
      id: `error:${message}`,
    });
  }, [message]);

  return null;
}
