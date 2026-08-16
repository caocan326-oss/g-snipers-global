import { Card, CardContent } from "@/components/ui/card";
import type { GeoSummary } from "@/lib/api";

export function MetricsGrid({ summary }: { summary: GeoSummary | null }) {
  return (
    <>
      <div className="grid gap-3 md:grid-cols-5">
        <Card className="rounded-md">
          <CardContent className="py-4">
            <div className="text-2xl font-semibold">{summary?.prompts ?? 0}</div>
            <div className="text-xs text-slate-500">买家问题</div>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="py-4">
            <div className="text-2xl font-semibold">{summary?.recorded ?? 0}</div>
            <div className="text-xs text-slate-500">已记录槽位</div>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="py-4">
            <div className="text-2xl font-semibold">{summary?.mention_rate ?? "未测"}</div>
            <div className="text-xs text-slate-500">品牌提及率</div>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="py-4">
            <div className="text-2xl font-semibold">{summary?.cite_rate ?? "未测"}</div>
            <div className="text-xs text-slate-500">官网引用率</div>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="py-4">
            <div className="text-2xl font-semibold">{summary?.verified_citation_rate ?? "未测"}</div>
            <div className="text-xs text-slate-500">核验引用率</div>
          </CardContent>
        </Card>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <Card className="rounded-md">
          <CardContent className="flex items-center justify-between py-4 text-sm">
            <span className="text-slate-500">竞品提及率</span>
            <span className="font-semibold text-slate-900">{summary?.competitor_rate ?? "未测"}</span>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="flex items-center justify-between py-4 text-sm">
            <span className="text-slate-500">竞品提及槽位</span>
            <span className="font-semibold text-slate-900">{summary?.competitor_mentions ?? 0}</span>
          </CardContent>
        </Card>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        <Card className="rounded-md">
          <CardContent className="flex items-center justify-between py-4 text-sm">
            <span className="text-slate-500">采样批次</span>
            <span className="font-semibold text-slate-900">{summary?.sample_runs ?? 0}</span>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="flex items-center justify-between py-4 text-sm">
            <span className="text-slate-500">证据记录</span>
            <span className="font-semibold text-slate-900">{summary?.evidence_results ?? 0}</span>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="py-4 text-sm">
            <div className="text-slate-500">最近 run</div>
            <div className="mt-1 truncate font-mono text-xs text-slate-900">{summary?.latest_run_id ?? "暂无"}</div>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
