"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api, type AiAssist, type ContentBrief, type OnsiteBoard, type OnsiteIssue, type SitePage } from "@/lib/api";

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
  drafted: "已有改稿，未应用",
  draft_applied: "已写入工作区",
  confirmed: "已确认（仍不上线）",
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

  function load() {
    Promise.all([
      api<OnsiteBoard>("/api/onsite/board"),
      api<SitePage[]>("/api/onsite/pages"),
      api<ContentBrief[]>("/api/onsite/briefs"),
    ])
      .then(([b, p, br]) => {
        setBoard(b);
        setPages(p);
        setBriefs(br);
      })
      .catch((e) => setError(e.message));
  }

  useEffect(() => {
    load();
  }, []);

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
          种子/工作区内链扩清单 → 按严重级别看问题（TDK / 标题 / 内链 / schema / 收录与
          Canonical）→ 写改稿 → 再应用。分析不会改字段。无 GSC 的指标保持未测。
        </p>
      </div>

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
                      写入工作区
                    </Button>
                  ) : (
                    <Button size="sm" onClick={() => apply(i)}>
                      确认应用（仍不上线）
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
          <p className="mt-3 text-xs text-slate-500">已登记 {pages.length} 页。点问题里的标题进入单页工作区。</p>
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
