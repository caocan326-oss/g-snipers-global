import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

const tones: Record<string, string> = {
  default: "bg-slate-100 text-slate-700",
  green: "bg-emerald-50 text-emerald-800",
  amber: "bg-amber-50 text-amber-800",
  blue: "bg-sky-50 text-sky-800",
  red: "bg-red-50 text-red-700",
  brand: "bg-brand-100 text-brand-700",
};

export function Badge({
  className,
  tone = "default",
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: keyof typeof tones }) {
  return (
    <span
      className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium", tones[tone], className)}
      {...props}
    />
  );
}
