"use client";

import Link from "next/link";
import { AlertTriangle, ArrowRight, CheckCircle2, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type ExecutionBoard, type ExecutionItem } from "@/lib/api";

const moduleLabel: Record<string, string> = {
  seo: "SEO",
  geo: "GEO",
  offsite: "站外",
};

const statusLabel: Record<string, string> = {
  open: "待处理",
  drafted: "已有方案",
  confirmed: "待复测",
  in_progress: "执行中",
  converted_to_task: "已生成任务",
  needs_retest: "待复测",
  blocked: "受阻",
  reopened: "已重开",
};

function ItemCard({ item }: { item: ExecutionItem }) {
  return (
    <Link href={item.href} className="block">
      <Card className="rounded-md transition hover:border-brand-500 hover:shadow-sm">
        <CardContent className="p-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={item.priority === "P0" || item.priority === "P1" ? "red" : item.priority === "P2" ? "amber" : "default"}>{item.priority}</Badge>
                <Badge tone="blue">{moduleLabel[item.source_module] ?? item.source_module}</Badge>
                <Badge tone={item.status === "blocked" ? "red" : item.status.includes("retest") || item.status === "confirmed" ? "amber" : "default"}>
                  {statusLabel[item.status] ?? item.status}
                </Badge>
              </div>
              <h3 className="mt-2 font-semibold text-slate-950">{item.title}</h3>
              {item.subtitle ? <p className="mt-1 text-sm text-slate-500">{item.subtitle}</p> : null}
              <div className="mt-3 grid gap-2 text-sm md:grid-cols-3">
                <div className="rounded-md bg-slate-50 p-3">
                  <div className="text-xs font-medium text-slate-500">负责人</div>
                  <p className="mt-1 text-slate-700">{item.owner_hint || "未指定"}</p>
                </div>
                <div className="rounded-md bg-slate-50 p-3">
                  <div className="text-xs font-medium text-slate-500">验收标准</div>
                  <p className="mt-1 line-clamp-2 text-slate-700">{item.acceptance_criteria || "待补充"}</p>
                </div>
                <div className="rounded-md bg-slate-50 p-3">
                  <div className="text-xs font-medium text-slate-500">复测方式</div>
                  <p className="mt-1 line-clamp-2 text-slate-700">{item.retest_method || "待补充"}</p>
                </div>
              </div>
              {item.blocked_reason ? <p className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{item.blocked_reason}</p> : null}
            </div>
            <span className="inline-flex shrink-0 items-center gap-1 text-sm font-medium text-brand-700">
              回到原模块 <ArrowRight className="h-4 w-4" />
            </span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

export default function ExecutionPage() {
  const [data, setData] = useState<ExecutionBoard | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<ExecutionBoard>("/api/execution/items").then(setData).catch((e) => setError(e.message));
  }, []);

  const grouped = useMemo(() => {
    const rows = data?.items ?? [];
    return {
      blocked: rows.filter((item) => item.status === "blocked" || item.blocked_reason),
      retest: rows.filter((item) => item.status === "needs_retest" || item.status === "confirmed" || item.status === "reopened"),
      active: rows.filter((item) => item.status !== "blocked" && !item.blocked_reason && !["needs_retest", "confirmed", "reopened"].includes(item.status)),
    };
  }, [data]);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!data) return <p className="text-sm text-slate-500">加载执行清单…</p>;

  return (
    <div className="space-y-6">
      <section className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <Badge tone="brand">Execution Board</Badge>
            <h1 className="mt-3 text-2xl font-semibold text-slate-950">跨模块执行清单</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
              这里不是新的工单系统，只聚合 SEO、GEO、站外模块中未关闭的 Issue。点击任意一项会回到原模块继续处理、验收和复测。
            </p>
          </div>
          <div className="grid w-full gap-2 sm:grid-cols-3 lg:w-[520px]">
            <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
              <div className="flex items-center gap-2 text-xs text-slate-500"><CheckCircle2 className="h-4 w-4" />未关闭</div>
              <div className="mt-1 text-2xl font-semibold">{data.total_open}</div>
            </div>
            <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
              <div className="flex items-center gap-2 text-xs text-slate-500"><AlertTriangle className="h-4 w-4" />受阻</div>
              <div className="mt-1 text-2xl font-semibold">{data.blocked}</div>
            </div>
            <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
              <div className="flex items-center gap-2 text-xs text-slate-500"><RefreshCw className="h-4 w-4" />待复测</div>
              <div className="mt-1 text-2xl font-semibold">{data.needs_retest}</div>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-3">
        <CardHeader className="px-0 pb-0">
          <CardTitle>受阻项</CardTitle>
        </CardHeader>
        {grouped.blocked.length ? grouped.blocked.map((item) => <ItemCard key={`${item.source_module}-${item.id}`} item={item} />) : <p className="rounded-md border border-dashed border-slate-300 bg-white px-4 py-5 text-sm text-slate-500">暂无受阻项。</p>}
      </section>

      <section className="space-y-3">
        <CardHeader className="px-0 pb-0">
          <CardTitle>待复测</CardTitle>
        </CardHeader>
        {grouped.retest.length ? grouped.retest.map((item) => <ItemCard key={`${item.source_module}-${item.id}`} item={item} />) : <p className="rounded-md border border-dashed border-slate-300 bg-white px-4 py-5 text-sm text-slate-500">暂无待复测项。</p>}
      </section>

      <section className="space-y-3">
        <CardHeader className="px-0 pb-0">
          <CardTitle>进行中</CardTitle>
        </CardHeader>
        {grouped.active.length ? grouped.active.map((item) => <ItemCard key={`${item.source_module}-${item.id}`} item={item} />) : <p className="rounded-md border border-dashed border-slate-300 bg-white px-4 py-5 text-sm text-slate-500">暂无进行中的执行项。</p>}
      </section>
    </div>
  );
}
