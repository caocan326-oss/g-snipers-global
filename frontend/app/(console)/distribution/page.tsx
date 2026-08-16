"use client";

import Link from "next/link";
import { Download, FileSpreadsheet, FileText, ShieldCheck } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type GeoReport, type GeoReportTable, type SeoReport, type SeoReportTable, type Workbench } from "@/lib/api";

function downloadText(filename: string, content: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export default function ReportDeliveryPage() {
  const [data, setData] = useState<Workbench | null>(null);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState("");

  useEffect(() => {
    api<Workbench>("/api/dashboard/workbench?days=28").then(setData).catch((e) => setError(e.message));
  }, []);

  const readiness = useMemo(() => {
    if (!data) return [];
    const highRisk = data.summary.onsite_open_critical + data.summary.onsite_open_high;
    return [
      { label: "诊断目标", ok: Boolean(data.site_origin), detail: data.site_origin || "未登记客户官网" },
      { label: "SEO 风险", ok: data.summary.onsite_pages > 0, detail: `${highRisk} 个 P0/P1，${data.summary.onsite_pages} 个页面` },
      { label: "GEO 证据", ok: data.summary.geo_recorded > 0, detail: data.summary.geo_recorded > 0 ? `${data.summary.geo_recorded} 条记录` : `${data.summary.geo_untested} 个槽位未测` },
      { label: "执行计划", ok: data.next_actions.length > 0, detail: `${data.next_actions.length} 个下一步动作` },
    ];
  }, [data]);

  async function exportSeoReport() {
    setBusy("seo-report");
    setError("");
    try {
      const report = await api<SeoReport>("/api/onsite/report");
      downloadText(`seo-report-${new Date(report.generated_at).toISOString().slice(0, 10)}.md`, report.markdown, "text/markdown;charset=utf-8");
      setNote("SEO 客户报告已导出。");
    } catch (e) {
      setError(e instanceof Error ? e.message : "SEO 报告导出失败");
    } finally {
      setBusy("");
    }
  }

  async function exportSeoTable() {
    setBusy("seo-table");
    setError("");
    try {
      const report = await api<SeoReportTable>("/api/onsite/report-table");
      downloadText(report.filename, report.csv, "text/csv;charset=utf-8");
      setNote("SEO 执行表格已导出。");
    } catch (e) {
      setError(e instanceof Error ? e.message : "SEO 表格导出失败");
    } finally {
      setBusy("");
    }
  }

  async function exportGeoReport() {
    setBusy("geo-report");
    setError("");
    try {
      const report = await api<GeoReport>("/api/geo/report");
      downloadText(`geo-report-${new Date(report.generated_at).toISOString().slice(0, 10)}.md`, report.markdown, "text/markdown;charset=utf-8");
      setNote("GEO 客户报告已导出。");
    } catch (e) {
      setError(e instanceof Error ? e.message : "GEO 报告导出失败");
    } finally {
      setBusy("");
    }
  }

  async function exportGeoTable() {
    setBusy("geo-table");
    setError("");
    try {
      const report = await api<GeoReportTable>("/api/geo/report-table");
      downloadText(report.filename, report.csv, "text/csv;charset=utf-8");
      setNote("GEO 证据表格已导出。");
    } catch (e) {
      setError(e instanceof Error ? e.message : "GEO 表格导出失败");
    } finally {
      setBusy("");
    }
  }

  if (error && !data) return <p className="text-sm text-red-600">{error}</p>;
  if (!data) return <p className="text-sm text-slate-500">加载报告交付状态…</p>;

  const highRisk = data.summary.onsite_open_critical + data.summary.onsite_open_high;
  const geoReady = data.summary.geo_recorded > 0;

  return (
    <div className="space-y-6">
      <section className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="brand">报告交付</Badge>
              <Badge tone={geoReady && highRisk >= 0 ? "green" : "amber"}>{geoReady ? "可生成阶段报告" : "GEO 证据待补"}</Badge>
            </div>
            <h1 className="mt-3 text-2xl font-semibold text-slate-950">客户诊断报告</h1>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-500">
              把当前 SEO 技术风险、GEO 可见度、站外线索和本周期执行项整理成客户可阅读的交付视图。报告数字必须能追溯到数据源、采样批次或问题证据。
            </p>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            <Button onClick={exportSeoReport} disabled={busy === "seo-report"}>
              <FileText className="mr-2 h-4 w-4" />
              导出 SEO 报告
            </Button>
            <Button variant="outline" onClick={exportSeoTable} disabled={busy === "seo-table"}>
              <FileSpreadsheet className="mr-2 h-4 w-4" />
              导出 SEO 表格
            </Button>
            <Button onClick={exportGeoReport} disabled={busy === "geo-report"}>
              <FileText className="mr-2 h-4 w-4" />
              导出 GEO 报告
            </Button>
            <Button variant="outline" onClick={exportGeoTable} disabled={busy === "geo-table"}>
              <Download className="mr-2 h-4 w-4" />
              导出 GEO 表格
            </Button>
          </div>
        </div>
        {note ? <p className="mt-3 text-sm text-emerald-700">{note}</p> : null}
        {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
      </section>

      <section className="grid gap-4 lg:grid-cols-4">
        {readiness.map((item) => (
          <Card key={item.label} className="rounded-md">
            <CardContent className="py-4">
              <div className="flex items-center justify-between gap-3">
                <div className="text-sm font-medium text-slate-800">{item.label}</div>
                <Badge tone={item.ok ? "green" : "amber"}>{item.ok ? "已具备" : "待补"}</Badge>
              </div>
              <p className="mt-2 text-xs text-slate-500">{item.detail}</p>
            </CardContent>
          </Card>
        ))}
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr_0.9fr]">
        <Card className="rounded-md">
          <CardHeader>
            <CardTitle>执行摘要</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-600">
            <div className="rounded-md bg-slate-50 p-3">
              <div className="font-medium text-slate-950">1. SEO 技术状态</div>
              <p className="mt-1">当前发现 {highRisk} 个 P0/P1 风险，优先处理抓取、收录、Canonical、Schema 和标题结构问题。</p>
            </div>
            <div className="rounded-md bg-slate-50 p-3">
              <div className="font-medium text-slate-950">2. GEO 可见度状态</div>
              <p className="mt-1">{geoReady ? `已有 ${data.summary.geo_recorded} 条 GEO 观测记录。` : `还有 ${data.summary.geo_untested} 个 GEO 采样槽位未测，报告中只能标记为待补证据。`}</p>
            </div>
            <div className="rounded-md bg-slate-50 p-3">
              <div className="font-medium text-slate-950">3. 本周期优先行动</div>
              <p className="mt-1">先完成高风险 SEO 整改、补齐 GEO 采样证据，并把待验收任务推进到复测。</p>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-md">
          <CardHeader>
            <CardTitle>质量闸门</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {[
              ["技术分与 GEO 可见度分开呈现", true],
              ["未测数据保持未测", true],
              ["P0/P1 有整改任务", highRisk > 0],
              ["GEO 结论有证据记录", geoReady],
            ].map(([label, ok]) => (
              <div key={String(label)} className="flex items-center justify-between gap-3 rounded-md border border-slate-200 px-3 py-2 text-sm">
                <span className="text-slate-700">{label}</span>
                <Badge tone={ok ? "green" : "amber"}>{ok ? "通过" : "待补"}</Badge>
              </div>
            ))}
            <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs leading-5 text-slate-500">
              <ShieldCheck className="mb-2 h-4 w-4 text-brand-700" />
              禁止在未采样或无证据时写“已被 AI 稳定推荐”。客户报告只能写当前协议下已经观测到的事实。
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <Card className="rounded-md">
          <CardHeader>
            <CardTitle>本周期 Top 动作</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.next_actions.slice(0, 5).map((item) => (
              <Link key={item.id} href={item.href} className="block rounded-md border border-slate-200 p-3 transition hover:border-brand-500">
                <div className="flex items-center justify-between gap-3">
                  <div className="font-medium text-slate-900">{item.title}</div>
                  <Badge tone={item.tone}>{item.status}</Badge>
                </div>
                <p className="mt-1 text-sm text-slate-500">{item.subtitle}</p>
              </Link>
            ))}
          </CardContent>
        </Card>

        <Card className="rounded-md">
          <CardHeader>
            <CardTitle>报告范围</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 text-sm sm:grid-cols-2">
            <div className="rounded-md bg-slate-50 p-3">
              <div className="text-xs text-slate-500">主域</div>
              <div className="mt-1 truncate font-medium text-slate-900">{data.site_origin || "未登记"}</div>
            </div>
            <div className="rounded-md bg-slate-50 p-3">
              <div className="text-xs text-slate-500">协议</div>
              <div className="mt-1 font-mono text-xs text-slate-900">geo-test-protocol-v1</div>
            </div>
            <div className="rounded-md bg-slate-50 p-3">
              <div className="text-xs text-slate-500">搜索表现</div>
              <div className="mt-1 font-medium text-slate-900">{data.seo_performance.data_status}</div>
            </div>
            <div className="rounded-md bg-slate-50 p-3">
              <div className="text-xs text-slate-500">AI 建议</div>
              <div className="mt-1 font-medium text-slate-900">{data.summary.llm_status}</div>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
