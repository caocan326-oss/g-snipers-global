import { Badge } from "@/components/ui/badge";
import type { ProjectTargets, Workbench } from "@/lib/api";
import { cn } from "@/lib/utils";

import { toneAccent } from "../_helpers";

export function WorkbenchSummaryHeader({
  data,
  targets,
  executiveSummary,
}: {
  data: Workbench;
  targets: ProjectTargets | null;
  executiveSummary: { label: string; text: string; tone: string }[];
}) {
  return (
    <section className="rounded-md border border-slate-200 bg-white px-5 py-4 shadow-sm">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="brand">客户项目状态</Badge>
            <Badge tone={data.diagnostic_status.includes("处理") ? "amber" : "green"}>{data.diagnostic_status}</Badge>
            <Badge tone={targets?.readiness === "ready" ? "green" : "amber"}>{targets?.readiness === "ready" ? "诊断目标完整" : "诊断目标待补"}</Badge>
          </div>
          <h1 className="mt-3 text-2xl font-semibold text-slate-950">{data.summary.tenant_name}</h1>
          <p className="mt-1 max-w-4xl text-sm leading-6 text-slate-500">
            这里用客户能理解的方式汇总：网站现在有什么风险、Google 搜索表现怎么样、AI 搜索是否能看到客户、下一步应该先做什么。没有测试的数据会明确标记为未测。
          </p>
          <div className="mt-4 grid gap-2 lg:grid-cols-3">
            {executiveSummary.map((item) => (
              <div key={item.label} className="rounded-md border border-slate-200 bg-slate-50 p-3">
                <div className="flex items-center gap-2">
                  <span className={cn("h-2 w-2 rounded-full", toneAccent[item.tone] ?? toneAccent.default)} />
                  <span className="text-xs font-semibold text-slate-700">{item.label}</span>
                </div>
                <p className="mt-1 text-sm leading-5 text-slate-600">{item.text}</p>
              </div>
            ))}
          </div>
        </div>
        <div className="grid w-full gap-2 text-sm sm:grid-cols-3 xl:w-[560px]">
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <div className="text-xs text-slate-500">主域</div>
            <div className="mt-1 truncate font-medium text-slate-900">{data.site_origin || "未登记"}</div>
          </div>
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <div className="text-xs text-slate-500">AI 搜索测试口径</div>
            <div className="mt-1 font-mono text-xs font-medium text-slate-900">标准买家问题集</div>
          </div>
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <div className="text-xs text-slate-500">AI 分析建议</div>
            <div className="mt-1 font-medium text-slate-900">{data.summary.llm_status}</div>
          </div>
        </div>
      </div>
    </section>
  );
}
