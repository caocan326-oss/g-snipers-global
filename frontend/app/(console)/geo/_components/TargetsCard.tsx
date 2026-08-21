import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ProjectTargets } from "@/lib/api";

export function TargetsCard({ targets }: { targets: ProjectTargets | null }) {
  return (
    <Card className="rounded-md">
      <CardHeader>
        <CardTitle>AI 搜索测试目标</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3 lg:grid-cols-3">
        <div className="rounded-md border border-slate-200 p-3">
          <div className="text-xs font-medium text-slate-500">目标国家</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {(targets?.markets ?? []).slice(0, 6).map((market) => (
              <Badge key={market.id} tone={market.status === "priority" ? "brand" : "default"}>
                {market.name}
              </Badge>
            ))}
            {targets?.markets.length ? null : <span className="text-sm text-slate-500">未设置</span>}
          </div>
        </div>
        <div className="rounded-md border border-slate-200 p-3">
          <div className="text-xs font-medium text-slate-500">问题来源搜索词</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {(targets?.markets.flatMap((market) => market.demand_signals) ?? []).slice(0, 8).map((signal) => (
              <Badge key={signal.id} tone="blue">{signal.theme}</Badge>
            ))}
            {targets?.keyword_count ? null : <span className="text-sm text-slate-500">未设置</span>}
          </div>
        </div>
        <div className="rounded-md border border-slate-200 p-3">
          <div className="text-xs font-medium text-slate-500">竞品对照</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {(targets?.markets.flatMap((market) => market.competitors) ?? []).slice(0, 8).map((competitor) => (
              <Badge key={competitor.id}>{competitor.name}</Badge>
            ))}
            {targets?.competitor_count ? null : <span className="text-sm text-slate-500">未设置</span>}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
