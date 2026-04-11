"use client";

import { useState } from "react";

type JobDebugDialogsProps = {
  jobId: string;
  pdfPreviewUrl: string;
  markdownPreviewUrl: string;
  markdownPreview: string | null;
  markdownLineCount: number;
  markdownCharCount: number;
};

export function JobDebugDialogs({
  jobId,
  pdfPreviewUrl,
  markdownPreviewUrl,
  markdownPreview,
  markdownLineCount,
  markdownCharCount,
}: JobDebugDialogsProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"pdf" | "markdown">("pdf");
  const [isCopied, setIsCopied] = useState(false);

  const handleCopy = async () => {
    if (markdownPreview) {
      await navigator.clipboard.writeText(markdownPreview);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    }
  };

  return (
    <>
      <section className="dashboard-surface rounded-[1.75rem] p-6">
        <p className="text-sm uppercase tracking-[0.3em] text-[var(--color-cyan)]">
          Source Preview
        </p>
        <h2 className="mt-3 font-mono text-2xl font-semibold text-white">
          Statement preview
        </h2>
        <p className="mt-3 max-w-4xl text-sm leading-7 text-[var(--color-mist)]">
          Open the original uploaded PDF in a dialog and compare it against the
          extracted rows. When markdown is available, you can inspect the exact
          extraction input from here too.
        </p>

        <div className="mt-6 flex flex-wrap gap-3">
          <button
            className="button-primary"
            onClick={() => setIsOpen(true)}
            type="button"
          >
            Preview statement
          </button>
        </div>

        {markdownPreview ? (
          <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:max-w-xl">
            <div className="rounded-[1.25rem] border border-white/8 bg-black/15 p-4">
              <p className="text-sm text-[var(--color-mist)]">Markdown lines</p>
              <p className="mt-2 font-mono text-2xl text-white">
                {markdownLineCount}
              </p>
            </div>
            <div className="rounded-[1.25rem] border border-white/8 bg-black/15 p-4">
              <p className="text-sm text-[var(--color-mist)]">Markdown chars</p>
              <p className="mt-2 font-mono text-2xl text-white">
                {markdownCharCount}
              </p>
            </div>
          </div>
        ) : null}
      </section>

      {isOpen ? (
        <div
          className="fixed inset-0 z-[200] flex items-center justify-center bg-black/75 p-4"
          onClick={() => setIsOpen(false)}
        >
          <div
            className="flex h-[94vh] w-[min(98vw,1500px)] flex-col overflow-hidden rounded-[1.75rem] border border-white/10 bg-[var(--color-panel-strong)] text-[var(--color-paper)] shadow-[0_30px_90px_rgba(2,6,23,0.6)]"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-center justify-between gap-4 border-b border-white/10 px-6 py-4">
              <div>
                <p className="text-xs uppercase tracking-[0.24em] text-[var(--color-cyan)]">
                  Statement Preview
                </p>
                <h3 className="mt-2 font-mono text-xl font-semibold text-white">
                  PDF and markdown for {jobId}
                </h3>
              </div>
              <button
                className="button-secondary"
                onClick={() => setIsOpen(false)}
                type="button"
              >
                Close
              </button>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-4">
              <div className="flex overflow-hidden rounded-full border border-white/10 bg-black/20 p-1">
                <button
                  onClick={() => setActiveTab("pdf")}
                  className={`rounded-full px-5 py-1.5 text-sm font-medium transition-colors ${
                    activeTab === "pdf"
                      ? "bg-[var(--color-cyan)] text-black"
                      : "text-[var(--color-mist)] hover:text-white"
                  }`}
                  type="button"
                >
                  PDF
                </button>
                {markdownPreview ? (
                  <button
                    onClick={() => setActiveTab("markdown")}
                    className={`rounded-full px-5 py-1.5 text-sm font-medium transition-colors ${
                      activeTab === "markdown"
                        ? "bg-[var(--color-cyan)] text-black"
                        : "text-[var(--color-mist)] hover:text-white"
                    }`}
                    type="button"
                  >
                    Markdown
                  </button>
                ) : null}
              </div>
              <div className="flex flex-wrap gap-3">
                <a
                  className="button-secondary"
                  href={activeTab === "pdf" ? pdfPreviewUrl : markdownPreviewUrl}
                  rel="noreferrer"
                  target="_blank"
                >
                  Open in new tab
                </a>
              </div>
            </div>
            <div className="min-h-0 flex-1 px-6 pb-6">
              <div className="h-full">
                {activeTab === "pdf" ? (
                  <div className="h-full min-h-0 overflow-hidden rounded-[1.5rem] border border-white/10 bg-black/20">
                    <iframe
                      className="h-full min-h-[520px] w-full bg-white"
                      src={pdfPreviewUrl}
                      title={`PDF preview for ${jobId}`}
                    />
                  </div>
                ) : null}
                {activeTab === "markdown" && markdownPreview ? (
                  <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-[1.5rem] border border-white/10 bg-black/25">
                    <div className="flex shrink-0 items-start justify-between border-b border-white/10 bg-black/20 px-4 py-3">
                      <div>
                        <p className="text-xs uppercase tracking-[0.24em] text-[var(--color-cyan)]">
                          Markdown Debug
                        </p>
                        <div className="mt-2 flex flex-wrap gap-3 text-sm text-[var(--color-mist)]">
                          <span>{markdownLineCount} lines</span>
                          <span>{markdownCharCount} chars</span>
                        </div>
                      </div>
                      <button
                        className="button-secondary"
                        onClick={handleCopy}
                        type="button"
                      >
                        {isCopied ? "Copied!" : "Copy"}
                      </button>
                    </div>
                    <pre className="flex-1 overflow-auto p-4 font-mono text-xs leading-6 whitespace-pre-wrap text-[var(--color-paper)]">
                      {markdownPreview}
                    </pre>
                  </div>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
