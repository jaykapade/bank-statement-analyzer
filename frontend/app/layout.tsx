import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/components/app-shell";
import { Toaster } from "sonner";
import { getCurrentUserServer } from "@/lib/server-auth";

export const metadata: Metadata = {
  title: "Finance Tracker",
  description:
    "A premium financial dashboard for uploads, job tracking, and transaction review.",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const user = await getCurrentUserServer();

  return (
    <html lang="en" className="h-full antialiased">
      <body
        suppressHydrationWarning
        className="min-h-full bg-[var(--color-ink)] text-[var(--color-paper)]"
      >
        <Toaster
          closeButton
          expand={false}
          position="bottom-right"
          richColors
          theme="dark"
        />
        <AppShell user={user}>{children}</AppShell>
      </body>
    </html>
  );
}
