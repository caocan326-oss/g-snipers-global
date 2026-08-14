"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api, type MarketDetail, type SeoPage } from "@/lib/api";

export default function MarketDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [market, setMarket] = useState<MarketDetail | null>(null);
  const [error, setError] = useState("");
  const [brief, setBrief] = useState({ summary: "", opportunities: "", risks: "", recommended_actions: "" });
  const [competitor, setCompetitor] = useState({ name: "", website: "", positioning: "" });
  const [signal, setSignal] = useState({ theme: "", locale: "", intensity: 3, intent: "informational" });

  function load() {
    api<MarketDetail>(`/api/markets/${params.id}`)
      .then((m) => {
        setMarket(m);
        setBrief({
          summary: m.brief?.summary ?? "",
          opportunities: m.brief?.opportunities ?? "",
          risks: m.brief?.risks ?? "",
          recommended_actions: m.brief?.recommended_actions ?? "",
        });
        setSignal((s) => ({ ...s, locale: m.primary_locale }));
      })
      .catch((e) => setError(e.message));
  }

  useEffect(() => {
    load();
  }, [params.id]);

  async function saveBrief(e: FormEvent) {
    e.preventDefault();
    await api(`/api/markets/${params.id}/brief`, { method: "PUT", body: JSON.stringify(brief) });
    load();
  }

  async function addCompetitor(e: FormEvent) {
    e.preventDefault();
    await api(`/api/markets/${params.id}/competitors`, { method: "POST", body: JSON.stringify(competitor) });
    setCompetitor({ name: "", website: "", positioning: "" });
    load();
  }

  async function addSignal(e: FormEvent) {
    e.preventDefault();
    await api(`/api/markets/${params.id}/demand-signals`, {
      method: "POST",
      body: JSON.stringify({ ...signal, source: "manual" }),
    });
    setSignal({ theme: "", locale: market?.primary_locale ?? "en-US", intensity: 3, intent: "informational" });
    load();
  }

  async function toSeo(signalId: string) {
    const page = await api<SeoPage>(`/api/demand-signals/${signalId}/create-seo-page`, { method: "POST" });
    router.push(`/seo/${page.id}`);
  }

  if (error) return <p className="text-red-600">{error}</p>;
  if (!market) return <p className="text-sm text-slate-500">加载中…</p>;

  return (
    <div className="space-y-6">
      <div>
        <Link href="/insights" className="text-sm text-brand-700">
          ← 全部市场
        </Link>
        <h1 className="mt-2 text-2xl font-semibold">
          {market.name}{" "}
          <span className="text-base font-normal text-slate-400">{market.country_code}</span>
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          {market.region} · {market.primary_locale} · 机会分 {market.opportunity_score}
        </p>
        {market.notes ? <p className="mt-2 text-sm text-slate-600">{market.notes}</p> : null}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>市场简报</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-3" onSubmit={saveBrief}>
              <div>
                <Label>判断</Label>
                <Textarea value={brief.summary} onChange={(e) => setBrief({ ...brief, summary: e.target.value })} />
              </div>
              <div>
                <Label>机会</Label>
                <Textarea
                  value={brief.opportunities}
                  onChange={(e) => setBrief({ ...brief, opportunities: e.target.value })}
                />
              </div>
              <div>
                <Label>风险</Label>
                <Textarea value={brief.risks} onChange={(e) => setBrief({ ...brief, risks: e.target.value })} />
              </div>
              <div>
                <Label>建议动作</Label>
                <Textarea
                  value={brief.recommended_actions}
                  onChange={(e) => setBrief({ ...brief, recommended_actions: e.target.value })}
                />
              </div>
              <Button type="submit">保存简报</Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>竞品</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <ul className="space-y-3">
              {market.competitors.map((c) => (
                <li key={c.id} className="rounded-md border border-slate-100 p-3">
                  <div className="font-medium">{c.name}</div>
                  {c.website ? (
                    <a className="text-xs text-brand-700" href={c.website} target="_blank" rel="noreferrer">
                      {c.website}
                    </a>
                  ) : null}
                  <p className="mt-1 text-sm text-slate-600">{c.positioning}</p>
                </li>
              ))}
            </ul>
            <form className="space-y-2" onSubmit={addCompetitor}>
              <Input
                placeholder="名称"
                value={competitor.name}
                onChange={(e) => setCompetitor({ ...competitor, name: e.target.value })}
                required
              />
              <Input
                placeholder="网站"
                value={competitor.website}
                onChange={(e) => setCompetitor({ ...competitor, website: e.target.value })}
              />
              <Input
                placeholder="定位"
                value={competitor.positioning}
                onChange={(e) => setCompetitor({ ...competitor, positioning: e.target.value })}
              />
              <Button type="submit" variant="outline">
                添加竞品
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>需求信号 → SEO 选题</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-slate-500">
            信号由客户经理录入（访谈、公开资料、后续可接真实数据源）。不是实时搜索量，也不是 Share of Voice。
          </p>
          <ul className="space-y-3">
            {market.demand_signals.map((s) => (
              <li key={s.id} className="flex items-start justify-between gap-4 rounded-md border border-slate-100 p-3">
                <div>
                  <div className="font-medium">{s.theme}</div>
                  <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-500">
                    <Badge>{s.locale}</Badge>
                    <Badge tone="amber">强度 {s.intensity}</Badge>
                    <Badge tone="blue">{s.intent}</Badge>
                    <span>来源 {s.source}</span>
                  </div>
                </div>
                <Button size="sm" onClick={() => toSeo(s.id)}>
                  开选题
                </Button>
              </li>
            ))}
          </ul>
          <form className="grid gap-2 md:grid-cols-4" onSubmit={addSignal}>
            <Input
              className="md:col-span-2"
              placeholder="主题 / 关键词"
              value={signal.theme}
              onChange={(e) => setSignal({ ...signal, theme: e.target.value })}
              required
            />
            <Input
              placeholder="语言"
              value={signal.locale}
              onChange={(e) => setSignal({ ...signal, locale: e.target.value })}
            />
            <Button type="submit" variant="outline">
              录入信号
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
