import Link from "next/link";
import { Database } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { GscStatus, Workbench, WorkbenchSeoPerformance } from "@/lib/api";

import { ActionRow } from "./ActionRow";
import { EmptyState } from "./EmptyState";

export function PriorityAndDataSourceSection({
  data,
  gsc,
  untestedTotal,
  perf,
  authorizeGsc,
}: {
  data: Workbench;
  gsc: GscStatus | null;
  untestedTotal: number;
  perf: WorkbenchSeoPerformance;
  authorizeGsc: () => void;
}) {
  return (
    <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
      <Card className="rounded-md">
        <CardHeader>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>优先处理队列</CardTitle>
              <p className="mt-1 text-sm text-slate-500">按风险等级、证据缺口和待验收状态排序，告诉交付人员今天优先处理什么。</p>
            </div>
            <Badge tone="amber">Top Actions</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {data.next_actions.length ? data.next_actions.slice(0, 6).map((item) => <ActionRow key={item.id} item={item} />) : <EmptyState text="暂无待处理动作。" />}
        </CardContent>
      </Card>

      <Card className="rounded-md">
        <CardHeader>
          <CardTitle>数据源与证据状态</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="rounded-md border border-slate-200 p-3">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-sm font-medium"><Database className="h-4 w-4 text-brand-700" />Google 搜索表现数据</div>
              <Badge tone={gsc?.connected ? "green" : gsc?.configured ? "amber" : "red"}>{gsc?.connected ? "已连接" : gsc?.configured ? "待授权" : "未配置"}</Badge>
            </div>
            <div className="mt-1 truncate text-xs text-slate-500">{gsc?.site_url || gsc?.note || "读取中"}</div>
            <div className="mt-3 flex flex-wrap gap-2">
              {gsc?.connected ? (
                <Link href="/onsite"><Button type="button" variant="outline" size="sm">同步 Google 数据</Button></Link>
              ) : gsc?.configured ? (
                <Button type="button" size="sm" onClick={authorizeGsc}>打开授权页</Button>
              ) : (
                <Link href="/onsite"><Button type="button" variant="outline" size="sm">查看配置要求</Button></Link>
              )}
            </div>
          </div>
          <div className="grid gap-2 text-sm">
            <div className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2"><span className="text-slate-600">未测项</span><span className="font-semibold">{untestedTotal}</span></div>
            <div className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2"><span className="text-slate-600">关键词排名检查</span><span className="font-semibold">{perf.serp_runs}</span></div>
            <div className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2"><span className="text-slate-600">AI 可引用资料草稿</span><span className="font-semibold">{data.summary.geo_assets_draft}</span></div>
          </div>
        </CardContent>
      </Card>
    </section>
  );
}
