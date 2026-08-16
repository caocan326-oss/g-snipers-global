import Link from "next/link";
import { FileText, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import type { reportReadyChecks } from "../_helpers";

export function ReportReadinessSection({
  reportChecks,
  passedChecks,
  reportReady,
}: {
  reportChecks: ReturnType<typeof reportReadyChecks>;
  passedChecks: number;
  reportReady: boolean;
}) {
  return (
    <section className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-brand-700" />
            <h2 className="text-lg font-semibold text-slate-950">交付就绪度 / 报告导出检查</h2>
            <Badge tone={reportReady ? "green" : "amber"}>{passedChecks}/{reportChecks.length} 项通过</Badge>
          </div>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            报告可以导出，但只有通过这些检查，结论才足够可信。未测项会在报告中标记为未测，不会被写成已验证结果。
          </p>
        </div>
        <Link href="/distribution">
          <Button type="button" variant={reportReady ? "default" : "outline"}>
            <FileText className="mr-2 h-4 w-4" />
            查看报告中心
          </Button>
        </Link>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {reportChecks.map((item) => (
          <div key={item.label} className={cn("rounded-md border p-3", item.ok ? "border-emerald-200 bg-emerald-50/40" : "border-amber-200 bg-amber-50/40")}>
            <div className="flex items-center justify-between gap-3">
              <span className="text-sm font-medium text-slate-900">{item.label}</span>
              <Badge tone={item.ok ? "green" : "amber"}>{item.status}</Badge>
            </div>
            <p className="mt-1 text-xs leading-5 text-slate-600">{item.detail}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
