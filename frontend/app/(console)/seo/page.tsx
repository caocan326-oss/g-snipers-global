"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { CountryPicker } from "@/components/CountryPicker";
import { api, type Market, type SeoPage } from "@/lib/api";
import { countryByCode, countryLabel, localeForCode } from "@/lib/countries";

const statusLabel: Record<string, string> = {
  idea: "选题",
  outline: "大纲",
  draft: "正文",
  meta: "Meta",
  review: "审核中",
  ready: "可交付",
};

const statusTone: Record<string, "default" | "blue" | "amber" | "green" | "brand"> = {
  idea: "default",
  outline: "blue",
  draft: "blue",
  meta: "amber",
  review: "amber",
  ready: "green",
};

export default function SeoListPage() {
  const [pages, setPages] = useState<SeoPage[]>([]);
  const [markets, setMarkets] = useState<Market[]>([]);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [form, setForm] = useState({ title: "", target_keyword: "", country_code: "US", market_id: "" });

  function load() {
    const q = status ? `?status=${status}` : "";
    Promise.all([api<SeoPage[]>(`/api/seo-pages${q}`), api<Market[]>("/api/markets")])
      .then(([p, m]) => {
        setPages(p);
        setMarkets(m);
      })
      .catch((e) => setError(e.message));
  }

  useEffect(() => {
    load();
  }, [status]);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    try {
      const created = await api<SeoPage>("/api/seo-pages", {
        method: "POST",
        body: JSON.stringify({
          title: form.title,
          target_keyword: form.target_keyword,
          locale: markets.find((m) => m.id === form.market_id)?.primary_locale || localeForCode(form.country_code),
          market_id: form.market_id || null,
        }),
      });
      window.location.href = `/seo/${created.id}`;
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建失败");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">SEO 内容生产</h1>
        <p className="mt-1 text-sm text-slate-500">
          面向目标市场生产 SEO 内容资产：选题、大纲、正文、Meta 和审核分步推进。这里不会自动发布到客户网站。
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {["", "idea", "outline", "draft", "meta", "review", "ready"].map((s) => (
          <Button key={s || "all"} size="sm" variant={status === s ? "default" : "outline"} onClick={() => setStatus(s)}>
            {s ? statusLabel[s] : "全部"}
          </Button>
        ))}
      </div>

      <Card>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead className="border-b bg-slate-50 text-left text-slate-500">
              <tr>
                <th className="px-5 py-3 font-medium">选题</th>
                <th className="px-5 py-3 font-medium">关键词</th>
                <th className="px-5 py-3 font-medium">国家</th>
                <th className="px-5 py-3 font-medium">状态</th>
              </tr>
            </thead>
            <tbody>
              {pages.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-5 py-8 text-center text-slate-500">
                    还没有选题。下面可以新建一条。
                  </td>
                </tr>
              ) : null}
              {pages.map((p) => (
                <tr
                  key={p.id}
                  className="cursor-pointer border-b last:border-0 hover:bg-slate-50"
                  onClick={() => {
                    window.location.href = `/seo/${p.id}`;
                  }}
                >
                  <td className="px-5 py-3">
                    <Link className="font-medium text-brand-700" href={`/seo/${p.id}`} onClick={(e) => e.stopPropagation()}>
                      {p.title}
                    </Link>
                  </td>
                  <td className="px-5 py-3 text-slate-600">{p.target_keyword}</td>
                  <td className="px-5 py-3">{countryLabel(p.locale)}</td>
                  <td className="px-5 py-3">
                    <Badge tone={statusTone[p.status]}>{statusLabel[p.status] ?? p.status}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>新建选题</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-3 md:grid-cols-2" onSubmit={onCreate}>
            <Input
              placeholder="内容标题"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              required
            />
            <Input
              placeholder="目标搜索词"
              value={form.target_keyword}
              onChange={(e) => setForm({ ...form, target_keyword: e.target.value })}
              required
            />
            <div className="md:col-span-2">
              <div className="mb-1 text-xs text-slate-500">这篇按哪个国家写</div>
              <CountryPicker
                value={form.country_code}
                onChange={(country_code) => {
                  const match = markets.find((m) => m.country_code.toUpperCase() === country_code);
                  setForm({ ...form, country_code, market_id: match?.id || "" });
                }}
              />
            </div>
            {markets.length ? (
              <select
                className="h-9 rounded-md border border-slate-200 px-2 text-sm"
                value={form.market_id}
                onChange={(e) => {
                  const market = markets.find((m) => m.id === e.target.value);
                  setForm({
                    ...form,
                    market_id: e.target.value,
                    country_code: market?.country_code.toUpperCase() || form.country_code,
                  });
                }}
              >
                <option value="">不绑定已有市场，只按上面的国家</option>
                {markets.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                    {countryByCode(m.country_code) ? "" : ` · ${m.country_code}`}
                  </option>
                ))}
              </select>
            ) : null}
            <Button type="submit">创建并编辑</Button>
          </form>
          {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
        </CardContent>
      </Card>
    </div>
  );
}
