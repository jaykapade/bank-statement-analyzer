import type { ReactNode } from "react";

type SectionCardProps = {
  eyebrow?: string;
  title: string;
  body?: string;
  children?: ReactNode;
  className?: string;
  contentClassName?: string;
};

export function SectionCard({
  eyebrow,
  title,
  body,
  children,
  className,
  contentClassName,
}: SectionCardProps) {
  return (
    <section
      className={`dashboard-surface flex h-full flex-col rounded-[1.75rem] p-6 ${className ?? ""}`}
    >
      {eyebrow ? (
        <p className="text-sm uppercase tracking-[0.3em] text-[var(--color-cyan)]">
          {eyebrow}
        </p>
      ) : null}
      <h2
        className={`${eyebrow ? "mt-3" : ""} font-mono text-2xl font-semibold text-white`}
      >
        {title}
      </h2>
      {body ? (
        <p className="mt-3 max-w-3xl text-sm leading-7 text-[var(--color-mist)]">
          {body}
        </p>
      ) : null}
      {children ? (
        <div className={`mt-6 flex-1 ${contentClassName ?? ""}`}>{children}</div>
      ) : null}
    </section>
  );
}
