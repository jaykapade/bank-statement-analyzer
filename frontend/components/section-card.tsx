import type { ReactNode } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

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
    <Card className={cn("flex h-full flex-col", className)}>
      <CardHeader>
        {eyebrow ? (
          <p className="text-sm uppercase tracking-[0.3em] text-[var(--color-cyan)]">
            {eyebrow}
          </p>
        ) : null}
        <CardTitle className={eyebrow ? "mt-1" : ""}>{title}</CardTitle>
        {body ? <CardDescription className="max-w-3xl">{body}</CardDescription> : null}
      </CardHeader>
      {children ? (
        <CardContent className={cn("flex-1", contentClassName)}>{children}</CardContent>
      ) : null}
    </Card>
  );
}
