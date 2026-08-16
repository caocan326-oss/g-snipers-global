"use client";

import Link from "next/link";
import { AlertTriangle, ArrowRight, BarChart3, CheckCircle2, ClipboardCheck, Gauge, Link2, SearchCheck, Target, Timer } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api, type GscAuthUrl, type GscStatus, type ProjectTargets, type Workbench, type WorkbenchChain, type WorkbenchItem } from "@/lib/api";
import { cn } from "@/lib/utils";

const toneBorder: Record<string, string> = {
  default: "border-slate-200",
  green: "border-emerald-200",
  amber: "border-amber-200",
  blue: "border-sky-200",
  red: "border-red-200",
  brand: "border-brand-200",
};

const toneText: Record<string, string> = {
  default: "text-slate-700",
  green: "text-emerald-700",
  amber: "text-amber-700",
  blue: "text-sky-700",
  red: "text-red-700",
  brand: "text-brand-700",
};

function EmptyState({ text }: { text: string }) {
  return <p className="rounded-md border border-dashed border-slate-200 px-3 py-4 text-sm text-slate-500">{text}</p>;
}

function ActionRow({ item }: { item: WorkbenchItem }) {
  return (
    <Link
      href={item.href}
      className={cn(
        "block rounded-md border bg-white p-4 transition hover:border-brand-400 hover:shadow-sm",
        toneBorder[item.tone] ?? toneBorder.default
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-medium text-slate-900">{item.title}</h3>
            {item.status ? <Badge tone={item.tone}>{item.status}</Badge> : null}
          </div>
          <p className="mt-1 line-clamp-2 text-sm text-slate-500">{item.subtitle}</p>
          {item.meta ? <p className="mt-2 text-xs text-slate-400">{item.meta}</p> : null}
        </div>
        <span className="shrink-0 text-xs font-medium text-brand-700">{item.action_label}</span>
      </div>
    </Link>
  );
}

function ChainCard({ chain }: { chain: WorkbenchChain }) {
  return (
    <Link href={chain.href}>
      <Card className={cn("h-full rounded-md transition hover:border-brand-500", toneBorder[chain.tone] ?? toneBorder.default)}>
        <CardHeader className="space-y-2">
          <div className="flex items-center justify-between gap-3">
            <CardTitle className="text-base">{chain.title}</CardTitle>
            <Badge tone={chain.tone}>{chain.health}</Badge>
          </div>
          <p className="text-xs text-slate-500">{chain.secondary}</p>
        </CardHeader>
        <CardContent>
          <div className={cn("text-3xl font-semibold", toneText[chain.tone] ?? toneText.default)}>{chain.primary}</div>
          <div className="mt-3 flex items-center gap-1 text-sm font-medium text-brand-700">
            {chain.action_label}
            <ArrowRight className="h-4 w-4" />
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

export default function HomePage() {
  const [data, setData] = useState<Workbench | null>(null);
  const [targets, setTargets] = useState<ProjectTargets | null>(null);
  const [gsc, setGsc] = useState<GscStatus | null>(null);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [days, setDays] = useState(28);
  const [targetForm, setTargetForm] = useState({
    site_origin: "",
    markets: "",
    keywords: "",
    competitors: "",
  });

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
          markets: res.markets
            .map((m) => [m.name, m.region, m.country_code, m.primary_locale].filter(Boolean).join(" | "))
            .join("\n"),
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
    return (
      data.summary.onsite_open_critical +
      data.summary.onsite_open_high +
      data.summary.geo_tickets_open +
      data.summary.seo_pending_review
    );
  }, [data]);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!data) return <p className="text-sm text-slate-500">加载中…</p>;

  const untestedTotal = data.summary.geo_untested + (data.summary.onsite_pages === 0 ? 1 : 0);
  const perf = data.seo_performance;

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
      .split("\n")
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
      const saved = await api<ProjectTargets>("/api/project-targets", {
        method: "PUT",
        body: JSON.stringify({
          site_origin: targetForm.site_origin,
          markets: parseMarkets(targetForm.markets),
          keywords: parseKeywords(targetForm.keywords),
          competitors: parseCompetitors(targetForm.competitors),
        }),
      });
      setTargets(saved);
      setNote(saved.note || "测试目标已保存。");
      const refreshed = await api<Workbench>(`/api/dashboard/workbench?days=${days}`);
      setData(refreshed);
    } catch (e) {
      setError(e instanceof Error ? e.message : "测试目标保存失败");
    }
  }

  async function authorizeGsc() {
    setError("");
    setNote("");
    try {
      const res = await api<GscAuthUrl>("/api/onsite/gsc/auth-url");
      if (!res.configured || !res.auth_url) {
        setError(res.note || "服务器未配置 Google Search Console OAuth。");
        return;
      }
      window.location.href = res.auth_url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "获取 GSC 授权链接失败");
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-md border border-slate-200 bg-white px-6 py-5 shadow-sm">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="brand">海外获客诊断工作台</Badge>
              <Badge tone={data.diagnostic_status.includes("处理") ? "amber" : "green"}>{data.diagnostic_status}</Badge>
            </div>
            <h1 className="mt-3 text-2xl font-semibold text-slate-950">G-Snipers Global</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
              {data.summary.tenant_name} · 当前聚焦 SEO + GEO 诊断闭环。没有数据源就保持未测，高风险改动进入人审确认。
            </p>
          </div>
          <div className="grid min-w-[280px] grid-cols-2 gap-3 text-sm">
            <div className="rounded-md border border-slate-200 p-3">
              <div className="text-xs text-slate-500">官网</div>
              <div className="mt-1 truncate font-medium">{data.site_origin || "未登记"}</div>
            </div>
            <div className="rounded-md border border-slate-200 p-3">
              <div className="text-xs text-slate-500">LLM</div>
              <div className="mt-1 font-medium">{data.summary.llm_status}</div>
            </div>
          </div>
        </div>
      </section>

      <section className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={targets?.readiness === "ready" ? "green" : "amber"}>{targets?.readiness === "ready" ? "目标已就绪" : "待补目标"}</Badge>
              <Badge tone="blue">{targets?.target_market_count ?? 0} 个国家</Badge>
              <Badge tone="brand">{targets?.keyword_count ?? 0} 个关键词</Badge>
              <Badge>{targets?.competitor_count ?? 0} 个竞品</Badge>
            </div>
            <h2 className="mt-3 flex items-center gap-2 text-xl font-semibold text-slate-950">
              <Target className="h-5 w-5 text-brand-700" />
              客户测试目标
            </h2>
          </div>
          <Button type="button" onClick={saveTargets}>保存测试目标</Button>
        </div>
        <div className="mt-4 grid gap-3 xl:grid-cols-[1.1fr_1fr_1fr_1fr]">
          <div>
            <div className="mb-1 text-xs font-medium text-slate-500">官网</div>
            <Input value={targetForm.site_origin} onChange={(e) => setTargetForm({ ...targetForm, site_origin: e.target.value })} placeholder="https://www.example.com" />
          </div>
          <div>
            <div className="mb-1 text-xs font-medium text-slate-500">目标国家</div>
            <Textarea
              className="min-h-[96px]"
              value={targetForm.markets}
              onChange={(e) => setTargetForm({ ...targetForm, markets: e.target.value })}
              placeholder="United States | North America | US | en-US"
            />
          </div>
          <div>
            <div className="mb-1 text-xs font-medium text-slate-500">核心关键词</div>
            <Textarea
              className="min-h-[96px]"
              value={targetForm.keywords}
              onChange={(e) => setTargetForm({ ...targetForm, keywords: e.target.value })}
              placeholder="industrial pump supplier"
            />
          </div>
          <div>
            <div className="mb-1 text-xs font-medium text-slate-500">主要竞品</div>
            <Textarea
              className="min-h-[96px]"
              value={targetForm.competitors}
              onChange={(e) => setTargetForm({ ...targetForm, competitors: e.target.value })}
              placeholder="Competitor | https://competitor.com"
            />
          </div>
        </div>
        {note ? <p className="mt-3 text-sm text-emerald-700">{note}</p> : null}
      </section>

      <section className="rounded-md border border-brand-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="brand">SEO 表现</Badge>
              <Badge tone={perf.data_status === "已导入" ? "green" : "amber"}>{perf.data_status}</Badge>
              <Badge tone={perf.pagespeed_status === "已测速" ? "green" : "amber"}>{perf.pagespeed_status}</Badge>
            </div>
            <h2 className="mt-3 text-xl font-semibold text-slate-950">客户官网搜索表现总览</h2>
            <p className="mt-1 text-sm text-slate-500">
              按所选时间范围查看曝光、点击、CTR、平均排名、收录核验、外链核验和页面速度。
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-slate-500">GSC</span>
                <Badge tone={gsc?.connected ? "green" : gsc?.configured ? "amber" : "red"}>
                  {gsc?.connected ? "已连接" : gsc?.configured ? "待客户授权" : "未配置"}
                </Badge>
              </div>
              <div className="mt-1 max-w-[260px] truncate text-xs text-slate-500">{gsc?.site_url || gsc?.note || "读取中"}</div>
            </div>
            {gsc?.connected ? (
              <Link href="/onsite">
                <Button type="button" variant="outline">同步 GSC 数据</Button>
              </Link>
            ) : (
              <Button type="button" onClick={authorizeGsc} disabled={!gsc?.configured}>
                连接 Google Search Console
              </Button>
            )}
            <div className="flex rounded-md border border-slate-200 bg-slate-50 p-1">
              {[7, 28, 90].map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => setDays(item)}
                  className={cn(
                    "h-9 rounded px-3 text-sm font-medium",
                    days === item ? "bg-white text-brand-700 shadow-sm" : "text-slate-500 hover:text-slate-800"
                  )}
                >
                  {item}天
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-6">
          <div className="rounded-md border border-slate-200 p-4">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <BarChart3 className="h-4 w-4" />
              曝光
            </div>
            <div className="mt-2 text-2xl font-semibold text-slate-950">{perf.total_impressions}</div>
          </div>
          <div className="rounded-md border border-slate-200 p-4">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <SearchCheck className="h-4 w-4" />
              点击
            </div>
            <div className="mt-2 text-2xl font-semibold text-slate-950">{perf.total_clicks}</div>
          </div>
          <div className="rounded-md border border-slate-200 p-4">
            <div className="text-xs text-slate-500">CTR</div>
            <div className="mt-2 text-2xl font-semibold text-slate-950">{perf.avg_ctr ?? "-"}</div>
            <div className="text-xs text-slate-400">%</div>
          </div>
          <div className="rounded-md border border-slate-200 p-4">
            <div className="text-xs text-slate-500">平均排名</div>
            <div className="mt-2 text-2xl font-semibold text-slate-950">{perf.avg_position ?? "-"}</div>
          </div>
          <div className="rounded-md border border-slate-200 p-4">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Timer className="h-4 w-4" />
              页面速度
            </div>
            <div className="mt-2 text-2xl font-semibold text-slate-950">{perf.latest_speed_score ?? "-"}</div>
          </div>
          <div className="rounded-md border border-slate-200 p-4">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Link2 className="h-4 w-4" />
              外链域名
            </div>
            <div className="mt-2 text-2xl font-semibold text-slate-950">{perf.backlink_domains}</div>
            <div className="text-xs text-slate-400">未核验 {perf.unverified_backlinks}</div>
          </div>
        </div>

        <div className="mt-5 grid gap-4 lg:grid-cols-3">
          <div className="rounded-md border border-slate-200 p-4">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-sm font-medium text-slate-900">关键词表现</h3>
              <Badge tone="blue">{perf.days}天</Badge>
            </div>
            <div className="mt-3 space-y-2">
              {perf.top_keywords.length ? (
                perf.top_keywords.map((item) => (
                  <div key={item.key} className="grid grid-cols-[1fr_auto] gap-3 text-sm">
                    <span className="truncate text-slate-700">{item.key}</span>
                    <span className="text-xs text-slate-500">曝光 {item.impressions} · 点击 {item.clicks} · 排名 {item.position ?? "-"}</span>
                  </div>
                ))
              ) : (
                <EmptyState text="导入 GSC/Bing CSV 后显示关键词表现。" />
              )}
            </div>
          </div>
          <div className="rounded-md border border-slate-200 p-4">
            <h3 className="text-sm font-medium text-slate-900">国家 / 地区表现</h3>
            <div className="mt-3 space-y-2">
              {perf.top_countries.length ? (
                perf.top_countries.map((item) => (
                  <div key={item.key} className="flex items-center justify-between gap-3 text-sm">
                    <span className="truncate text-slate-700">{item.key}</span>
                    <span className="text-xs text-slate-500">曝光 {item.impressions} / 点击 {item.clicks}</span>
                  </div>
                ))
              ) : (
                <EmptyState text="导入带国家维度的搜索表现数据后显示。" />
              )}
            </div>
          </div>
          <div className="rounded-md border border-slate-200 p-4">
            <h3 className="text-sm font-medium text-slate-900">收录 / 权重 / 外链</h3>
            <div className="mt-3 grid gap-2 text-sm text-slate-600">
              <div className="flex items-center justify-between gap-3">
                <span>已确认收录页面</span>
                <span className="font-medium text-slate-900">{perf.indexed_pages}</span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span>待 GSC 核验页面</span>
                <span className="font-medium text-slate-900">{perf.index_pending_pages}</span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span>权重 / Authority</span>
                <Badge tone="amber">{perf.authority_status}</Badge>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span>外链未核验</span>
                <span className="font-medium text-slate-900">{perf.unverified_backlinks}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-4">
        <Card className="rounded-md">
          <CardContent className="flex items-center gap-3 py-4">
            <SearchCheck className="h-5 w-5 text-brand-700" />
            <div>
              <div className="text-2xl font-semibold">{data.summary.onsite_pages}</div>
              <div className="text-xs text-slate-500">已登记页面</div>
            </div>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="flex items-center gap-3 py-4">
            <AlertTriangle className="h-5 w-5 text-red-600" />
            <div>
              <div className="text-2xl font-semibold">{data.summary.onsite_open_critical + data.summary.onsite_open_high}</div>
              <div className="text-xs text-slate-500">高风险 SEO 问题</div>
            </div>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="flex items-center gap-3 py-4">
            <Gauge className="h-5 w-5 text-amber-600" />
            <div>
              <div className="text-2xl font-semibold">{untestedTotal}</div>
              <div className="text-xs text-slate-500">未测项</div>
            </div>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="flex items-center gap-3 py-4">
            <ClipboardCheck className="h-5 w-5 text-sky-700" />
            <div>
              <div className="text-2xl font-semibold">{reviewTotal}</div>
              <div className="text-xs text-slate-500">待人审动作</div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {data.chains.map((chain) => (
          <ChainCard key={chain.key} chain={chain} />
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="rounded-md">
          <CardHeader>
            <div className="flex items-center justify-between gap-3">
              <CardTitle>下一步动作</CardTitle>
              <Badge tone="amber">按风险排序</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.next_actions.length ? (
              data.next_actions.map((item) => <ActionRow key={item.id} item={item} />)
            ) : (
              <EmptyState text="暂无待处理动作。" />
            )}
          </CardContent>
        </Card>

        <Card className="rounded-md">
          <CardHeader>
            <div className="flex items-center justify-between gap-3">
              <CardTitle>诊断边界</CardTitle>
              <CheckCircle2 className="h-5 w-5 text-emerald-600" />
            </div>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-600">
            <p>当前只推进官网 SEO 诊断、GEO 采样与验收工单。</p>
            <p>SEM、新媒体、真实分发、GSC、广告账户接入和线索归因暂缓，不用占位数据补齐看板。</p>
            <div className="grid gap-2 pt-1">
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
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="rounded-md">
          <CardHeader>
            <CardTitle>SEO 风险问题</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.seo_items.length ? (
              data.seo_items.map((item) => <ActionRow key={item.id} item={item} />)
            ) : (
              <EmptyState text="暂无打开的高风险 SEO 问题；未抓取页面仍显示为未测。" />
            )}
          </CardContent>
        </Card>

        <Card className="rounded-md">
          <CardHeader>
            <CardTitle>GEO 待验收</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.geo_items.length ? (
              data.geo_items.map((item) => <ActionRow key={item.id} item={item} />)
            ) : (
              <EmptyState text="暂无打开的 GEO 工单；问句或采样槽位不足时保持未测。" />
            )}
          </CardContent>
        </Card>
      </div>

    </div>
  );
}
