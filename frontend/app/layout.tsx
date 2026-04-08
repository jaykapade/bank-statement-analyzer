import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/components/app-shell";
import { Toaster } from "sonner";

export const metadata: Metadata = {
  title: "Finance Tracker",
  description:
    "A premium financial dashboard for uploads, job tracking, and transaction review.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body
        suppressHydrationWarning
        className="min-h-full bg-[var(--color-ink)] text-[var(--color-paper)]"
      >
        <Toaster
          closeButton
          expand={false}
          position="top-right"
          richColors
          theme="dark"
          toastOptions={{
            style: {
              background: "rgba(12, 20, 34, 0.94)",
              border: "1px solid rgba(255,255,255,0.08)",
              color: "#f4f7fb",
            },
          }}
        />
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
