"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  api,
  crawlStatusLabel,
  type AiAssist,
  type ContentBrief,
  type FetchRegistered,
  type OnsiteBoard,
  type OnsiteIssue,
  type SitePage,
} from "@/lib/api";

const catLabel: Record<string, string> = {
  tdk: "TDK",
  heading: "标题",
  internal_link: "内链",
  schema: "JSON-LD",
  index: "收录",
  crawl: "抓取",
  canonical: "Canonical",
};

const sevLabel: Record<string, string> = { critical: "Critical", high: "High", low: "Low" };
const sevTone: Record<string, "red" | "amber" | "green"> = { critical: "red", high: "amber", low: "green" };
const statusLabel: Record<string, string> = {
  open: "已分析，待改稿",
  drafted: "已有改稿，未上线",
  draft_applied: "改稿已交付站点",
  confirmed: "已确认上线，待回抓",
  verified: "观察已验收",
};

export default function OnsiteBoardPage() {
  const [board, setBoard] = useState<OnsiteBoard | null>(null);
  const [pages, setPages] = useState<SitePage[]>([]);
  const [briefs, setBriefs] = useState<ContentBrief[]>([]);
  const [filter, setFilter] = useState<"critical" | "high" | "low" | "all">("all");
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [form, setForm] = useState({ path: "/", locale: "en-US", title: "" });
  const [origin, setOrigin] = useState("");

  function load() {
    Promise.all([
      api<OnsiteBoard>("/api/onsite/board"),
      api<SitePage[]>("/api/onsite/pages"),
      api<ContentBrief[]>("/api/onsite/briefs"),
      api<{ site_origin: string }>("/api/onsite/settings"),
    ])
      .then(([b, p, br, s]) => {
        setBoard(b);
        setPages(p);
        setBriefs(br);
        setOrigin(s.site_origin || "");
      })
      .catch((e) => setError(e.message));
  }

  useEffect(() => {
    load();
  }, []);

  async function saveOrigin() {
    setError("");
    try {
      const res = await api<{ site_origin: string }>("/api/onsite/settings", {
        method: "PATCH",
        body: JSON.stringify({ site_origin: origin }),
      });
      setOrigin(res.site_origin);
      setNote(`已保存站点 origin：${res.site_origin}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存 origin 失败");
    }
  }

  async function fetchSite() {
    setError("");
    try {
      const res = await api<FetchRegistered>("/api/onsite/fetch-registered", { method: "POST" });
      setNote(`${res.note} 成功 ${res.fetched} · 失败 ${res.failed} · 验收 ${res.verified}`);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "抓取失败");
    }
  }

  async function crawlOrSeed() {
    setError("");
    const res = await api<{ seeded: number; note: string }>("/api/onsite/crawl-or-seed", { method: "POST" });
    setNote(res.note + `（新增 ${res.seeded} 页）`);
    load();
  }

  async function analyze() {
    setError("");
    const res = await api<AiAssist>("/api/onsite/ai", { method: "POST", body: JSON.stringify({ step: "all" }) });
    setNote(`${res.detail || res.status} ${res.evidence ? "· 见各条论证" : ""}`);
    if (res.status === "未配置") setError(res.detail || "LLM 未配置，未编造分析。");
    load();
  }

  async function aiIssue(id: string, step: string) {
    setError("");
    try {
      const res = await api<AiAssist>(`/api/onsite/issues/${id}/ai`, {
        method: "POST",
        body: JSON.stringify({ step }),
      });
      setNote(res.detail || res.status);
      if (res.status === "未配置") setError(res.detail);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "AI 失败");
    }
  }

  async function saveDraft(id: string) {
    const text = drafts[id];
    if (!text?.trim()) {
      setError("请先写改稿，分析与应用是两步");
      return;
    }
    await api(`/api/onsite/issues/${id}/draft`, { method: "PATCH", body: JSON.stringify({ proposed_change: text }) });
    load();
  }

  async function apply(issue: OnsiteIssue) {
    setError("");
    try {
      if (issue.severity === "low" && issue.risk === "low") {
        await api(`/api/onsite/issues/${issue.id}/apply-draft`, { method: "POST" });
      } else {
        await api(`/api/onsite/issues/${issue.id}/confirm-apply`, {
          method: "POST",
          body: JSON.stringify({ confirmed: true }),
        });
      }
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "失败");
    }
  }

  async function create(e: FormEvent) {
    e.preventDefault();
    await api<SitePage>("/api/onsite/pages", { method: "POST", body: JSON.stringify(form) });
    setForm({ path: "/", locale: "en-US", title: "" });
    load();
  }

  if (!board) return <p className="text-sm text-slate-500">{error || "加载中…"}</p>;

  const groups = (["critical", "high", "low"] as const).filter((k) => filter === "all" || filter === k);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">站内改页 + 人审</h1>
        <p className="mt-1 text-sm text-slate-500">
          只抓已登记页。观察层来自线上回抓，改稿写在工单里，互不覆盖。确认上线后会再抓一次做验收。无
          GSC 的收录保持未测。
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>站点 origin</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-2">
          <Input
            className="min-w-[280px] flex-1"
            placeholder="https://www.snipers.com.cn"
            value={origin}
            onChange={(e) => setOrigin(e.target.value)}
          />
          <Button type="button" variant="outline" onClick={saveOrigin}>
            保存 origin
          </Button>
          <Button type="button" onClick={fetchSite}>
            抓这一站
          </Button>
        </CardContent>
      </Card>

      <div className="flex flex-wrap gap-2">
        <Button onClick={crawlOrSeed} variant="outline">
          从内链扩清单（不抓线上）
        </Button>
        <Button onClick={analyze}>AI 分析 / 内容 / 审核 / 论证</Button>
      </div>
      {note ? <p className="text-sm text-slate-600">{note}</p> : null}

      <div className="grid gap-3 md:grid-cols-3">
        {(["critical", "high", "low"] as const).map((k) => (
          <button key={k} type="button" onClick={() => setFilter(filter === k ? "all" : k)} className="text-left">
            <Card className={filter === k ? "border-brand-600" : ""}>
              <CardHeader>
                <CardTitle className="text-sm">{sevLabel[k]}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-semibold">{board.counts[k]}</div>
                <p className="mt-1 text-xs text-slate-500">
                  {board.analyzed_pages}/{board.pages} 页已分析
                </p>
              </CardContent>
            </Card>
          </button>
        ))}
      </div>

      {groups.map((sev) => (
        <Card key={sev}>
          <CardHeader>
            <CardTitle>
              <Badge tone={sevTone[sev]}>{sevLabel[sev]}</Badge>
              <span className="ml-2 text-sm font-normal text-slate-500">{board.groups[sev].length} 条待处理</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {board.groups[sev].length === 0 ? <p className="text-sm text-slate-500">这一档没有待处理问题。</p> : null}
            {board.groups[sev].map((i) => (
              <div key={i.id} className="rounded-md border p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Link className="font-medium text-brand-700" href={`/onsite/${i.page_id}`}>
                    {i.page_title || i.page_path}
                  </Link>
                  <span className="text-xs text-slate-400">{i.page_path}</span>
                  <Badge>{catLabel[i.category] ?? i.category}</Badge>
                  <Badge tone="amber">{i.metric_status === "untested" ? "未测" : i.metric_status}</Badge>
                  <Badge tone="blue">{statusLabel[i.status] ?? i.status}</Badge>
                </div>
                <p className="mt-1 text-sm">{i.title}</p>
                <p className="text-sm text-slate-500">{i.detail}</p>
                {i.evidence ? <pre className="mt-2 whitespace-pre-wrap text-xs text-slate-500">{i.evidence}</pre> : null}
                {i.ai_review ? <p className="mt-1 text-xs text-slate-600">初审：{i.ai_review}</p> : null}
                {i.proposed_change ? <p className="mt-1 text-xs text-slate-500">已写改稿：{i.proposed_change}</p> : null}
                <Textarea
                  className="mt-2"
                  placeholder="改稿草稿（分析不会自动写入）"
                  value={drafts[i.id] ?? i.proposed_change}
                  onChange={(e) => setDrafts({ ...drafts, [i.id]: e.target.value })}
                />
                <div className="mt-2 flex flex-wrap gap-2">
                  <Button size="sm" onClick={() => aiIssue(i.id, "all")}>
                    AI 本条
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => saveDraft(i.id)}>
                    保存改稿
                  </Button>
                  {i.severity === "low" ? (
                    <Button size="sm" variant="outline" onClick={() => apply(i)}>
                      标记改稿已交付
                    </Button>
                  ) : (
                    <Button size="sm" onClick={() => apply(i)}>
                      确认已上线（回抓验收）
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      ))}

      <Card>
        <CardHeader>
          <CardTitle>登记种子页</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-3 md:grid-cols-4" onSubmit={create}>
            <Input placeholder="路径" value={form.path} onChange={(e) => setForm({ ...form, path: e.target.value })} required />
            <Input placeholder="语言" value={form.locale} onChange={(e) => setForm({ ...form, locale: e.target.value })} />
            <Input placeholder="标题" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
            <Button type="submit">加入清单</Button>
          </form>
          <ul className="mt-3 space-y-1 text-xs text-slate-500">
            {pages.map((p) => (
              <li key={p.id}>
                <Link className="text-brand-700" href={`/onsite/${p.id}`}>
                  {p.path}
                </Link>
                {" · "}
                {crawlStatusLabel[p.crawl_status] ?? p.crawl_status}
                {" · "}
                {p.fetched_at ? new Date(p.fetched_at).toLocaleString("zh-CN") : "尚未抓取"}
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-slate-500">已登记 {pages.length} 页。点路径进入单页观察与改稿。</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>内容提纲（次要）</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-sm text-slate-500">关键词 → SERP 特征。没有搜索源时特征为未测，不编造精选摘要。</p>
          {briefs.length === 0 ? <p className="text-sm text-slate-500">还没有提纲。站内问题优先。</p> : null}
          {briefs.map((b) => (
            <div key={b.id} className="flex items-center justify-between rounded-md border p-3">
              <div>
                <div className="font-medium">{b.title}</div>
                <div className="text-xs text-slate-500">
                  {b.target_keyword} · {b.locale}
                </div>
              </div>
              <Badge tone="amber">SERP {b.serp_features}</Badge>
            </div>
          ))}
        </CardContent>
      </Card>
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
    </div>
  );
}
