import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function SummaryCard({
  label,
  value,
  valueClassName,
}: {
  label: string;
  value: string | number;
  valueClassName?: string;
}) {
  return (
    <Card className="h-full rounded-[1.6rem]">
      <CardContent className="flex min-h-[7.2rem] flex-col justify-between gap-4 p-5">
        <span className="text-[0.74rem] uppercase tracking-[0.24em] text-[var(--color-mist-strong)]">
          {label}
        </span>
        <strong
          className={cn(
            "block max-w-full break-words font-mono text-[clamp(1.8rem,3vw,2.35rem)] leading-tight text-white",
            valueClassName,
          )}
        >
          {value}
        </strong>
      </CardContent>
    </Card>
  );
}
