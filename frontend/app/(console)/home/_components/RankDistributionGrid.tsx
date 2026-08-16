import { Badge } from "@/components/ui/badge";
import type { WorkbenchSeoPerformance } from "@/lib/api";

export function RankDistributionGrid({
  title,
  distribution,
  empty,
}: {
  title: string;
  distribution?: WorkbenchSeoPerformance["keyword_rank_distribution"];
  empty: string;
}) {
  const total = distribution?.total ?? 0;
  const cells = [
    { label: "TOP 10", value: distribution?.top_10 ?? 0, helper: "强可见" },
    { label: "TOP 30", value: distribution?.top_30 ?? 0, helper: "可冲刺" },
    { label: "TOP 50", value: distribution?.top_50 ?? 0, helper: "需跟踪" },
    { label: "未进前 50", value: (distribution?.beyond_50 ?? 0) + (distribution?.unranked ?? 0), helper: "优先补强" },
  ];
  return (
    <div className="rounded-md border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-slate-950">{title}</div>
          <div className="mt-1 text-xs text-slate-500">{total > 0 ? `共 ${total} 个关键词/查询样本` : empty}</div>
        </div>
        <Badge tone={total > 0 ? "blue" : "amber"}>{total > 0 ? "有数据" : "未测"}</Badge>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 lg:grid-cols-4">
        {cells.map((cell) => (
          <div key={cell.label} className="rounded-md bg-slate-50 p-3">
            <div className="text-xs font-medium text-slate-500">{cell.label}</div>
            <div className="mt-1 text-xl font-semibold text-slate-950">{cell.value}</div>
            <div className="mt-1 text-[11px] text-slate-500">{cell.helper}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
