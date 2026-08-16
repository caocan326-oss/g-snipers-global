"use client";

import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  CheckCircle2,
  ClipboardCheck,
  Database,
  FileText,
  Gauge,
  Globe2,
  Link2,
  SearchCheck,
  ShieldCheck,
  Target,
} from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api, type GscAuthUrl, type GscStatus, type ProjectTargets, type Workbench, type WorkbenchItem } from "@/lib/api";
import { cn } from "@/lib/utils";

const toneBorder: Record<string, string> = {
  default: "border-slate-200",
  green: "border-emerald-200",
  amber: "border-amber-200",
  blue: "border-sky-200",
  red: "border-red-200",
  brand: "border-brand-200",
};

const toneAccent: Record<string, string> = {
  default: "bg-slate-500",
  green: "bg-emerald-600",
  amber: "bg-amber-500",
  blue: "bg-sky-600",
  red: "bg-red-600",
  brand: "bg-brand-600",
};

function EmptyState({ text }: { text: string }) {
  return <p className="rounded-md border border-dashed border-slate-300 bg-slate-50 px-3 py-4 text-sm text-slate-500">{text}</p>;
}

function ActionRow({ item }: { item: WorkbenchItem }) {
  return (
    <Link
      href={item.href}
      className={cn(
        "group block rounded-md border bg-white p-4 transition hover:border-brand-500 hover:shadow-sm",
        toneBorder[item.tone] ?? toneBorder.default
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className={cn("h-2 w-2 rounded-full", toneAccent[item.tone] ?? toneAccent.default)} />
            <h3 className="font-medium text-slate-950">{item.title}</h3>
            {item.status ? <Badge tone={item.tone}>{item.status}</Badge> : null}
          </div>
          <p className="mt-1 line-clamp-2 text-sm text-slate-500">{item.subtitle}</p>
          {item.meta ? <p className="mt-2 font-mono text-xs text-slate-400">{item.meta}</p> : null}
        </div>
        <span className="flex shrink-0 items-center gap-1 text-xs font-medium text-brand-700">
          {item.action_label}
          <ArrowRight className="h-3.5 w-3.5 transition group-hover:translate-x-0.5" />
        </span>
      </div>
    </Link>
  );
}

function MetricTile({ label, value, helper, icon: Icon }: { label: string; value: string | number | null; helper?: string; icon?: typeof Gauge }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
        {Icon ? <Icon className="h-4 w-4 text-slate-400" /> : null}
      </div>
      <div className="mt-2 text-2xl font-semibold text-slate-950">{value ?? "-"}</div>
      {helper ? <div className="mt-1 text-xs text-slate-500">{helper}</div> : null}
    </div>
  );
}

function PillarCard({
  title,
  status,
  statusTone,
  primary,
  helper,
  href,
  icon: Icon,
  children,
}: {
  title: string;
  status: string;
  statusTone: "default" | "green" | "amber" | "blue" | "red" | "brand";
  primary: string;
  helper: string;
  href: string;
  icon: typeof Gauge;
  children: ReactNode;
}) {
  return (
    <Card className="h-full rounded-md">
      <CardHeader className="space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <Icon className="h-5 w-5 text-brand-700" />
            <CardTitle>{title}</CardTitle>
          </div>
          <Badge tone={statusTone}>{status}</Badge>
        </div>
        <div>
          <div className="text-3xl font-semibold text-slate-950">{primary}</div>
          <p className="mt-1 text-sm text-slate-500">{helper}</p>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {children}
        <Link href={href} className="inline-flex items-center gap-1 text-sm font-medium text-brand-700">
          查看详情 <ArrowRight className="h-4 w-4" />
        </Link>
      </CardContent>
    </Card>
  );
}

export default function HomePage() {
  const [data, setData] = useState<Workbench | null>(null);
  const [targets, setTargets] = useState<ProjectTargets | null>(null);
  const [gsc, setGsc] = useState<GscStatus | null>(null);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [days, setDays] = useState(28);
  const [targetForm, setTargetForm] = useState({ site_origin: "", markets: "", keywords: "", competitors: "" });

  useEffect(() => {
    api<Workbench>(`/api/dashboard/workbench?days=${days}`)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [days]);

  useEffect(() => {
    api<ProjectTargets>("/api/project-targets")
      .then((res) => {
        setTargets(res);
        setTargetForm({
          site_origin: res.site_origin || "",
          markets: res.markets.map((m) => [m.name, m.region, m.country_code, m.primary_locale].filter(Boolean).join(" | ")).join("\n"),
          keywords: res.markets.flatMap((m) => m.demand_signals.map((s) => s.theme)).join("\n"),
          competitors: res.markets.flatMap((m) => m.competitors.map((c) => [c.name, c.website].filter(Boolean).join(" | "))).join("\n"),
        });
      })
      .catch((e) => setError(e.message));
    api<GscStatus>("/api/onsite/gsc/status")
      .then(setGsc)
      .catch(() => undefined);
  }, []);

  const reviewTotal = useMemo(() => {
    if (!data) return 0;
    return data.summary.onsite_open_critical + data.summary.onsite_open_high + data.summary.geo_tickets_open + data.summary.seo_pending_review;
  }, [data]);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!data) return <p className="text-sm text-slate-500">加载中…</p>;

  const perf = data.seo_performance;
  const highRisk = data.summary.onsite_open_critical + data.summary.onsite_open_high;
  const untestedTotal = data.summary.geo_untested + (data.summary.onsite_pages === 0 ? 1 : 0);
  const geoRecorded = data.summary.geo_recorded;
  const geoStatusTone = data.summary.geo_untested > 0 ? "amber" : geoRecorded > 0 ? "green" : "default";
  const technicalTone = highRisk > 0 ? "red" : data.summary.onsite_pages > 0 ? "green" : "amber";
  const workTone = reviewTotal > 0 ? "amber" : "green";
  const executiveSummary = [
    {
      label: "技术结论",
      text: highRisk > 0 ? `当前有 ${highRisk} 个 P0/P1 SEO 风险，优先处理抓取、收录、Canonical 和 Schema。` : "当前没有打开的高风险 SEO 问题，重点进入复测和报告整理。",
      tone: technicalTone,
    },
    {
      label: "GEO 结论",
      text: geoRecorded > 0 ? `已有 ${geoRecorded} 条 GEO 观测记录，可开始整理可见度证据。` : `还有 ${data.summary.geo_untested} 个 GEO 采样槽位未测，报告中保持待补证据。`,
      tone: geoStatusTone,
    },
    {
      label: "本周期动作",
      text: reviewTotal > 0 ? `先推进 ${reviewTotal} 个待办：高风险整改、GEO 采样和工单验收。` : "本周期暂无阻塞待办，可进入报告交付或复测观察。",
      tone: workTone,
    },
  ];

  function parseMarkets(text: string) {
    return text
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const [name, region = "", country_code = "", primary_locale = "en-US"] = line.split("|").map((item) => item.trim());
        return { name, region, country_code: country_code || name.slice(0, 2).toUpperCase(), primary_locale, status: "priority", opportunity_score: 70 };
      });
  }

  function parseKeywords(text: string) {
    return text
      .split(/[\n,，;；]+/)
      .map((line) => line.trim())
      .filter(Boolean)
      .map((theme) => ({ theme, locale: "en-US", intent: "commercial", intensity: 4 }));
  }

  function parseCompetitors(text: string) {
    return text
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const [name, website = ""] = line.split("|").map((item) => item.trim());
        return { name, website };
      });
  }

  async function saveTargets() {
    setError("");
    setNote("");
    try {
      const parsedMarkets = parseMarkets(targetForm.markets);
      const parsedKeywords = parseKeywords(targetForm.keywords);
      const parsedCompetitors = parseCompetitors(targetForm.competitors);
      if (!targetForm.site_origin.trim()) return setError("请先填写客户官网。");
      if (!parsedMarkets.length) return setError("请至少填写 1 个目标国家，例如：United States | North America | US | en-US");
      if (!parsedKeywords.length) return setError("请至少填写 1 个核心关键词。");
      const saved = await api<ProjectTargets>("/api/project-targets", {
        method: "PUT",
        body: JSON.stringify({ site_origin: targetForm.site_origin, markets: parsedMarkets, keywords: parsedKeywords, competitors: parsedCompetitors }),
      });
      setTargets(saved);
      setTargetForm({
        site_origin: saved.site_origin || targetForm.site_origin,
        markets: saved.markets.map((m) => [m.name, m.region, m.country_code, m.primary_locale].filter(Boolean).join(" | ")).join("\n"),
        keywords: saved.markets.flatMap((m) => m.demand_signals.map((s) => s.theme)).join("\n"),
        competitors: saved.markets.flatMap((m) => m.competitors.map((c) => [c.name, c.website].filter(Boolean).join(" | "))).join("\n"),
      });
      setNote(saved.note || "诊断目标已保存。");
      setData(await api<Workbench>(`/api/dashboard/workbench?days=${days}`));
    } catch (e) {
      setError(e instanceof Error ? e.message : "诊断目标保存失败");
    }
  }

  async function authorizeGsc() {
    setError("");
    setNote("");
    try {
      const res = await api<GscAuthUrl>("/api/onsite/gsc/auth-url");
      if (!res.configured || !res.auth_url) return setError(res.note || "服务器未配置 Google Search Console OAuth。");
      window.location.href = res.auth_url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "获取 GSC 授权链接失败");
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-md border border-slate-200 bg-white px-5 py-4 shadow-sm">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="brand">诊断交付总览</Badge>
              <Badge tone={data.diagnostic_status.includes("处理") ? "amber" : "green"}>{data.diagnostic_status}</Badge>
              <Badge tone={targets?.readiness === "ready" ? "green" : "amber"}>{targets?.readiness === "ready" ? "诊断目标完整" : "诊断目标待补"}</Badge>
            </div>
            <h1 className="mt-3 text-2xl font-semibold text-slate-950">{data.summary.tenant_name}</h1>
            <p className="mt-1 max-w-4xl text-sm leading-6 text-slate-500">
              面向出口企业的 SEO 与 GEO 获客诊断总览。这里汇总搜索表现、站内风险、AI 可见度和待办动作；没有接入的数据源会明确标记为未测，不用假数据填屏。
            </p>
            <div className="mt-4 grid gap-2 lg:grid-cols-3">
              {executiveSummary.map((item) => (
                <div key={item.label} className="rounded-md border border-slate-200 bg-slate-50 p-3">
                  <div className="flex items-center gap-2">
                    <span className={cn("h-2 w-2 rounded-full", toneAccent[item.tone] ?? toneAccent.default)} />
                    <span className="text-xs font-semibold text-slate-700">{item.label}</span>
                  </div>
                  <p className="mt-1 text-sm leading-5 text-slate-600">{item.text}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="grid w-full gap-2 text-sm sm:grid-cols-3 xl:w-[560px]">
            <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
              <div className="text-xs text-slate-500">主域</div>
              <div className="mt-1 truncate font-medium text-slate-900">{data.site_origin || "未登记"}</div>
            </div>
            <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
              <div className="text-xs text-slate-500">GEO 评测口径</div>
              <div className="mt-1 font-mono text-xs font-medium text-slate-900">geo-test-protocol-v1</div>
            </div>
            <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
              <div className="text-xs text-slate-500">AI 建议</div>
              <div className="mt-1 font-medium text-slate-900">{data.summary.llm_status}</div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <PillarCard
          title="SEO 技术风险"
          status={highRisk > 0 ? "需整改" : data.summary.onsite_pages > 0 ? "已审计" : "未抓取"}
          statusTone={technicalTone}
          primary={`${highRisk} 个 P0/P1`}
          helper={`${data.summary.onsite_pages} 个页面，分别检查抓取、结构、Schema、收录意愿和页面质量。`}
          href="/onsite"
          icon={SearchCheck}
        >
          <div className="grid grid-cols-3 gap-2 text-sm">
            <div className="rounded-md bg-slate-50 p-3"><div className="text-xs text-slate-500">P0</div><div className="mt-1 font-semibold">{data.summary.onsite_open_critical}</div></div>
            <div className="rounded-md bg-slate-50 p-3"><div className="text-xs text-slate-500">P1</div><div className="mt-1 font-semibold">{data.summary.onsite_open_high}</div></div>
            <div className="rounded-md bg-slate-50 p-3"><div className="text-xs text-slate-500">P2</div><div className="mt-1 font-semibold">{data.summary.onsite_open_low}</div></div>
          </div>
        </PillarCard>

        <PillarCard
          title="GEO 可见度"
          status={data.summary.geo_untested > 0 ? "存在未测" : geoRecorded > 0 ? "已有证据" : "未采样"}
          statusTone={geoStatusTone}
          primary={`${geoRecorded} 条记录`}
          helper={`${data.summary.geo_prompts} 个买家问题，${data.summary.geo_untested} 个未测。区分品牌提及、官网引用和已核验引用。`}
          href="/geo"
          icon={Globe2}
        >
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="rounded-md bg-slate-50 p-3"><div className="text-xs text-slate-500">买家问题</div><div className="mt-1 font-semibold">{data.summary.geo_prompts}</div></div>
            <div className="rounded-md bg-slate-50 p-3"><div className="text-xs text-slate-500">证据待补</div><div className="mt-1 font-semibold">{data.summary.geo_untested}</div></div>
          </div>
        </PillarCard>

        <PillarCard
          title="本周期交付"
          status={reviewTotal > 0 ? "待处理" : "清爽"}
          statusTone={workTone}
          primary={`${reviewTotal} 个待办`}
          helper={`${data.summary.geo_tickets_open} 个 GEO 工单，${data.summary.seo_pending_review} 个 SEO 待复核。`}
          href="/work-orders"
          icon={ClipboardCheck}
        >
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="rounded-md bg-slate-50 p-3"><div className="text-xs text-slate-500">GEO</div><div className="mt-1 font-semibold">{data.summary.geo_tickets_open}</div></div>
            <div className="rounded-md bg-slate-50 p-3"><div className="text-xs text-slate-500">人审</div><div className="mt-1 font-semibold">{data.summary.seo_pending_review}</div></div>
          </div>
        </PillarCard>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricTile label="曝光" value={perf.total_impressions} helper={`${perf.days} 天 GSC/Bing 数据`} icon={BarChart3} />
        <MetricTile label="点击" value={perf.total_clicks} helper={`CTR ${perf.avg_ctr ?? "-"}%`} icon={Gauge} />
        <MetricTile label="收录页面" value={perf.indexed_pages} helper={`待核验 ${perf.index_pending_pages}`} icon={CheckCircle2} />
        <MetricTile label="第三方 / 外链" value={perf.backlink_domains} helper={`未核验 ${perf.unverified_backlinks}`} icon={Link2} />
      </section>

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
                <div className="flex items-center gap-2 text-sm font-medium"><Database className="h-4 w-4 text-brand-700" />Google Search Console</div>
                <Badge tone={gsc?.connected ? "green" : gsc?.configured ? "amber" : "red"}>{gsc?.connected ? "已连接" : gsc?.configured ? "待授权" : "未配置"}</Badge>
              </div>
              <div className="mt-1 truncate text-xs text-slate-500">{gsc?.site_url || gsc?.note || "读取中"}</div>
              <div className="mt-3 flex flex-wrap gap-2">
                {gsc?.connected ? (
                  <Link href="/onsite"><Button type="button" variant="outline" size="sm">同步 GSC 数据</Button></Link>
                ) : gsc?.configured ? (
                  <Button type="button" size="sm" onClick={authorizeGsc}>打开授权页</Button>
                ) : (
                  <Link href="/onsite"><Button type="button" variant="outline" size="sm">查看配置要求</Button></Link>
                )}
              </div>
            </div>
            <div className="grid gap-2 text-sm">
              <div className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2"><span className="text-slate-600">未测项</span><span className="font-semibold">{untestedTotal}</span></div>
              <div className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2"><span className="text-slate-600">SERP 查询轮次</span><span className="font-semibold">{perf.serp_runs}</span></div>
              <div className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2"><span className="text-slate-600">GEO 资产草稿</span><span className="font-semibold">{data.summary.geo_assets_draft}</span></div>
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Target className="h-5 w-5 text-brand-700" />
              <h2 className="text-lg font-semibold text-slate-950">客户诊断目标</h2>
              <Badge tone={targets?.readiness === "ready" ? "green" : "amber"}>{targets?.readiness === "ready" ? "可开跑" : "待补"}</Badge>
            </div>
            <p className="mt-1 text-sm text-slate-500">先明确客户官网、目标国家、核心关键词和竞品，后续 SEO 抓取、SERP 查询和 GEO 问句都会按这些目标执行。</p>
          </div>
          <Button type="button" onClick={saveTargets}>保存诊断目标</Button>
        </div>
        <div className="mt-4 grid gap-3 xl:grid-cols-[1.1fr_1fr_1fr_1fr]">
          <div>
            <div className="mb-1 text-xs font-medium text-slate-500">官网</div>
            <Input value={targetForm.site_origin} onChange={(e) => setTargetForm({ ...targetForm, site_origin: e.target.value })} placeholder="https://www.example.com" />
          </div>
          <div>
            <div className="mb-1 text-xs font-medium text-slate-500">目标国家</div>
            <Textarea className="min-h-[96px]" value={targetForm.markets} onChange={(e) => setTargetForm({ ...targetForm, markets: e.target.value })} placeholder="United States | North America | US | en-US" />
          </div>
          <div>
            <div className="mb-1 text-xs font-medium text-slate-500">核心品类 / 搜索词</div>
            <Textarea className="min-h-[96px]" value={targetForm.keywords} onChange={(e) => setTargetForm({ ...targetForm, keywords: e.target.value })} placeholder="industrial pump supplier, valve manufacturer" />
          </div>
          <div>
            <div className="mb-1 text-xs font-medium text-slate-500">主要竞品</div>
            <Textarea className="min-h-[96px]" value={targetForm.competitors} onChange={(e) => setTargetForm({ ...targetForm, competitors: e.target.value })} placeholder="Competitor | https://competitor.com" />
          </div>
        </div>
        {note ? <p className="mt-3 text-sm text-emerald-700">{note}</p> : null}
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <Card className="rounded-md">
          <CardHeader><CardTitle>SEO 风险问题</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {data.seo_items.length ? data.seo_items.map((item) => <ActionRow key={item.id} item={item} />) : <EmptyState text="暂无打开的高风险 SEO 问题；未抓取页面仍显示为未测。" />}
          </CardContent>
        </Card>

        <Card className="rounded-md">
          <CardHeader><CardTitle>GEO 待验收</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {data.geo_items.length ? data.geo_items.map((item) => <ActionRow key={item.id} item={item} />) : <EmptyState text="暂无打开的 GEO 工单；买家问题或采样证据不足时会保持未测。" />}
          </CardContent>
        </Card>
      </section>

      <section className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-brand-700" />
              <h2 className="text-lg font-semibold text-slate-950">交付边界</h2>
            </div>
            <p className="mt-1 text-sm text-slate-500">客户看到可追溯的诊断结论，交付人员看到可执行的整改任务。SEM、社媒投放和自动分发仍处于延期阶段，不参与当前报告评分。</p>
          </div>
          <div className="flex rounded-md border border-slate-200 bg-slate-50 p-1">
            {[7, 28, 90].map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setDays(item)}
                className={cn("h-9 rounded px-3 text-sm font-medium", days === item ? "bg-white text-brand-700 shadow-sm" : "text-slate-500 hover:text-slate-800")}
              >
                {item}天
              </button>
            ))}
          </div>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {data.deferred_modules.map((item) => (
            <div key={item.id} className="rounded-md border border-slate-200 p-3">
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium text-slate-800">{item.title}</span>
                <Badge>{item.status}</Badge>
              </div>
              <p className="mt-1 text-xs text-slate-500">{item.subtitle}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <Link href="/geo" className="rounded-md border border-slate-200 bg-white p-4 shadow-sm transition hover:border-brand-500">
          <Globe2 className="h-5 w-5 text-brand-700" />
          <div className="mt-3 font-medium text-slate-950">检测 GEO 可见度</div>
          <p className="mt-1 text-sm text-slate-500">按品牌、品类、竞品和任务型问题分开观测，不用一个黑箱分数概括所有结果。</p>
        </Link>
        <Link href="/onsite" className="rounded-md border border-slate-200 bg-white p-4 shadow-sm transition hover:border-brand-500">
          <SearchCheck className="h-5 w-5 text-brand-700" />
          <div className="mt-3 font-medium text-slate-950">复查 SEO 高风险项</div>
          <p className="mt-1 text-sm text-slate-500">优先修 robots、noindex、JS 壳、canonical 和 Schema。</p>
        </Link>
        <Link href="/distribution" className="rounded-md border border-slate-200 bg-white p-4 shadow-sm transition hover:border-brand-500">
          <FileText className="h-5 w-5 text-brand-700" />
          <div className="mt-3 font-medium text-slate-950">生成交付报告</div>
          <p className="mt-1 text-sm text-slate-500">报告跟随总览结构，保留数据来源、抓取记录和证据索引，方便客户复核。</p>
        </Link>
      </section>
    </div>
  );
}
