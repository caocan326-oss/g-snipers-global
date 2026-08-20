"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, type Market, type SeoPage } from "@/lib/api";

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
  const [form, setForm] = useState({ title: "", target_keyword: "", locale: "en-US", market_id: "" });

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
          ...form,
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
                <th className="px-5 py-3 font-medium">语言</th>
                <th className="px-5 py-3 font-medium">状态</th>
              </tr>
            </thead>
            <tbody>
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
                  <td className="px-5 py-3">{p.locale}</td>
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
          <form className="grid gap-3 md:grid-cols-5" onSubmit={onCreate}>
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
            <Input
              placeholder="语言，例如 en-US"
              value={form.locale}
              onChange={(e) => setForm({ ...form, locale: e.target.value })}
            />
            <select
              className="h-9 rounded-md border border-slate-200 px-2 text-sm"
              value={form.market_id}
              onChange={(e) => setForm({ ...form, market_id: e.target.value })}
            >
              <option value="">暂不绑定市场</option>
              {markets.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name}
                </option>
              ))}
            </select>
            <Button type="submit">创建并编辑</Button>
          </form>
          {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
        </CardContent>
      </Card>
    </div>
  );
}
