"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type DashboardSummary } from "@/lib/api";

export default function HomePage() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<DashboardSummary>("/api/dashboard/summary")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!data) return <p className="text-sm text-slate-500">加载中…</p>;

  const chains = [
    {
      href: "/onsite",
      title: "站内改页 + 人审",
      value: data.onsite_pages,
      hint: `Critical ${data.onsite_open_critical} · High ${data.onsite_open_high} · Low ${data.onsite_open_low}`,
      body: "抓已登记页 → 按观察出问题 → 改稿与观察分层 → 确认上线后再抓验收。无 GSC 显示未测。",
    },
    {
      href: "/geo",
      title: "GEO：采样 → 工单 → 验收",
      value: data.geo_tickets_open,
      hint:
        data.geo_prompts === 0
          ? "问句未建"
          : `未测槽位 ${data.geo_untested} · 已记录 ${data.geo_recorded}（非引用率）`,
      body: "中西引擎人工采样。引用 ≠ 吸收。不得声称「已让 ChatGPT 引用」。llms.txt 是本链资产。",
    },
    {
      href: "/offsite",
      title: "外链核验 + 分发台",
      value: data.links_unverified,
      hint: `未核验 ${data.links_unverified} · 跟进 ${data.offsite_outreach_open} · 分发队列 ${data.distribution_jobs}`,
      body: "逐条核验（未核验 / 有效 / 失效 / 垃圾）。分发须确认；未配置 Key 不会发送、不会刷成功。",
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">三条交付链</h1>
        <p className="mt-1 text-sm text-slate-500">
          {data.tenant_name} · AI 引擎 {data.llm_status}。低风险 AI 稿落工作区；改线上 / 分发 / 可交付须人确认。没有数据源就写未测。
        </p>
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        {chains.map((c) => (
          <Link key={c.href} href={c.href}>
            <Card className="h-full hover:border-brand-600">
              <CardHeader>
                <CardTitle className="text-base">{c.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-semibold">{c.value}</div>
                <div className="mt-1 text-xs text-slate-500">{c.hint}</div>
                <p className="mt-3 text-sm text-slate-600">{c.body}</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
      <p className="text-sm text-slate-500">
        从「洞察投喂」选市场 / 信号，可直接开站内任务、GEO 工单或外链跟进。
      </p>
    </div>
  );
}
