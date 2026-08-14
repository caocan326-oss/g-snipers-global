"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type DashboardSummary } from "@/lib/api";

export default function HomePage() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<DashboardSummary>("/api/dashboard/summary").then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!data) return <p className="text-sm text-slate-500">加载中…</p>;

  const cards = [
    { label: "跟踪市场", value: data.markets_count, href: "/insights", hint: `优先 ${data.priority_markets}` },
    { label: "SEO 执行中", value: data.seo_in_progress, href: "/seo", hint: "大纲 / 正文 / Meta" },
    { label: "待审核选题", value: data.seo_pending_review, href: "/seo", hint: `可交付 ${data.seo_ready}` },
    { label: "未完工单", value: data.open_work_orders, href: "/work-orders", hint: "洞察与 SEO 执行" },
    { label: "询盘", value: data.inquiries_total, href: "/inquiries", hint: `合格 ${data.qualified_inquiries}` },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">工作台首页</h1>
        <p className="mt-1 text-sm text-slate-500">
          {data.tenant_name} · 本切片只做全球洞察与多语言 SEO 执行，不接广告账户。
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
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
    </div>
  );
}
