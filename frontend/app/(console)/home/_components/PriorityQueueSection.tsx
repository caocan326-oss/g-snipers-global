import Link from "next/link";
import { ArrowRight, ListChecks, RefreshCw } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ExecutionBoard, ExecutionItem } from "@/lib/api";
import { executionStatusLabel } from "../../_labels";

const moduleLabel: Record<string, string> = {
  seo: "网站检查",
  geo: "AI 搜索",
  offsite: "站外曝光",
};

const priorityLabel: Record<string, string> = {
  P0: "紧急",
  P1: "优先",
  P2: "常规",
};

const statusLabel = executionStatusLabel;

function priorityTone(priority: string) {
  if (priority === "P0") return "red";
  if (priority === "P1") return "amber";
  return "default";
}

function statusTone(item: ExecutionItem) {
  if (item.status === "blocked" || item.blocked_reason) return "red";
  if (item.status === "needs_retest" || item.status === "confirmed" || item.status === "reopened") return "amber";
  return "default";
}

function PriorityRow({ item }: { item: ExecutionItem }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-4 transition hover:border-brand-500 hover:shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={priorityTone(item.priority)}>{priorityLabel[item.priority] ?? item.priority ?? "常规"}</Badge>
            <Badge tone="blue">{moduleLabel[item.source_module] ?? item.source_module}</Badge>
            <Badge tone={statusTone(item)}>{statusLabel[item.status] ?? item.status}</Badge>
          </div>
          <h3 className="mt-2 font-semibold text-slate-950">{item.title}</h3>
          {item.subtitle ? <p className="mt-1 line-clamp-2 text-sm text-slate-500">{item.subtitle}</p> : null}
          <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
            <span className="rounded-md bg-slate-50 px-2.5 py-1">负责人：{item.owner_hint || "未指定"}</span>
            {item.retest_method ? <span className="rounded-md bg-slate-50 px-2.5 py-1">复测：{item.retest_method}</span> : null}
          </div>
          {item.blocked_reason ? <p className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{item.blocked_reason}</p> : null}
        </div>
        <Button asChild size="sm" variant="outline" className="shrink-0">
          <Link href={item.href}>
            去处理
            <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
          </Link>
        </Button>
      </div>
    </div>
  );
}

export function PriorityQueueSection({
  board,
  weeklyIds,
  loading,
  error,
  reload,
}: {
  board: ExecutionBoard | null;
  weeklyIds: string[];
  loading: boolean;
  error: string;
  reload: () => void;
}) {
  const weekItems = (board?.items ?? []).filter(
    (item) => weeklyIds.includes(item.id) || item.source_module === "geo",
  );
  const items = weekItems.slice(0, 8);
  const boardTotal = board?.total_open ?? 0;

  return (
    <Card className="rounded-md border-brand-100 shadow-sm">
      <CardHeader className="flex flex-col gap-3 border-b border-slate-100 bg-white sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Badge tone="brand">优先处理</Badge>
            {board ? <Badge tone={weekItems.length ? "amber" : "green"}>这周 {weekItems.length} 项</Badge> : null}
            {board && boardTotal > weekItems.length ? <Badge>{`问题板 ${boardTotal} 条，不是这周要做完`}</Badge> : null}
          </div>
          <CardTitle className="mt-3 flex items-center gap-2 text-xl">
            <ListChecks className="h-5 w-5 text-brand-700" />
            本周期待处理优先级队列
          </CardTitle>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
            这周给客户看的项。问题板上那些检查记录不是这周要做完。客户改不改官网不挡交付。
          </p>
        </div>
        <div className="flex gap-2">
          <Button type="button" size="sm" variant="outline" onClick={reload} disabled={loading}>
            <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
            刷新
          </Button>
          <Button asChild size="sm">
            <Link href="/execution">查看问题板</Link>
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3 p-4">
        {error ? <p className="rounded-md border border-red-100 bg-red-50 px-3 py-3 text-sm text-red-700">{error}</p> : null}
        {loading && !board ? <p className="rounded-md border border-dashed border-slate-300 bg-slate-50 px-3 py-4 text-sm text-slate-500">正在加载待处理队列…</p> : null}
        {!loading && board && items.length === 0 ? (
          <div className="rounded-md border border-emerald-100 bg-emerald-50 px-4 py-5">
            <h3 className="font-medium text-emerald-900">这周还没有要给客户看的项</h3>
            <p className="mt-1 text-sm text-emerald-700">有紧急或优先页、或 AI 搜索待处理时会出现。问题板上的检查记录不是这周要做完。</p>
          </div>
        ) : null}
        {items.map((item) => <PriorityRow key={`${item.source_module}-${item.id}`} item={item} />)}
      </CardContent>
    </Card>
  );
}
