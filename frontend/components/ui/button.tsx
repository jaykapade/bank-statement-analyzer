import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-medium transition-all outline-none disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "border border-cyan-300/20 bg-[linear-gradient(135deg,rgba(8,145,178,0.96),rgba(29,78,216,0.92),rgba(67,56,202,0.9))] text-cyan-50 shadow-[0_18px_40px_rgba(37,99,235,0.22)] hover:-translate-y-0.5 hover:saturate-110",
        secondary:
          "border border-white/10 bg-white/5 text-slate-100 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)] hover:-translate-y-0.5 hover:border-cyan-300/25 hover:bg-white/8",
        outline:
          "border border-white/10 bg-transparent text-slate-100 hover:border-cyan-300/25 hover:bg-white/5",
        ghost: "text-slate-300 hover:bg-white/6 hover:text-white",
        destructive:
          "border border-rose-400/20 bg-rose-500/10 text-rose-200 hover:border-rose-400/30 hover:bg-rose-500/15",
        nav: "justify-start rounded-2xl border border-transparent px-4 py-3 text-sm font-semibold text-slate-300 hover:bg-white/4 hover:text-white",
      },
      size: {
        default: "h-11 px-4 py-2",
        sm: "h-9 rounded-lg px-3",
        lg: "h-12 px-6 text-sm",
        icon: "h-10 w-10",
      },
      active: {
        true: "border-cyan-300/20 bg-[linear-gradient(135deg,rgba(56,189,248,0.14),rgba(255,255,255,0.03))] text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.04),0_10px_24px_rgba(8,18,34,0.22)]",
        false: "",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
      active: false,
    },
  },
);

export type ButtonProps = React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
  };

function Button({
  className,
  variant,
  size,
  active,
  asChild = false,
  ...props
}: ButtonProps) {
  const Comp = asChild ? Slot : "button";

  return (
    <Comp
      className={cn(buttonVariants({ variant, size, active }), className)}
      {...props}
    />
  );
}

export { Button, buttonVariants };
