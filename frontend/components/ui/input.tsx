import * as React from "react";
import { cn } from "@/lib/utils";

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      className={cn(
        "flex h-11 w-full rounded-xl border border-white/10 bg-black/20 px-4 py-2 text-sm text-white outline-none transition placeholder:text-slate-500 focus-visible:border-cyan-300/45 focus-visible:ring-2 focus-visible:ring-cyan-300/15 disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}

export { Input };
