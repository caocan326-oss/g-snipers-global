import { Badge } from "@/components/ui/badge";
import type { SeoPerformanceSummary } from "@/lib/api";

export function RankDistributionPanel({
  title,
  distribution,
  empty,
}: {
  title: string;
  distribution?: SeoPerformanceSummary["keyword_rank_distribution"];
  empty: string;
}) {
  const total = distribution?.total ?? 0;
  const cells = [
    { label: "TOP 10", value: distribution?.top_10 ?? 0, helper: "第一页" },
    { label: "TOP 30", value: distribution?.top_30 ?? 0, helper: "前三页" },
    { label: "TOP 50", value: distribution?.top_50 ?? 0, helper: "前五页" },
    { label: "未进前 50", value: (distribution?.beyond_50 ?? 0) + (distribution?.unranked ?? 0), helper: "需补强" },
  ];
  return (
    <div className="rounded-md border border-slate-200 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-medium text-slate-900">{title}</div>
          <p className="mt-1 text-xs text-slate-500">{total > 0 ? `共 ${total} 个关键词/查询样本` : empty}</p>
        </div>
        <Badge tone={total > 0 ? "blue" : "amber"}>{total > 0 ? "有数据" : "未测"}</Badge>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
        {cells.map((cell) => (
          <div key={cell.label} className="rounded-md bg-slate-50 p-3">
            <div className="text-xs text-slate-500">{cell.label}</div>
            <div className="mt-1 text-lg font-semibold text-slate-950">{cell.value}</div>
            <div className="mt-1 text-[11px] text-slate-500">{cell.helper}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
