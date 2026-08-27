"use client";

import { FormEvent, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, type GeoPrompt, type Inquiry, type Market, type SeoPage } from "@/lib/api";

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
  const [prompts, setPrompts] = useState<GeoPrompt[]>([]);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [attachById, setAttachById] = useState<Record<string, string>>({});
  const [form, setForm] = useState({
    source: "谷歌自然搜索",
    contact: "",
    quality: "unreviewed",
    related_market_id: "",
    related_seo_page_id: "",
    related_prompt_id: "",
    notes: "",
  });

  function load() {
    Promise.all([
      api<Inquiry[]>("/api/inquiries"),
      api<Market[]>("/api/markets"),
      api<SeoPage[]>("/api/seo-pages"),
      api<GeoPrompt[]>("/api/geo/prompts"),
    ])
      .then(([i, m, p, q]) => {
        setRows(i);
        setMarkets(m);
        setPages(p);
        setPrompts(q);
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
    setNote("");
    await api("/api/inquiries", {
      method: "POST",
      body: JSON.stringify({
        ...form,
        related_market_id: form.related_market_id || null,
        related_seo_page_id: form.related_seo_page_id || null,
        related_prompt_id: form.related_prompt_id || null,
        notes: form.notes.trim() || null,
      }),
    });
    setForm({ ...form, contact: "", related_prompt_id: "", notes: "" });
    setShowForm(false);
    load();
  }

  async function attachPrompt(inquiryId: string) {
    const promptId = (attachById[inquiryId] || "").trim();
    if (!promptId) {
      setError("请先选一句已记问句。");
      return;
    }
    setError("");
    setNote("");
    await api(`/api/inquiries/${inquiryId}`, {
      method: "PATCH",
      body: JSON.stringify({ related_prompt_id: promptId }),
    });
    setNote("已挂上这句。挂上不是证明 AI 提到了我们。");
    load();
  }

  const monthCount = thisMonthCount(rows);
  const linkedCount = rows.filter((row) => row.related_prompt_text).length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">询盘</h1>
        <p className="mt-1 text-sm text-slate-500">
          这里记客户经理收到的问价，不会自动抓老外邮箱。可以挂上已记的买家问句；挂上不是证明 AI 提到了我们。
        </p>
      </div>

      <Card>
        <CardContent className="space-y-3 p-5">
          <div className="text-2xl font-semibold text-slate-950">这个月记到 {monthCount} 条</div>
          {linkedCount ? (
            <p className="text-sm text-slate-600">其中 {linkedCount} 条挂了已记问句。</p>
          ) : rows.length ? (
            <p className="text-sm text-slate-600">还没挂问句。没有原句就空着，不要编。</p>
          ) : null}
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
                {r.related_prompt_text ? (
                  <p className="mt-1 text-sm text-slate-700">挂了问句：{r.related_prompt_text}</p>
                ) : prompts.length ? (
                  <div className="mt-2 flex flex-col gap-2 sm:flex-row">
                    <select
                      className="h-9 min-w-0 flex-1 rounded-md border border-slate-200 px-2 text-sm"
                      value={attachById[r.id] || ""}
                      onChange={(e) => setAttachById({ ...attachById, [r.id]: e.target.value })}
                    >
                      <option value="">挂上已记问句（可选）</option>
                      {prompts.map((prompt) => (
                        <option key={prompt.id} value={prompt.id}>
                          {prompt.prompt_text}
                        </option>
                      ))}
                    </select>
                    <Button type="button" size="sm" variant="outline" onClick={() => void attachPrompt(r.id)}>
                      挂上这句
                    </Button>
                  </div>
                ) : (
                  <p className="mt-1 text-xs text-slate-500">还没有买家原句。不要编。先去 AI 搜索可见度手录一句。</p>
                )}
                {r.notes ? <p className="mt-1 text-sm text-slate-600">{r.notes}</p> : null}
              </div>
            ))
          )}
          <Button type="button" variant="outline" onClick={() => setShowForm((v) => !v)}>
            {showForm ? "收起登记" : "登记一条"}
          </Button>
          {note ? <p className="text-sm text-emerald-700">{note}</p> : null}
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
                className="h-9 rounded-md border border-slate-200 px-2 text-sm md:col-span-2"
                value={form.related_prompt_id}
                onChange={(e) => setForm({ ...form, related_prompt_id: e.target.value })}
              >
                <option value="">{prompts.length ? "挂上已记问句（可选）" : "还没有买家原句，不要编"}</option>
                {prompts.map((prompt) => (
                  <option key={prompt.id} value={prompt.id}>
                    {prompt.prompt_text}
                  </option>
                ))}
              </select>
              <Input
                className="md:col-span-2"
                placeholder="备注（可选）"
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
              />
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
            <p className="mt-3 text-xs leading-5 text-slate-500">挂上问句只表示经理认为对得上。不是 AI 提到了我们。</p>
            {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
          </CardContent>
        </Card>
      ) : error ? (
        <p className="text-sm text-red-600">{error}</p>
      ) : null}
    </div>
  );
}
