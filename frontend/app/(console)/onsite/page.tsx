"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, type SitePage } from "@/lib/api";

export default function OnsiteListPage() {
  const [pages, setPages] = useState<SitePage[]>([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ path: "/", locale: "en-US", title: "" });

  function load() {
    api<SitePage[]>("/api/onsite/pages").then(setPages).catch((e) => setError(e.message));
  }

  useEffect(() => {
    load();
  }, []);

  async function create(e: FormEvent) {
    e.preventDefault();
    const created = await api<SitePage>("/api/onsite/pages", { method: "POST", body: JSON.stringify(form) });
    window.location.href = `/onsite/${created.id}`;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">站内优化</h1>
        <p className="mt-1 text-sm text-slate-500">
          监测 TDK / 标题 / 内链 / 结构化数据 / 收录与抓取。低风险可在工作区落草稿；高风险（改线上 HTML、noindex、robots）必须人工确认。收录未接 GSC，显示未测，不填 0 页。
        </p>
      </div>
      <Card>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead className="border-b bg-slate-50 text-left text-slate-500">
              <tr>
                <th className="px-5 py-3 font-medium">页面</th>
                <th className="px-5 py-3 font-medium">语言</th>
                <th className="px-5 py-3 font-medium">收录</th>
                <th className="px-5 py-3 font-medium">抓取</th>
                <th className="px-5 py-3 font-medium">待办</th>
              </tr>
            </thead>
            <tbody>
              {pages.map((p) => (
                <tr key={p.id} className="border-b last:border-0">
                  <td className="px-5 py-3">
                    <Link className="font-medium text-brand-700" href={`/onsite/${p.id}`}>
                      {p.title}
                    </Link>
                    <div className="text-xs text-slate-400">{p.path}</div>
                  </td>
                  <td className="px-5 py-3">{p.locale}</td>
                  <td className="px-5 py-3">
                    <Badge tone="amber">{p.index_status === "untested" ? "未测" : p.index_status}</Badge>
                  </td>
                  <td className="px-5 py-3">
                    <Badge tone="amber">{p.crawl_status === "untested" ? "未测" : p.crawl_status}</Badge>
                  </td>
                  <td className="px-5 py-3">{p.open_issue_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>登记演示页</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-3 md:grid-cols-4" onSubmit={create}>
            <Input placeholder="路径" value={form.path} onChange={(e) => setForm({ ...form, path: e.target.value })} required />
            <Input placeholder="语言" value={form.locale} onChange={(e) => setForm({ ...form, locale: e.target.value })} />
            <Input placeholder="标题" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
            <Button type="submit">进入工作台</Button>
          </form>
          {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
        </CardContent>
      </Card>
    </div>
  );
}
