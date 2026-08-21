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
import { api, type ChainFeed, type MarketDetail } from "@/lib/api";
import { countryLabel } from "@/lib/countries";

export default function MarketDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [market, setMarket] = useState<MarketDetail | null>(null);
  const [error, setError] = useState("");
  const [brief, setBrief] = useState({ summary: "", opportunities: "", risks: "", recommended_actions: "" });
  const [competitor, setCompetitor] = useState({ name: "", website: "", positioning: "" });
  const [signal, setSignal] = useState({ theme: "", locale: "", intensity: 3, intent: "informational" });
  const [settings, setSettings] = useState({ status: "watching", notes: "" });

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
        setSettings({ status: m.status, notes: m.notes ?? "" });
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
      body: JSON.stringify({ ...signal, locale: market?.primary_locale || signal.locale, source: "manual" }),
    });
    setSignal({ theme: "", locale: market?.primary_locale ?? "en-US", intensity: 3, intent: "informational" });
    load();
  }

  async function feed(signalId: string, path: string) {
    setError("");
    try {
      const res = await api<ChainFeed>(`/api/demand-signals/${signalId}/${path}`, { method: "POST" });
      router.push(res.redirect_path);
    } catch (e) {
      setError(e instanceof Error ? e.message : "生成交付任务失败");
    }
  }

  async function saveSettings(e: FormEvent) {
    e.preventDefault();
    await api(`/api/markets/${params.id}`, {
      method: "PATCH",
      body: JSON.stringify({ status: settings.status, notes: settings.notes }),
    });
    load();
  }

  if (error && !market) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-red-600">{error === "市场不存在" ? "没有这个市场。" : error}</p>
        <Link href="/insights" className="text-sm text-brand-700">返回市场列表</Link>
      </div>
    );
  }
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
          {market.region} · {countryLabel(market.country_code || market.primary_locale)} · 可转为 SEO、GEO 和站外跟进任务
        </p>
        {market.notes ? <p className="mt-2 text-sm text-slate-600">{market.notes}</p> : null}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>市场状态</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-3 md:grid-cols-3" onSubmit={saveSettings}>
            <select
              className="h-9 rounded-md border border-slate-200 px-2 text-sm"
              value={settings.status}
              onChange={(e) => setSettings({ ...settings, status: e.target.value })}
            >
              <option value="priority">优先</option>
              <option value="watching">观察</option>
              <option value="paused">暂停</option>
            </select>
            <Input
              placeholder="备注"
              value={settings.notes}
              onChange={(e) => setSettings({ ...settings, notes: e.target.value })}
            />
            <Button type="submit">保存状态</Button>
          </form>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>市场简报</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-3" onSubmit={saveBrief}>
              <div>
                <Label>市场判断</Label>
                <Textarea value={brief.summary} onChange={(e) => setBrief({ ...brief, summary: e.target.value })} />
              </div>
              <div>
                <Label>建议转化动作</Label>
                <Textarea
                  value={brief.recommended_actions}
                  onChange={(e) => setBrief({ ...brief, recommended_actions: e.target.value })}
                />
              </div>
              <div>
                <Label>风险</Label>
                <Textarea value={brief.risks} onChange={(e) => setBrief({ ...brief, risks: e.target.value })} />
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
          <CardTitle>需求信号转交付任务</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-slate-500">
            这里记录客户经理发现的买家需求、内容机会或竞品线索。它不是搜索量，也不是市场份额；选中一条后，可转成 SEO、GEO 或站外跟进任务。
          </p>
          <ul className="space-y-3">
            {market.demand_signals.map((s) => (
              <li key={s.id} className="rounded-md border border-slate-100 p-3">
                <div className="font-medium">{s.theme}</div>
                <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-500">
                  <Badge>{countryLabel(s.locale)}</Badge>
                  <Badge tone="blue">{s.intent}</Badge>
                  <span>来源 {s.source}</span>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button size="sm" onClick={() => feed(s.id, "open-onsite")}>
                    生成 SEO 任务
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => feed(s.id, "open-geo-ticket")}>
                    生成 GEO 整改项
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => feed(s.id, "open-link-followup")}>
                    生成站外跟进
                  </Button>
                </div>
              </li>
            ))}
          </ul>
          <form className="grid gap-2 md:grid-cols-4" onSubmit={addSignal}>
            <Input
              className="md:col-span-2"
              placeholder="主题 / 买家会问的原句"
              value={signal.theme}
              onChange={(e) => setSignal({ ...signal, theme: e.target.value })}
              required
            />
            <select
              className="h-9 rounded-md border border-slate-200 px-2 text-sm"
              value={signal.intent}
              onChange={(e) => setSignal({ ...signal, intent: e.target.value })}
            >
              <option value="informational">了解</option>
              <option value="commercial">比较</option>
              <option value="transactional">转化</option>
            </select>
            <Button type="submit" variant="outline">
              录入信号
            </Button>
          </form>
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
        </CardContent>
      </Card>
    </div>
  );
}
