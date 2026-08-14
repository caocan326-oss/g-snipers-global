"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type DashboardSummary, type Market, type SeoPage } from "@/lib/api";

const seoLabel: Record<string, string> = {
  idea: "选题",
  outline: "大纲",
  draft: "正文",
  meta: "Meta",
  review: "审核中",
  ready: "可交付",
};

export default function HomePage() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [markets, setMarkets] = useState<Market[]>([]);
  const [pages, setPages] = useState<SeoPage[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      api<DashboardSummary>("/api/dashboard/summary"),
      api<Market[]>("/api/markets"),
      api<SeoPage[]>("/api/seo-pages"),
    ])
      .then(([summary, marketList, seoList]) => {
        setData(summary);
        setMarkets(marketList);
        setPages(seoList);
      })
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!data) return <p className="text-sm text-slate-500">加载中…</p>;

  const cards = [
    { label: "跟踪市场", value: data.markets_count, href: "/insights", hint: `优先 ${data.priority_markets}` },
    { label: "SEO 执行中", value: data.seo_in_progress, href: "/seo", hint: "大纲 / 正文 / Meta" },
    { label: "待审核选题", value: data.seo_pending_review, href: "/seo", hint: `可交付 ${data.seo_ready}` },
    { label: "未完工单", value: data.open_work_orders, href: "/work-orders", hint: "洞察与 SEO 执行" },
    { label: "询盘", value: data.inquiries_total, href: "/inquiries", hint: `合格 ${data.qualified_inquiries}` },
    {
      label: "GEO 未测",
      value: data.geo_prompts === 0 ? "未测" : data.geo_untested,
      href: "/geo",
      hint: data.geo_recorded > 0 ? `已记录 ${data.geo_recorded}（非引用率）` : "尚无抽查，不显示 0%",
    },
    {
      label: "站内页面",
      value: data.onsite_pages,
      href: "/onsite",
      hint: `低风险待办 ${data.onsite_open_low} · 高风险 ${data.onsite_open_high}`,
    },
    {
      label: "站外缺口",
      value: data.offsite_gaps,
      href: "/offsite",
      hint: `外联未完 ${data.offsite_outreach_open}`,
    },
    {
      label: "分发任务",
      value: data.distribution_jobs,
      href: "/distribution",
      hint: "渠道未配置则不会发送",
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">工作台首页</h1>
        <p className="mt-1 text-sm text-slate-500">
          {data.tenant_name} · 监测发现问题，执行按风险分级：低风险落工作区草稿，高风险须人工确认。
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {cards.map((c) => (
          <Link key={c.label} href={c.href}>
            <Card className="h-full hover:border-brand-600">
              <CardHeader>
                <CardTitle className="text-sm font-medium text-slate-500">{c.label}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-semibold">{c.value}</div>
                <div className="mt-1 text-xs text-slate-500">{c.hint}</div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>优先市场</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {markets.slice(0, 5).map((m) => (
              <Link key={m.id} href={`/insights/${m.id}`} className="flex items-center justify-between rounded-md border p-3 hover:border-brand-600">
                <div>
                  <div className="font-medium">{m.name}</div>
                  <div className="text-xs text-slate-500">
                    {m.primary_locale} · 需求 {m.demand_count} · 选题 {m.seo_count}
                  </div>
                </div>
                <Badge tone={m.status === "priority" ? "green" : "amber"}>机会 {m.opportunity_score}</Badge>
              </Link>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>SEO 选题进度</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {pages.slice(0, 5).map((p) => (
              <Link key={p.id} href={`/seo/${p.id}`} className="flex items-center justify-between rounded-md border p-3 hover:border-brand-600">
                <div>
                  <div className="font-medium">{p.title}</div>
                  <div className="text-xs text-slate-500">
                    {p.locale} · {p.target_keyword}
                  </div>
                </div>
                <Badge>{seoLabel[p.status] ?? p.status}</Badge>
              </Link>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
