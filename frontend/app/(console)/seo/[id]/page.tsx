"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api, type SeoPage, type WorkOrder } from "@/lib/api";

const steps = ["outline", "draft", "meta", "review"] as const;
const stepLabel: Record<string, string> = {
  outline: "大纲",
  draft: "正文",
  meta: "Meta",
  review: "审核",
};

export default function SeoEditorPage() {
  const params = useParams<{ id: string }>();
  const [page, setPage] = useState<SeoPage | null>(null);
  const [tab, setTab] = useState<(typeof steps)[number]>("outline");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmNote, setConfirmNote] = useState("");
  const [orderMsg, setOrderMsg] = useState("");

  function load() {
    api<SeoPage>(`/api/seo-pages/${params.id}`).then(setPage).catch((e) => setError(e.message));
  }

  useEffect(() => {
    load();
  }, [params.id]);

  async function save() {
    if (!page) return;
    setBusy(true);
    try {
      const updated = await api<SeoPage>(`/api/seo-pages/${page.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          outline: page.outline,
          draft_body: page.draft_body,
          meta_title: page.meta_title,
          meta_description: page.meta_description,
          notes: page.notes,
        }),
      });
      setPage(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setBusy(false);
    }
  }

  async function generate(kind: "outline" | "draft" | "meta") {
    if (!page) return;
    setBusy(true);
    setError("");
    try {
      const updated = await api<SeoPage>(`/api/seo-pages/${page.id}/generate-${kind}`, { method: "POST" });
      setPage(updated);
      setTab(kind);
    } catch (e) {
      setError(e instanceof Error ? e.message : "生成失败");
    } finally {
      setBusy(false);
    }
  }

  async function submitReview() {
    if (!page) return;
    setBusy(true);
    try {
      await save();
      const updated = await api<SeoPage>(`/api/seo-pages/${page.id}/submit-review`, { method: "POST" });
      setPage(updated);
      setTab("review");
    } catch (e) {
      setError(e instanceof Error ? e.message : "提交失败");
    } finally {
      setBusy(false);
    }
  }

  async function markReady() {
    if (!page) return;
    setBusy(true);
    setError("");
    try {
      const updated = await api<SeoPage>(`/api/seo-pages/${page.id}/mark-ready`, {
        method: "POST",
        body: JSON.stringify({ confirmed: true, note: confirmNote }),
      });
      setPage(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "确认失败");
    } finally {
      setBusy(false);
    }
  }

  async function openWorkOrder() {
    if (!page) return;
    const type = tab === "meta" || tab === "review" ? "seo_meta" : tab === "draft" ? "seo_draft" : "seo_outline";
    setBusy(true);
    setOrderMsg("");
    try {
      const order = await api<WorkOrder>("/api/work-orders", {
        method: "POST",
        body: JSON.stringify({
          title: `${page.title} · ${stepLabel[tab] ?? "执行"}`,
          type,
          seo_page_id: page.id,
          market_id: page.market_id,
          acceptance_criteria: "大纲、正文、Meta 齐全后提交审核，由客户经理确认可交付。",
        }),
      });
      setOrderMsg(`已创建交付工单，可在工单列表领取（${order.id.slice(0, 8)}…）`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "开单失败");
    } finally {
      setBusy(false);
    }
  }

  if (!page) return <p className="text-sm text-slate-500">{error || "加载中…"}</p>;

  return (
    <div className="space-y-6">
      <div>
        <Link href="/seo" className="text-sm text-brand-700">
          ← 选题列表
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold">{page.title}</h1>
          <Badge>{page.locale}</Badge>
          <Badge tone="brand">{page.status}</Badge>
        </div>
        <p className="mt-1 text-sm text-slate-500">
          关键词：{page.target_keyword}
          {page.market_id ? (
            <>
              {" · "}
              <Link className="text-brand-700" href={`/insights/${page.market_id}`}>
                查看来源市场
              </Link>
            </>
          ) : null}
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Button size="sm" variant="outline" disabled={busy} onClick={openWorkOrder}>
            为当前步骤创建工单
          </Button>
          <Link href="/geo" className="text-sm text-brand-700">
            查看 GEO 可见度 →
          </Link>
          {orderMsg ? <span className="text-sm text-slate-500">{orderMsg}</span> : null}
        </div>
      </div>

      <div className="flex gap-2">
        {steps.map((s) => (
          <Button key={s} size="sm" variant={tab === s ? "default" : "outline"} onClick={() => setTab(s)}>
            {stepLabel[s]}
          </Button>
        ))}
      </div>

      {tab === "outline" ? (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>大纲</CardTitle>
            <Button variant="outline" disabled={busy} onClick={() => generate("outline")}>
              生成大纲模板
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-slate-500">
              按目标市场语言直接组织结构。AI 模板只是起点，交付前需要结合客户业务和当地买家表达人工确认。
            </p>
            <Textarea
              className="min-h-[320px] font-mono"
              value={page.outline}
              onChange={(e) => setPage({ ...page, outline: e.target.value })}
            />
            <Button disabled={busy} onClick={save}>
              保存大纲
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {tab === "draft" ? (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>正文</CardTitle>
            <Button variant="outline" disabled={busy} onClick={() => generate("draft")}>
              按大纲生成初稿
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            <Textarea
              className="min-h-[360px]"
              value={page.draft_body}
              onChange={(e) => setPage({ ...page, draft_body: e.target.value })}
            />
            <Button disabled={busy} onClick={save}>
              保存正文
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {tab === "meta" ? (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Meta 标题与描述</CardTitle>
            <Button variant="outline" disabled={busy} onClick={() => generate("meta")}>
              生成 Meta 草稿
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <Label>Title（建议 ≤ 60）</Label>
              <Input
                value={page.meta_title}
                onChange={(e) => setPage({ ...page, meta_title: e.target.value })}
              />
              <p className="mt-1 text-xs text-slate-400">{page.meta_title.length} 字符</p>
            </div>
            <div>
              <Label>Description（建议 ≤ 160）</Label>
              <Textarea
                value={page.meta_description}
                onChange={(e) => setPage({ ...page, meta_description: e.target.value })}
              />
              <p className="mt-1 text-xs text-slate-400">{page.meta_description.length} 字符</p>
            </div>
            <Button disabled={busy} onClick={save}>
              保存 Meta
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {tab === "review" ? (
        <Card>
          <CardHeader>
            <CardTitle>审核与人工确认</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-slate-600">
              标记“可交付”必须由客户经理确认。系统只保存内容资产，不会自动发布到客户网站。
            </p>
            <div className="grid gap-3 text-sm md:grid-cols-3">
              <div className="rounded-md bg-slate-50 p-3">大纲 {page.outline ? "已有" : "缺失"}</div>
              <div className="rounded-md bg-slate-50 p-3">正文 {page.draft_body ? "已有" : "缺失"}</div>
              <div className="rounded-md bg-slate-50 p-3">Meta {page.meta_title ? "已有" : "缺失"}</div>
            </div>
            <Button variant="outline" disabled={busy} onClick={submitReview}>
              提交审核
            </Button>
            <div className="space-y-2 border-t pt-4">
              <Label>确认备注</Label>
              <Input value={confirmNote} onChange={(e) => setConfirmNote(e.target.value)} />
              <Button disabled={busy} onClick={markReady}>
                我已确认，标记可交付
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {error ? <p className="text-sm text-red-600">{error}</p> : null}
    </div>
  );
}
