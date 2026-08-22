"use client";

import { FormEvent, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, type Inquiry, type Market, type SeoPage } from "@/lib/api";

const qualityLabel: Record<string, string> = {
  unreviewed: "未评",
  qualified: "合格",
  disqualified: "不合格",
};

const sourceLabel: Record<string, string> = {
  organic: "谷歌自然搜索",
  organic_en: "谷歌自然搜索",
  referral: "转介绍",
  email: "邮件",
  form: "官网表单",
  other: "其他",
};

function sourceText(value: string) {
  return sourceLabel[value] || value;
}

function thisMonthCount(rows: Inquiry[]) {
  const now = new Date();
  return rows.filter((row) => {
    if (!row.created_at) return false;
    const created = new Date(row.created_at);
    return created.getFullYear() === now.getFullYear() && created.getMonth() === now.getMonth();
  }).length;
}

export default function InquiriesPage() {
  const [rows, setRows] = useState<Inquiry[]>([]);
  const [markets, setMarkets] = useState<Market[]>([]);
  const [pages, setPages] = useState<SeoPage[]>([]);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    source: "谷歌自然搜索",
    contact: "",
    quality: "unreviewed",
    related_market_id: "",
    related_seo_page_id: "",
  });

  function load() {
    Promise.all([api<Inquiry[]>("/api/inquiries"), api<Market[]>("/api/markets"), api<SeoPage[]>("/api/seo-pages")])
      .then(([i, m, p]) => {
        setRows(i);
        setMarkets(m);
        setPages(p);
      })
      .catch((e) => setError(e.message));
  }

  useEffect(() => {
    load();
  }, []);

  async function create(e: FormEvent) {
    e.preventDefault();
    if (!form.contact.trim()) {
      setError("请填写联系人或邮箱。");
      return;
    }
    setError("");
    await api("/api/inquiries", {
      method: "POST",
      body: JSON.stringify({
        ...form,
        related_market_id: form.related_market_id || null,
        related_seo_page_id: form.related_seo_page_id || null,
      }),
    });
    setForm({ ...form, contact: "" });
    setShowForm(false);
    load();
  }

  const monthCount = thisMonthCount(rows);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">询盘</h1>
        <p className="mt-1 text-sm text-slate-500">
          这里记客户经理收到的问价，不会自动抓老外邮箱。
        </p>
      </div>

      <Card>
        <CardContent className="space-y-3 p-5">
          <div className="text-2xl font-semibold text-slate-950">这个月记到 {monthCount} 条</div>
          {rows.length === 0 ? (
            <p className="text-sm leading-6 text-slate-600">
              这个月还没记到老外询盘。软件不会自动抓邮箱，客户来问之后由客户经理登记。
            </p>
          ) : (
            rows.map((r) => (
              <div key={r.id} className="rounded-md border p-3">
                <div className="flex items-center justify-between">
                  <div className="font-medium">{r.contact}</div>
                  <Badge tone={r.quality === "qualified" ? "green" : "default"}>{qualityLabel[r.quality]}</Badge>
                </div>
                <p className="mt-1 text-xs text-slate-500">来源 {sourceText(r.source)}</p>
                {r.notes ? <p className="mt-1 text-sm text-slate-600">{r.notes}</p> : null}
              </div>
            ))
          )}
          <Button type="button" variant="outline" onClick={() => setShowForm((v) => !v)}>
            {showForm ? "收起登记" : "登记一条"}
          </Button>
        </CardContent>
      </Card>

      {showForm ? (
        <Card>
          <CardHeader>
            <CardTitle>登记询盘</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="grid gap-3 md:grid-cols-2" onSubmit={create} noValidate>
              <Input
                placeholder="联系人 / 邮箱"
                value={form.contact}
                onChange={(e) => setForm({ ...form, contact: e.target.value })}
              />
              <Input
                placeholder="来源，例如谷歌自然搜索"
                value={form.source}
                onChange={(e) => setForm({ ...form, source: e.target.value })}
              />
              <select
                className="h-9 rounded-md border border-slate-200 px-2 text-sm"
                value={form.related_market_id}
                onChange={(e) => setForm({ ...form, related_market_id: e.target.value })}
              >
                <option value="">关联市场（可选）</option>
                {markets.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
              <select
                className="h-9 rounded-md border border-slate-200 px-2 text-sm"
                value={form.related_seo_page_id}
                onChange={(e) => setForm({ ...form, related_seo_page_id: e.target.value })}
              >
                <option value="">关联选题（可选）</option>
                {pages.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.title}
                  </option>
                ))}
              </select>
              <select
                className="h-9 rounded-md border border-slate-200 px-2 text-sm"
                value={form.quality}
                onChange={(e) => setForm({ ...form, quality: e.target.value })}
              >
                {Object.entries(qualityLabel).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
              <Button type="submit">保存</Button>
            </form>
            {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
          </CardContent>
        </Card>
      ) : error ? (
        <p className="text-sm text-red-600">{error}</p>
      ) : null}
    </div>
  );
}
