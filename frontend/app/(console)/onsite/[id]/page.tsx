"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api, type OnsiteIssue, type SitePageDetail } from "@/lib/api";

const catLabel: Record<string, string> = {
  tdk: "TDK",
  heading: "标题",
  internal_link: "内链",
  schema: "结构化数据",
  index: "收录",
  crawl: "抓取",
};

export default function OnsiteEditorPage() {
  const params = useParams<{ id: string }>();
  const [page, setPage] = useState<SitePageDetail | null>(null);
  const [error, setError] = useState("");
  const [issueForm, setIssueForm] = useState({ category: "tdk", title: "", proposed_change: "" });

  function load() {
    api<SitePageDetail>(`/api/onsite/pages/${params.id}`).then(setPage).catch((e) => setError(e.message));
  }

  useEffect(() => {
    load();
  }, [params.id]);

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!page) return;
    await api(`/api/onsite/pages/${page.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        title: page.title,
        meta_title: page.meta_title,
        meta_description: page.meta_description,
        meta_keywords: page.meta_keywords,
        headings: page.headings,
        internal_links: page.internal_links,
        structured_data: page.structured_data,
        notes: page.notes,
      }),
    });
    load();
  }

  async function addIssue(e: FormEvent) {
    e.preventDefault();
    if (!page) return;
    await api(`/api/onsite/pages/${page.id}/issues`, { method: "POST", body: JSON.stringify(issueForm) });
    setIssueForm({ category: "tdk", title: "", proposed_change: "" });
    load();
  }

  async function applyDraft(id: string) {
    setError("");
    try {
      await api(`/api/onsite/issues/${id}/apply-draft`, { method: "POST" });
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "失败");
    }
  }

  async function confirmHigh(id: string) {
    setError("");
    try {
      await api(`/api/onsite/issues/${id}/confirm-apply`, {
        method: "POST",
        body: JSON.stringify({ confirmed: true }),
      });
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "失败");
    }
  }

  if (!page) return <p className="text-sm text-slate-500">{error || "加载中…"}</p>;

  return (
    <div className="space-y-6">
      <div>
        <Link href="/onsite" className="text-sm text-brand-700">
          ← 页面列表
        </Link>
        <h1 className="mt-2 text-2xl font-semibold">{page.title}</h1>
        <p className="text-sm text-slate-500">
          {page.path} · 收录 {page.index_status === "untested" ? "未测" : page.index_status} · 抓取{" "}
          {page.crawl_status === "untested" ? "未测" : page.crawl_status}
        </p>
      </div>

      <form className="grid gap-6 lg:grid-cols-2" onSubmit={save}>
        <Card>
          <CardHeader>
            <CardTitle>TDK</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <Label>Title</Label>
              <Input value={page.meta_title} onChange={(e) => setPage({ ...page, meta_title: e.target.value })} />
            </div>
            <div>
              <Label>Description</Label>
              <Textarea value={page.meta_description} onChange={(e) => setPage({ ...page, meta_description: e.target.value })} />
            </div>
            <div>
              <Label>Keywords</Label>
              <Input value={page.meta_keywords} onChange={(e) => setPage({ ...page, meta_keywords: e.target.value })} />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>标题 / 内链 / 结构化数据</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <Label>Headings</Label>
              <Textarea value={page.headings} onChange={(e) => setPage({ ...page, headings: e.target.value })} />
            </div>
            <div>
              <Label>内链</Label>
              <Textarea value={page.internal_links} onChange={(e) => setPage({ ...page, internal_links: e.target.value })} />
            </div>
            <div>
              <Label>结构化数据草稿</Label>
              <Textarea value={page.structured_data} onChange={(e) => setPage({ ...page, structured_data: e.target.value })} />
            </div>
            <Button type="submit">保存工作区（不改线上）</Button>
          </CardContent>
        </Card>
      </form>

      <Card>
        <CardHeader>
          <CardTitle>监测任务 · 执行分级</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {page.issues.map((i: OnsiteIssue) => (
            <div key={i.id} className="rounded-md border p-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium">{i.title}</span>
                <Badge>{catLabel[i.category] ?? i.category}</Badge>
                <Badge tone={i.risk === "high" ? "red" : "green"}>{i.risk === "high" ? "高风险" : "低风险"}</Badge>
                <Badge tone="amber">{i.metric_status === "untested" ? "指标未测" : i.metric_status}</Badge>
                <Badge tone="blue">{i.status}</Badge>
              </div>
              <p className="mt-1 text-sm text-slate-600">{i.detail}</p>
              <p className="mt-1 text-sm text-slate-500">方案：{i.proposed_change}</p>
              <div className="mt-2 flex gap-2">
                {i.risk === "low" ? (
                  <Button size="sm" variant="outline" onClick={() => applyDraft(i.id)}>
                    低风险：落工作区草稿
                  </Button>
                ) : (
                  <Button size="sm" onClick={() => confirmHigh(i.id)}>
                    高风险：我已确认（仍不自动改线上）
                  </Button>
                )}
              </div>
            </div>
          ))}
          <form className="grid gap-2 md:grid-cols-4" onSubmit={addIssue}>
            <select
              className="h-9 rounded-md border border-slate-200 px-2 text-sm"
              value={issueForm.category}
              onChange={(e) => setIssueForm({ ...issueForm, category: e.target.value })}
            >
              {Object.entries(catLabel).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
            <Input
              placeholder="问题"
              value={issueForm.title}
              onChange={(e) => setIssueForm({ ...issueForm, title: e.target.value })}
              required
            />
            <Input
              placeholder="方案"
              value={issueForm.proposed_change}
              onChange={(e) => setIssueForm({ ...issueForm, proposed_change: e.target.value })}
            />
            <Button type="submit" variant="outline">
              记一条监测
            </Button>
          </form>
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
        </CardContent>
      </Card>
    </div>
  );
}
