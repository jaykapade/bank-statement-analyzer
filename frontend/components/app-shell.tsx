"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { Clock3, Command, LayoutDashboard, Upload } from "lucide-react";
import type { AuthUser } from "@/lib/api";
import { LogoutButton } from "@/components/logout-button";
import { ResetButton } from "@/components/reset-button";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/upload", label: "Upload", icon: Upload },
  { href: "/jobs", label: "Jobs", icon: Clock3 },
];

function isActive(pathname: string, href: string) {
  if (href === "/") {
    return pathname === "/";
  }

  return pathname.startsWith(href);
}

export function AppShell({
  children,
  user,
}: {
  children: ReactNode;
  user: AuthUser | null;
}) {
  const pathname = usePathname();
  const isAuthRoute = pathname === "/login" || pathname === "/register";
  const activeItem =
    navItems.find((item) => isActive(pathname, item.href)) ?? navItems[0];

  if (!user && isAuthRoute) {
    return (
      <div className="dashboard-grid min-h-screen">
        <main className="mx-auto flex min-h-screen w-full max-w-6xl items-center justify-center px-4 py-10 sm:px-6 lg:px-8">
          <div className="w-full max-w-3xl">{children}</div>
        </main>
      </div>
    );
  }

  return (
    <div className="dashboard-grid min-h-screen">
      <div className="relative mx-auto flex min-h-screen w-full max-w-[1600px] flex-col gap-6 px-4 py-4 sm:px-6 lg:flex-row lg:px-8 lg:py-6">
        <aside className="dashboard-surface rounded-[2rem] p-4 lg:sticky lg:top-6 lg:h-[calc(100vh-3rem)] lg:w-[280px] lg:flex-none">
          <div className="flex h-full flex-col">
            <div className="flex items-center gap-3 rounded-[1.5rem] border border-white/8 bg-[linear-gradient(135deg,rgba(56,189,248,0.16),rgba(129,140,248,0.1),rgba(255,255,255,0.03))] px-4 py-4">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[linear-gradient(135deg,rgba(56,189,248,0.95),rgba(129,140,248,0.85))] text-slate-950">
                <Command className="h-5 w-5" />
              </div>
              <div>
                <p className="text-[11px] uppercase tracking-[0.28em] text-[var(--color-mist-strong)]">
                  Finance tracker
                </p>
                <p className="mt-1 font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-white">
                  Control center
                </p>
              </div>
            </div>

            <nav className="mt-6 flex flex-1 flex-col gap-2">
              {user
                ? navItems.map((item) => {
                    const active = item.href === activeItem.href;
                    const Icon = item.icon;

                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        className={`nav-chip rounded-[1.25rem] px-4 py-3 ${
                          active
                            ? "border border-cyan-300/18 bg-[linear-gradient(135deg,rgba(56,189,248,0.14),rgba(255,255,255,0.03))] text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.04),0_10px_24px_rgba(8,18,34,0.22)]"
                            : ""
                        }`}
                      >
                        <Icon className="h-4 w-4" />
                        <span>{item.label}</span>
                      </Link>
                    );
                  })
                : [
                    <Link
                      key="/login"
                      href="/login"
                      className={`nav-chip rounded-[1.25rem] px-4 py-3 ${
                        pathname === "/login"
                          ? "border border-cyan-300/18 bg-[linear-gradient(135deg,rgba(56,189,248,0.14),rgba(255,255,255,0.03))] text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.04),0_10px_24px_rgba(8,18,34,0.22)]"
                          : ""
                      }`}
                    >
                      <span>Sign in</span>
                    </Link>,
                    <Link
                      key="/register"
                      href="/register"
                      className={`nav-chip rounded-[1.25rem] px-4 py-3 ${
                        pathname === "/register"
                          ? "border border-cyan-300/18 bg-[linear-gradient(135deg,rgba(56,189,248,0.14),rgba(255,255,255,0.03))] text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.04),0_10px_24px_rgba(8,18,34,0.22)]"
                          : ""
                      }`}
                    >
                      <span>Create account</span>
                    </Link>,
                  ]}
            </nav>

              {user && (
                <div className="mb-4">
                  <ResetButton />
                </div>
              )}
            <div className="mt-auto rounded-[1.5rem] border border-white/8 bg-white/4 p-4">
              {user ? (
                <div className="space-y-3">
                  <div>
                    <p className="text-[11px] uppercase tracking-[0.24em] text-[var(--color-mist)]">
                      Signed in
                    </p>
                    <p className="mt-2 break-all text-sm font-medium text-white">
                      {user.email}
                    </p>
                  </div>
                  <LogoutButton />
                </div>
              ) : (
                <div className="space-y-3">
                  <p className="text-sm leading-6 text-[var(--color-mist)]">
                    Sign in to upload statements and keep each job tied to your
                    own workspace.
                  </p>
                  <Link className="button-primary w-full text-center" href="/login">
                    Sign in
                  </Link>
                </div>
              )}
            </div>
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col gap-6">
          <main className="flex-1">{children}</main>
        </div>
      </div>
    </div>
  );
}
