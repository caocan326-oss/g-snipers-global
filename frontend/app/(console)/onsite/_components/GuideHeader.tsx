import { Bot, ChevronDown, ClipboardList, Download } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { OnsiteGuide } from "@/lib/api";
import { cn } from "@/lib/utils";

const stepTone: Record<string, "green" | "brand" | "default"> = {
  done: "green",
  current: "brand",
  upcoming: "default",
};

export function GuideHeader({
  guide,
  voicePending,
  busyId,
  onPrimary,
  crawlOrSeed,
  writeDrafts,
  recheckSite,
  downloadReport,
  downloadReportTable,
}: {
  guide: OnsiteGuide | null;
  voicePending: boolean;
  busyId: string;
  onPrimary: () => void;
  crawlOrSeed: () => void;
  writeDrafts: () => void;
  recheckSite: () => void;
  downloadReport: () => void;
  downloadReportTable: () => void;
}) {
  const [more, setMore] = useState(false);
  const primaryBusy =
    (guide?.action_key === "generate_drafts" && busyId === "ai-batch") ||
    (guide?.action_key === "fetch_site" && busyId === "fetch-site") ||
    busyId === "save-origin";

  return (
    <section className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-semibold text-slate-950">网站检查与改法</h1>
            <Badge tone="brand">按步骤进行</Badge>
          </div>
          <p className="mt-1 text-sm text-slate-500">先查看网站，再给出改法。未查看的内容不会写成结论，也不会直接修改客户网站。</p>
        </div>
        <Button type="button" onClick={onPrimary} disabled={!guide || Boolean(primaryBusy)}>
          <Bot className="mr-2 h-4 w-4" />
          {primaryBusy ? "处理中…" : guide?.action_label ?? "加载下一步…"}
        </Button>
      </div>

      <ol className="mt-4 grid gap-2 sm:grid-cols-5">
        {(guide?.steps ?? [
          { key: "setup", label: "登记网站", status: "upcoming" },
          { key: "collect", label: "查看网页", status: "upcoming" },
          { key: "diagnose", label: "给出改法", status: "upcoming" },
          { key: "confirm", label: "确认改法", status: "upcoming" },
          { key: "retest", label: "改后复查", status: "upcoming" },
        ]).map((step, index) => (
          <li
            key={step.key}
            className={cn(
              "rounded-md border px-3 py-2",
              step.status === "current" ? "border-brand-600 bg-brand-50" : "border-slate-200 bg-slate-50"
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs text-slate-500">{index + 1}</span>
              <Badge tone={stepTone[step.status] ?? "default"}>{step.status === "current" ? "进行中" : step.status === "done" ? "已完成" : "未开始"}</Badge>
            </div>
            <div className="mt-1 text-sm font-medium text-slate-900">{step.label}</div>
          </li>
        ))}
      </ol>

      <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 px-3 py-3">
        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <Bot className="h-3.5 w-3.5" />
          <span>当前建议</span>
          <Badge tone={guide?.ai_status === "ok" ? "green" : guide?.ai_status === "未配置" ? "amber" : "blue"}>
            {voicePending ? "正在生成说明…" : guide?.ai_status === "ok" ? "已根据查看结果说明" : guide?.ai_status === "未配置" ? "步骤说明（未接入 AI）" : "步骤说明"}
          </Badge>
        </div>
        <p className="mt-2 text-sm leading-6 text-slate-800">{guide?.narrative ?? "正在确认当前步骤…"}</p>
      </div>

      <div className="mt-3">
        <Button type="button" variant="ghost" size="sm" className="px-0 text-slate-500" onClick={() => setMore((v) => !v)}>
          <ChevronDown className={cn("mr-1 h-4 w-4 transition", more ? "rotate-180" : "")} />
          更多操作
        </Button>
        {more ? (
          <div className="mt-2 flex flex-wrap gap-2">
            <Button type="button" variant="outline" size="sm" onClick={crawlOrSeed}>
              <ClipboardList className="mr-2 h-4 w-4" />
              补充更多页面
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={writeDrafts} disabled={busyId === "ai-batch"}>
              <Bot className="mr-2 h-4 w-4" />
              {busyId === "ai-batch" ? "处理中…" : "继续写剩下的改法"}
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={recheckSite} disabled={busyId === "ai-recheck"}>
              <Bot className="mr-2 h-4 w-4" />
              {busyId === "ai-recheck" ? "检查中…" : "再检查一遍"}
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={downloadReport}>
              <Download className="mr-2 h-4 w-4" />
              下载客户说明
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={downloadReportTable}>
              <Download className="mr-2 h-4 w-4" />
              下载执行清单
            </Button>
          </div>
        ) : null}
      </div>
    </section>
  );
}
