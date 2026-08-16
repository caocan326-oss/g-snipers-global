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
import { api, crawlStatusLabel, type AiAssist, type FetchRegistered, type OnsiteIssue, type SitePageDetail } from "@/lib/api";

const catLabel: Record<string, string> = {
  tdk: "TDK",
  heading: "标题",
  internal_link: "内链",
  schema: "JSON-LD",
  index: "收录",
  crawl: "抓取",
  canonical: "Canonical",
  image: "图片",
  content: "内容",
  b2b: "B2B",
};

const sevLabel: Record<string, string> = { critical: "Critical", high: "High", low: "Low" };
const sevTone: Record<string, "red" | "amber" | "green"> = { critical: "red", high: "amber", low: "green" };
const statusLabel: Record<string, string> = {
  open: "已分析，待改稿",
  drafted: "已有改稿，未上线",
  draft_applied: "改稿已交付站点",
  confirmed: "已确认上线，待回抓",
  verified: "观察已验收",
  wont_fix: "不做",
};

export default function OnsiteEditorPage() {
  const params = useParams<{ id: string }>();
  const [page, setPage] = useState<SitePageDetail | null>(null);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [drafts, setDrafts] = useState<Record<string, string>>({});
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
        canonical: page.canonical,
        notes: page.notes,
      }),
    });
    load();
  }

  async function analyze() {
    if (!page) return;
    const res = await api<{ created: number; note: string; ai_status?: string }>(
      `/api/onsite/pages/${page.id}/analyze`,
      { method: "POST" }
    );
    setNote(`${res.note} 新建 ${res.created}。`);
    if (res.ai_status === "未配置") setError("AI 建议服务未配置，本次只保留抓取和规则诊断结果。");
    load();
  }

  async function fetchThis() {
    if (!page) return;
    setError("");
    try {
      const res = await api<FetchRegistered>(`/api/onsite/pages/${page.id}/fetch`, { method: "POST" });
      setNote(`${res.note} 状态 ${res.results[0]?.crawl_status ?? ""}`);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "回抓失败");
    }
  }

  async function aiIssue(id: string) {
    const res = await api<AiAssist>(`/api/onsite/issues/${id}/ai`, { method: "POST", body: JSON.stringify({ step: "all" }) });
    setNote(res.detail || res.status);
    if (res.status === "未配置") setError(res.detail);
    load();
  }

  async function addIssue(e: FormEvent) {
    e.preventDefault();
    if (!page) return;
    await api(`/api/onsite/pages/${page.id}/issues`, { method: "POST", body: JSON.stringify(issueForm) });
    setIssueForm({ category: "tdk", title: "", proposed_change: "" });
    load();
  }

  async function saveDraft(issue: OnsiteIssue) {
    const text = drafts[issue.id] ?? issue.proposed_change;
    if (!text?.trim()) {
      setError("请先填写整改方案。AI 建议只提供参考，仍需要人工确认后执行。");
      return;
    }
    await api(`/api/onsite/issues/${issue.id}/draft`, { method: "PATCH", body: JSON.stringify({ proposed_change: text }) });
    setNote("处理方案已保存，下一步交给执行人上线或进入人审。");
    load();
  }

  async function apply(issue: OnsiteIssue) {
    setError("");
    try {
      if (issue.severity === "low" && issue.risk === "low") {
        await api(`/api/onsite/issues/${issue.id}/apply-draft`, { method: "POST" });
        setNote("已标记为交付执行人。执行完成后可回抓复测。");
      } else {
        await api(`/api/onsite/issues/${issue.id}/mark-executed`, {
          method: "POST",
          body: JSON.stringify({ confirmed: true, note: "人工确认已处理，等待复测。" }),
        });
        setNote("已记录人工执行，下一步回抓复测。");
      }
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "失败");
    }
  }

  if (!page) return <p className="text-sm text-slate-500">{error || "加载中…"}</p>;

  const grouped = {
    critical: page.issues.filter((i) => i.severity === "critical"),
    high: page.issues.filter((i) => i.severity === "high"),
    low: page.issues.filter((i) => i.severity !== "critical" && i.severity !== "high"),
  };

  return (
    <div className="space-y-6">
      <div>
        <Link href="/onsite" className="text-sm text-brand-700">
          ← SEO 诊断看板
        </Link>
        <h1 className="mt-2 text-2xl font-semibold">{page.title}</h1>
        <p className="text-sm text-slate-500">
          {page.path} · 抓取 {crawlStatusLabel[page.crawl_status] ?? page.crawl_status}
          {page.http_status ? ` ${page.http_status}` : ""} ·{" "}
          {page.fetched_at ? new Date(page.fetched_at).toLocaleString("zh-CN") : "尚未抓取"}
          {page.final_url ? ` · ${page.final_url}` : ""} · 收录{" "}
          {page.index_status === "untested" ? "未测" : page.index_status}
        </p>
        <p className="mt-1 text-xs text-slate-500">
          {page.priority_hint || "P2"} · {page.page_type || "other"} · 深度 {page.url_depth ?? 0} · 来源 {page.discovery_source || "manual"} · sitemap {page.is_in_sitemap || "未测"} · 字数 {page.word_count ?? 0} · 图片缺 alt {page.images_missing_alt ?? 0}/{page.image_count ?? 0} · 外链 {page.external_link_count ?? 0}
        </p>
        {(page.meta_robots || page.x_robots_tag) ? (
          <p className="mt-1 text-xs text-slate-500">
            robots {page.meta_robots || "—"} · X-Robots {page.x_robots_tag || "—"}
          </p>
        ) : null}
        {page.crawl_error ? <p className="mt-1 text-xs text-amber-700">{page.crawl_error}</p> : null}
        <div className="mt-3 flex flex-wrap gap-2">
          <Button variant="outline" onClick={fetchThis}>
            回抓本页
          </Button>
          <Button variant="outline" onClick={analyze}>
            基于当前抓取重新诊断
          </Button>
        </div>
        {note ? <p className="mt-2 text-sm text-slate-600">{note}</p> : null}
      </div>

      {(["critical", "high", "low"] as const).map((sev) => (
        <Card key={sev}>
          <CardHeader>
            <CardTitle>
              <Badge tone={sevTone[sev]}>{sevLabel[sev]}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {grouped[sev].length === 0 ? <p className="text-sm text-slate-500">无</p> : null}
            {grouped[sev].map((i) => (
              <div key={i.id} className="rounded-md border p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium">{i.title}</span>
                  <Badge>{catLabel[i.category] ?? i.category}</Badge>
                  <Badge tone="amber">{i.metric_status === "untested" ? "未测" : i.metric_status}</Badge>
                  <Badge tone="blue">{statusLabel[i.status] ?? i.status}</Badge>
                </div>
                <p className="mt-1 text-sm text-slate-600">{i.detail}</p>
                {i.evidence ? <pre className="mt-2 whitespace-pre-wrap text-xs text-slate-500">{i.evidence}</pre> : null}
                <div className="mt-3 grid gap-2 md:grid-cols-2">
                  <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                    <div className="text-xs font-medium text-slate-500">影响</div>
                    <p className="mt-1 text-sm text-slate-700">{i.impact || "影响页面可被理解和复测。"}</p>
                  </div>
                  <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                    <div className="text-xs font-medium text-slate-500">执行角色</div>
                    <p className="mt-1 text-sm text-slate-700">{i.owner_hint || "客户经理 / 执行人"}</p>
                  </div>
                  <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                    <div className="text-xs font-medium text-slate-500">建议整改动作</div>
                    <p className="mt-1 text-sm text-slate-700">{i.recommended_action || "结合诊断证据补充处理方案，人工确认后执行。"}</p>
                  </div>
                  <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                    <div className="text-xs font-medium text-slate-500">复测方法</div>
                    <p className="mt-1 text-sm text-slate-700">{i.retest_method || "执行后重新抓取页面并比对观察层。"}</p>
                  </div>
                </div>
                <Textarea
                  className="mt-2"
                  placeholder="填写给客户技术或内容执行人的整改方案"
                  value={drafts[i.id] ?? i.proposed_change}
                  onChange={(e) => setDrafts({ ...drafts, [i.id]: e.target.value })}
                />
                <div className="mt-2 flex gap-2">
                  <Button size="sm" onClick={() => aiIssue(i.id)}>
                    生成处理建议
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => saveDraft(i)}>
                    保存整改方案
                  </Button>
                  {i.status === "confirmed" || i.status === "draft_applied" ? (
                    <Button size="sm" variant="outline" onClick={fetchThis}>
                      回抓复测
                    </Button>
                  ) : (
                    <Button size="sm" onClick={() => apply(i)}>
                      {i.severity === "low" ? "交付执行人" : "已人工上线，回抓验收"}
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      ))}

      <form className="grid gap-6 lg:grid-cols-2" onSubmit={save}>
        <Card>
          <CardHeader>
            <CardTitle>线上观察（抓取覆盖；改稿不写这里）</CardTitle>
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
              <Label>Canonical</Label>
              <Input value={page.canonical ?? ""} onChange={(e) => setPage({ ...page, canonical: e.target.value })} />
            </div>
            <p className="text-xs text-slate-500">
              html lang {page.html_lang || "—"} · viewport {page.viewport || "—"} · JSON-LD{" "}
              {page.json_ld_types || "—"}
              {page.needs_js ? " · 需要 JS" : ""}
            </p>
            {page.hreflang ? <p className="text-xs text-slate-500">hreflang {page.hreflang}</p> : null}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>标题 / 内链 / JSON-LD</CardTitle>
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
                <Button type="submit">保存观察记录</Button>
          </CardContent>
        </Card>
      </form>

      <Card>
        <CardHeader>
          <CardTitle>手工补充问题</CardTitle>
        </CardHeader>
        <CardContent>
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
              placeholder="问题标题"
              value={issueForm.title}
              onChange={(e) => setIssueForm({ ...issueForm, title: e.target.value })}
              required
            />
            <Input
              placeholder="整改方案（可后补）"
              value={issueForm.proposed_change}
              onChange={(e) => setIssueForm({ ...issueForm, proposed_change: e.target.value })}
            />
            <Button type="submit" variant="outline">
              记录问题
            </Button>
          </form>
          {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}
        </CardContent>
      </Card>
    </div>
  );
}
