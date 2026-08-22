"use client";

import Link from "next/link";
import { Copy, Download, FileSpreadsheet, FileText, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  api,
  downloadApiFile,
  type CustomerBrief,
  type GeoReportTable,
  type SeoReportTable,
  type Workbench,
} from "@/lib/api";
import { copyText } from "@/lib/utils";

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
  const [brief, setBrief] = useState<CustomerBrief | null>(null);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState("");

  useEffect(() => {
    Promise.all([
      api<Workbench>("/api/dashboard/workbench?days=28"),
      api<CustomerBrief>("/api/dashboard/customer-brief"),
    ])
      .then(([workbench, nextBrief]) => {
        setData(workbench);
        setBrief(nextBrief);
      })
      .catch((e) => setError(e.message));
  }, []);

  async function copyPaste() {
    if (!brief?.paste_text) {
      setError("没有可复制的短稿。");
      return;
    }
    setError("");
    try {
      await copyText(brief.paste_text);
      setNote("短稿已复制，可直接贴微信或邮件。");
    } catch {
      setError("复制失败，请手动选中短稿。");
    }
  }

  async function downloadBrief() {
    if (!brief) return;
    setBusy("brief");
    setError("");
    try {
      const date = new Date(brief.generated_at).toISOString().slice(0, 10);
      await downloadApiFile("/api/dashboard/customer-brief.pdf", `本周客户说明-${date}.pdf`);
      setNote("本周客户说明（PDF）已下载。");
    } catch (e) {
      setError(e instanceof Error ? e.message : "下载失败");
    } finally {
      setBusy("");
    }
  }

  async function exportSeoReport() {
    setBusy("seo-report");
    setError("");
    try {
      const date = new Date().toISOString().slice(0, 10);
      await downloadApiFile("/api/onsite/report.pdf", `网站检查说明-${date}.pdf`);
      setNote("网站说明（PDF）已下载。");
    } catch (e) {
      setError(e instanceof Error ? e.message : "网站说明下载失败");
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
      setNote("改法清单已下载。");
    } catch (e) {
      setError(e instanceof Error ? e.message : "改法清单下载失败");
    } finally {
      setBusy("");
    }
  }

  async function exportGeoReport() {
    setBusy("geo-report");
    setError("");
    try {
      const date = new Date().toISOString().slice(0, 10);
      await downloadApiFile("/api/geo/report.pdf", `AI搜索说明-${date}.pdf`);
      setNote("AI 搜索说明（PDF）已下载。");
    } catch (e) {
      setError(e instanceof Error ? e.message : "AI 搜索说明下载失败");
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
      setNote("AI 搜索检查记录已下载。");
    } catch (e) {
      setError(e instanceof Error ? e.message : "检查记录下载失败");
    } finally {
      setBusy("");
    }
  }

  if (error && !data) return <p className="text-sm text-red-600">{error}</p>;
  if (!data || !brief) return <p className="text-sm text-slate-500">加载客户说明…</p>;

  return (
    <div className="space-y-6">
      <section className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="brand">给客户看的这一页</Badge>
              <Badge tone={brief.untested.some((item) => item.includes("尚未检查") || item.includes("尚未")) ? "amber" : "green"}>
                {brief.this_week[0] ?? "可预览"}
              </Badge>
            </div>
            <h1 className="mt-3 text-2xl font-semibold text-slate-950">{brief.title}</h1>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-500">{brief.headline}</p>
          </div>
          <div className="flex flex-col gap-2 sm:min-w-[220px]">
            <Button onClick={copyPaste} disabled={!brief.paste_text}>
              <Copy className="mr-2 h-4 w-4" />
              复制给客户
            </Button>
            <Button variant="outline" onClick={downloadBrief} disabled={busy === "brief"}>
              <FileText className="mr-2 h-4 w-4" />
              {busy === "brief" ? "下载中…" : "下载本周说明（PDF）"}
            </Button>
          </div>
        </div>
        {note ? <p className="mt-3 text-sm text-emerald-700">{note}</p> : null}
        {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
      </section>

      {brief.paste_text ? (
        <Card className="rounded-md">
          <CardHeader>
            <CardTitle>发给客户的短稿</CardTitle>
            <p className="text-sm leading-6 text-slate-500">微信 / 邮件用这一段。工作台说明和下方三处留给你们自己看。</p>
          </CardHeader>
          <CardContent>
            <pre className="whitespace-pre-wrap rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm leading-6 text-slate-800">{brief.paste_text}</pre>
          </CardContent>
        </Card>
      ) : null}

      <section className="grid gap-4 lg:grid-cols-2">
        {brief.sections.map((section) => (
          <Card key={section.key} className="rounded-md">
            <CardHeader>
              <CardTitle>{section.title}</CardTitle>
              {section.body ? <p className="text-sm leading-6 text-slate-500">{section.body}</p> : null}
            </CardHeader>
            <CardContent className="space-y-2">
              {section.items.map((item) => (
                <div key={item} className="whitespace-pre-wrap rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-700">
                  {item}
                </div>
              ))}
            </CardContent>
          </Card>
        ))}
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr_0.9fr]">
        <Card className="rounded-md">
          <CardHeader>
            <CardTitle>本周期动作</CardTitle>
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
            <CardTitle>写法提醒</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm leading-6 text-slate-600">
              <ShieldCheck className="mb-2 h-4 w-4 text-brand-700" />
              没有检查记录时，不要写“已被 AI 稳定推荐”。客户说明只写这次已经看到的事实。
            </div>
            <div className="grid gap-2 text-sm sm:grid-cols-2">
              <div className="rounded-md bg-slate-50 p-3">
                <div className="text-xs text-slate-500">主域</div>
                <div className="mt-1 truncate font-medium text-slate-900">{data.site_origin || "尚未登记"}</div>
              </div>
              <div className="rounded-md bg-slate-50 p-3">
                <div className="text-xs text-slate-500">AI 分析建议</div>
                <div className="mt-1 font-medium text-slate-900">{data.summary.llm_status}</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="rounded-md border border-slate-200 bg-white p-5">
        <div className="text-sm font-medium text-slate-900">更多导出</div>
        <p className="mt-1 text-sm text-slate-500">给客户的说明是排好版的 PDF。改法清单和检查记录仍是表格，留给执行留底。</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button size="sm" variant="outline" onClick={exportSeoReport} disabled={busy === "seo-report"}>
            <FileText className="mr-2 h-4 w-4" />
            下载网站说明（PDF）
          </Button>
          <Button size="sm" variant="outline" onClick={exportSeoTable} disabled={busy === "seo-table"}>
            <FileSpreadsheet className="mr-2 h-4 w-4" />
            下载改法清单
          </Button>
          <Button size="sm" variant="outline" onClick={exportGeoReport} disabled={busy === "geo-report"}>
            <FileText className="mr-2 h-4 w-4" />
            下载 AI 搜索说明（PDF）
          </Button>
          <Button size="sm" variant="outline" onClick={exportGeoTable} disabled={busy === "geo-table"}>
            <Download className="mr-2 h-4 w-4" />
            下载检查记录
          </Button>
        </div>
      </section>
    </div>
  );
}
