import { Card, CardContent } from "@/components/ui/card";
import type { GeoSummary } from "@/lib/api";

import { displayRate, formatCheckAt } from "../_helpers";

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
            <div className="text-2xl font-semibold">{displayRate(summary?.mention_rate)}</div>
            <div className="text-xs text-slate-500">品牌被提到</div>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="py-4">
            <div className="text-2xl font-semibold">{displayRate(summary?.cite_rate)}</div>
            <div className="text-xs text-slate-500">给出了官网</div>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="py-4">
            <div className="text-2xl font-semibold">{displayRate(summary?.verified_citation_rate)}</div>
            <div className="text-xs text-slate-500">官网来源已核对</div>
          </CardContent>
        </Card>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <Card className="rounded-md">
          <CardContent className="flex items-center justify-between py-4 text-sm">
            <span className="text-slate-500">主要在推竞品</span>
            <span className="font-semibold text-slate-900">{displayRate(summary?.competitor_rate)}</span>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="flex items-center justify-between py-4 text-sm">
            <span className="text-slate-500">提到竞品的次数</span>
            <span className="font-semibold text-slate-900">{summary?.competitor_mentions ?? 0}</span>
          </CardContent>
        </Card>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        <Card className="rounded-md">
          <CardContent className="flex items-center justify-between py-4 text-sm">
            <span className="text-slate-500">检查批次</span>
            <span className="font-semibold text-slate-900">{summary?.sample_runs ?? 0}</span>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="flex items-center justify-between py-4 text-sm">
            <span className="text-slate-500">检查记录</span>
            <span className="font-semibold text-slate-900">{summary?.evidence_results ?? 0}</span>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="py-4 text-sm">
            <div className="text-slate-500">最近一次检查</div>
            <div className="mt-1 font-medium text-slate-900">{formatCheckAt(summary?.latest_run_at)}</div>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
