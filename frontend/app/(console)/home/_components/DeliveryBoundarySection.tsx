import { ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { Workbench } from "@/lib/api";
import { cn } from "@/lib/utils";

export function DeliveryBoundarySection({
  data,
  days,
  setDays,
}: {
  data: Workbench;
  days: number;
  setDays: (value: number) => void;
}) {
  return (
    <section className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-brand-700" />
            <h2 className="text-lg font-semibold text-slate-950">交付边界</h2>
          </div>
          <p className="mt-1 text-sm text-slate-500">客户看到对得上的检查结论，交付人员看到改法、渠道卡片和复查结果。发新媒体是半自动：AI 写稿，人登号或走接口。不自动群发。</p>
        </div>
        <div className="flex rounded-md border border-slate-200 bg-slate-50 p-1">
          {[7, 28, 90].map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setDays(item)}
              className={cn("h-9 rounded px-3 text-sm font-medium", days === item ? "bg-white text-brand-700 shadow-sm" : "text-slate-500 hover:text-slate-800")}
            >
              {item}天
            </button>
          ))}
        </div>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {data.deferred_modules.map((item) => (
          <div key={item.id} className="rounded-md border border-slate-200 p-3">
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium text-slate-800">{item.title}</span>
              <Badge>{item.status}</Badge>
            </div>
            <p className="mt-1 text-xs text-slate-500">{item.subtitle}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
