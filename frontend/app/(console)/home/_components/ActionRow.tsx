import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { WorkbenchItem } from "@/lib/api";
import { cn } from "@/lib/utils";

import { toneAccent, toneBorder } from "../_helpers";

export function ActionRow({ item }: { item: WorkbenchItem }) {
  return (
    <Link
      href={item.href}
      className={cn(
        "group block rounded-md border bg-white p-4 transition hover:border-brand-500 hover:shadow-sm",
        toneBorder[item.tone] ?? toneBorder.default
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className={cn("h-2 w-2 rounded-full", toneAccent[item.tone] ?? toneAccent.default)} />
            <h3 className="font-medium text-slate-950">{item.title}</h3>
            {item.status ? <Badge tone={item.tone}>{item.status}</Badge> : null}
          </div>
          <p className="mt-1 line-clamp-2 text-sm text-slate-500">{item.subtitle}</p>
          {item.meta ? <p className="mt-2 font-mono text-xs text-slate-400">{item.meta}</p> : null}
        </div>
        <span className="flex shrink-0 items-center gap-1 text-xs font-medium text-brand-700">
          {item.action_label}
          <ArrowRight className="h-3.5 w-3.5 transition group-hover:translate-x-0.5" />
        </span>
      </div>
    </Link>
  );
}
