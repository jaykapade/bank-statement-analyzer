import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] transition-colors",
  {
    variants: {
      variant: {
        default: "border-white/10 bg-white/8 text-slate-100",
        secondary: "border-white/10 bg-white/5 text-slate-300",
        success: "border-emerald-400/20 bg-emerald-400/16 text-emerald-300",
        warning: "border-amber-400/20 bg-amber-400/16 text-amber-200",
        info: "border-sky-400/20 bg-sky-400/16 text-sky-200",
        accent: "border-indigo-400/20 bg-indigo-400/16 text-indigo-200",
        destructive: "border-rose-400/20 bg-rose-400/16 text-rose-200",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

function Badge({
  className,
  variant,
  ...props
}: React.ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
