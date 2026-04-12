"use client";

import { useRouter } from "next/navigation";
import {
  type ChangeEvent,
  type DragEvent,
  type FormEvent,
  useState,
} from "react";
import { toast } from "sonner";
import { getApiBaseUrl } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

type UploadState = {
  error: string | null;
  filename: string;
  isSubmitting: boolean;
};

export function UploadForm() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [state, setState] = useState<UploadState>({
    error: null,
    filename: "",
    isSubmitting: false,
  });

  function applySelectedFile(nextFile: File | null) {
    setFile(nextFile);
    setState((current) => ({
      ...current,
      filename: nextFile?.name ?? "",
      error: null,
    }));
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const nextFile = event.target.files?.[0] ?? null;
    applySelectedFile(nextFile);
  }

  function handleDragOver(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsDragging(true);
  }

  function handleDragLeave(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsDragging(false);
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsDragging(false);
    const nextFile = event.dataTransfer.files?.[0] ?? null;
    applySelectedFile(nextFile);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!file) {
      setState((current) => ({
        ...current,
        error: "Choose a PDF statement before uploading.",
      }));
      return;
    }

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setState((current) => ({
        ...current,
        error: "Only PDF statements are supported right now.",
      }));
      return;
    }

    setState((current) => ({
      ...current,
      error: null,
      isSubmitting: true,
    }));

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${getApiBaseUrl()}/upload`, {
        method: "POST",
        body: formData,
        credentials: "include",
      });

      const payload = (await response.json()) as {
        detail?: string;
        job_id?: string;
      };

      if (!response.ok || !payload.job_id) {
        throw new Error(payload.detail ?? "Upload failed");
      }

      toast.success("Upload started. Opening job workspace...");
      router.push(`/jobs/${payload.job_id}`);
      router.refresh();
    } catch (error) {
      setState((current) => ({
        ...current,
        error:
          error instanceof Error
            ? error.message
            : "Upload failed. Please try again.",
      }));
    } finally {
      setState((current) => ({
        ...current,
        isSubmitting: false,
      }));
    }
  }

  return (
    <form
      className="flex h-full w-full flex-col justify-between gap-5"
      onSubmit={handleSubmit}
    >
      <label
        className={`block w-full flex-1 rounded-[1.75rem] border border-dashed p-6 transition duration-200 ${
          isDragging
            ? "border-cyan-200/65 bg-[linear-gradient(135deg,rgba(56,189,248,0.18),rgba(129,140,248,0.08),rgba(255,255,255,0.05))] shadow-[0_22px_44px_rgba(14,165,233,0.12)]"
            : state.filename
              ? "border-emerald-300/40 bg-[linear-gradient(135deg,rgba(52,211,153,0.12),rgba(255,255,255,0.04))] shadow-[0_18px_40px_rgba(16,185,129,0.08)]"
              : "border-cyan-300/30 bg-[linear-gradient(135deg,rgba(56,189,248,0.08),rgba(255,255,255,0.03))] hover:-translate-y-0.5 hover:border-cyan-300/55 hover:bg-[linear-gradient(135deg,rgba(56,189,248,0.12),rgba(255,255,255,0.04))]"
        }`}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <div className="flex h-full flex-col">
          <span className="block font-mono text-lg text-white">
            Upload statement PDF
          </span>
          <span className="mt-2 block max-w-xl text-sm leading-6 text-[var(--color-mist)]">
            Pick a single bank statement. The backend will create the job
            immediately, process it in the background, and then we will take you
            to the job page.
          </span>
          <span className="mt-4 text-sm font-medium text-cyan-200/80">
            Drag and drop a PDF here or click to Choose PDF.
          </span>
          <input
            accept=".pdf,application/pdf"
            className="sr-only"
            name="file"
            onChange={handleFileChange}
            type="file"
          />
          <div className="mt-auto pt-5">
            <div
              className={`inline-flex rounded-full px-4 py-2 text-sm shadow-[0_10px_24px_rgba(0,0,0,0.22)] ${
                isDragging
                  ? "border border-cyan-200/30 bg-cyan-300/12 text-cyan-100"
                  : state.filename
                    ? "border border-emerald-300/25 bg-emerald-400/12 text-emerald-100"
                    : "border border-white/10 bg-black/20 text-[var(--color-paper)]"
              }`}
            >
              {isDragging
                ? "Drop PDF to attach"
                : state.filename || "Choose PDF"}
            </div>
          </div>
        </div>
      </label>

      <div className="flex flex-wrap items-center gap-3">
        <Button disabled={state.isSubmitting} type="submit">
          {state.isSubmitting ? "Uploading..." : "Upload and process"}
        </Button>
        <Badge variant="secondary">PDF only</Badge>
      </div>

      {state.error ? (
        <div className="rounded-[1.25rem] border border-rose-400/25 bg-rose-400/10 p-4 text-sm leading-6 text-[var(--color-paper)]">
          {state.error}
        </div>
      ) : null}
    </form>
  );
}
