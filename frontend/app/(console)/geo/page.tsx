"use client";

import { FormEvent, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  api,
  type GeoAsset,
  type GeoChecklistItem,
  type GeoPrompt,
  type GeoTicket,
  type SeoPage,
} from "@/lib/api";

const obsLabel: Record<string, string> = {
  untested: "未测",
  mentioned: "出现",
  not_mentioned: "未出现",
  cited: "被引用",
};

const obsTone: Record<string, "default" | "amber" | "green" | "red" | "blue"> = {
  untested: "amber",
  mentioned: "blue",
  not_mentioned: "default",
  cited: "green",
};

const diagnosisOptions = [
  ["untested", "未测"],
  ["absent", "未出现"],
  ["mentioned", "被提及"],
  ["competitor_dominated", "竞品主导"],
  ["suspected_negative", "疑似负面"],
] as const;

const ticketStatus: Record<string, string> = {
  open: "待办",
  in_progress: "执行中",
  verify: "待验收",
  done: "已验收",
  reopened: "已重开",
};

export default function GeoPage() {
  const [tab, setTab] = useState<"sample" | "tickets" | "assets">("sample");
  const [prompts, setPrompts] = useState<GeoPrompt[]>([]);
  const [tickets, setTickets] = useState<GeoTicket[]>([]);
  const [assets, setAssets] = useState<GeoAsset[]>([]);
  const [pages, setPages] = useState<SeoPage[]>([]);
  const [pageId, setPageId] = useState("");
  const [items, setItems] = useState<GeoChecklistItem[]>([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ prompt_text: "", locale: "en-US" });
  const [ticketForm, setTicketForm] = useState({
    prompt_id: "",
    title: "",
    diagnosis: "untested",
    rationale: "",
    acceptance_criteria: "",
  });
  const [confirmNote, setConfirmNote] = useState("");

  function loadPrompts() {
    api<GeoPrompt[]>("/api/geo/prompts").then(setPrompts).catch((e) => setError(e.message));
  }
  function loadTickets() {
    api<GeoTicket[]>("/api/geo/tickets").then(setTickets).catch((e) => setError(e.message));
  }
  function loadAssets() {
    api<GeoAsset[]>("/api/geo/assets").then(setAssets).catch((e) => setError(e.message));
  }

  useEffect(() => {
    loadPrompts();
    loadTickets();
    loadAssets();
    api<SeoPage[]>("/api/seo-pages").then(setPages).catch(() => undefined);
  }, []);

  async function addPrompt(e: FormEvent) {
    e.preventDefault();
    await api("/api/geo/prompts", { method: "POST", body: JSON.stringify(form) });
    setForm({ prompt_text: "", locale: "en-US" });
    loadPrompts();
  }

  async function setObs(id: string, status: string) {
    await api(`/api/geo/observations/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
    loadPrompts();
  }

  async function setDiagnosis(promptId: string, diagnosis: string) {
    await api(`/api/geo/prompts/${promptId}/diagnosis`, { method: "PATCH", body: JSON.stringify({ diagnosis }) });
    loadPrompts();
  }

  async function addTicket(e: FormEvent) {
    e.preventDefault();
    await api("/api/geo/tickets", { method: "POST", body: JSON.stringify(ticketForm) });
    setTicketForm({ prompt_id: "", title: "", diagnosis: "untested", rationale: "", acceptance_criteria: "" });
    loadTickets();
  }

  async function verifyTicket(id: string, confirmed: boolean) {
    setError("");
    try {
      await api(`/api/geo/tickets/${id}/verify`, {
        method: "POST",
        body: JSON.stringify({ confirmed, note: confirmNote }),
      });
      loadTickets();
    } catch (e) {
      setError(e instanceof Error ? e.message : "验收失败");
    }
  }

  async function reopenTicket(id: string) {
    await api(`/api/geo/tickets/${id}/reopen`, { method: "POST", body: JSON.stringify({ note: confirmNote }) });
    loadTickets();
  }

  async function generateLlms() {
    await api("/api/geo/assets/llms.txt/generate", { method: "POST" });
    loadAssets();
  }

  async function saveAsset(id: string, body: string) {
    await api(`/api/geo/assets/${id}`, { method: "PATCH", body: JSON.stringify({ body }) });
    loadAssets();
  }

  async function readyAsset(id: string) {
    setError("");
    try {
      await api(`/api/geo/assets/${id}/mark-ready`, {
        method: "POST",
        body: JSON.stringify({ confirmed: true, note: confirmNote }),
      });
      loadAssets();
    } catch (e) {
      setError(e instanceof Error ? e.message : "确认失败");
    }
  }

  async function loadChecklist(id: string) {
    setPageId(id);
    const rows = await api<GeoChecklistItem[]>(`/api/geo/checklists/ensure?seo_page_id=${id}`, { method: "POST" });
    setItems(rows);
  }

  async function setCheck(id: string, status: string) {
    await api(`/api/geo/checklist-items/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
    if (pageId) loadChecklist(pageId);
  }

  const llms = assets.find((a) => a.kind === "llms_txt");
  const cite = assets.find((a) => a.kind === "cite_checklist");

  function slotGroup(p: GeoPrompt, region: string, title: string) {
    const rows = p.observations.filter((o) => (o.region || "") === region);
    return (
      <div>
        <div className="mb-2 text-xs font-medium text-slate-500">{title}</div>
        <div className="flex flex-wrap gap-3">
          {rows.map((o) => (
            <div key={o.id} className="rounded-md border p-3">
              <div className="mb-2 text-xs text-slate-500">{o.engine_label || o.engine}</div>
              <Badge tone={obsTone[o.status]}>{obsLabel[o.status] ?? o.status}</Badge>
              <div className="mt-2 flex flex-wrap gap-1">
                {["untested", "mentioned", "not_mentioned", "cited"].map((s) => (
                  <Button key={s} size="sm" variant="ghost" onClick={() => setObs(o.id, s)}>
                    {obsLabel[s]}
                  </Button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">GEO 闭环</h1>
        <p className="mt-1 text-sm text-slate-500">
          问句集 → 中西引擎采样（可手填 / 未配置）→ 诊断层 → 带验收标准的工单 → 确认验收或重开。引用 ≠
          吸收。brand.com 引用率未测。不得交付「已让 ChatGPT 引用」。
        </p>
      </div>

      <div className="flex gap-2">
        <Button size="sm" variant={tab === "sample" ? "default" : "outline"} onClick={() => setTab("sample")}>
          采样
        </Button>
        <Button size="sm" variant={tab === "tickets" ? "default" : "outline"} onClick={() => setTab("tickets")}>
          工单验收
        </Button>
        <Button size="sm" variant={tab === "assets" ? "default" : "outline"} onClick={() => setTab("assets")}>
          资产（llms.txt / 可引用）
        </Button>
      </div>

      {tab === "sample" ? (
        <div className="space-y-4">
          {prompts.map((p) => (
            <Card key={p.id}>
              <CardHeader>
                <CardTitle className="text-base">{p.prompt_text}</CardTitle>
                <p className="text-xs text-slate-500">
                  {p.locale} · 引用率 {p.cite_rate ?? "未测"} · 吸收率 {p.absorption_rate ?? "未测"}
                </p>
                <div className="mt-2 flex items-center gap-2">
                  <span className="text-xs text-slate-500">诊断</span>
                  <select
                    className="h-8 rounded-md border border-slate-200 px-2 text-sm"
                    value={p.diagnosis}
                    onChange={(e) => setDiagnosis(p.id, e.target.value)}
                  >
                    {diagnosisOptions.map(([k, v]) => (
                      <option key={k} value={k}>
                        {v}
                      </option>
                    ))}
                  </select>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {slotGroup(p, "western", "西方引擎")}
                {slotGroup(p, "china", "中国引擎（可手填，未测即可）")}
              </CardContent>
            </Card>
          ))}
          <Card>
            <CardHeader>
              <CardTitle>加入采样问句</CardTitle>
            </CardHeader>
            <CardContent>
              <form className="grid gap-3 md:grid-cols-3" onSubmit={addPrompt}>
                <Input
                  className="md:col-span-2"
                  placeholder="买家会问模型的原句"
                  value={form.prompt_text}
                  onChange={(e) => setForm({ ...form, prompt_text: e.target.value })}
                  required
                />
                <div className="flex gap-2">
                  <Input value={form.locale} onChange={(e) => setForm({ ...form, locale: e.target.value })} />
                  <Button type="submit">添加</Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      ) : null}

      {tab === "tickets" ? (
        <div className="space-y-4">
          {tickets.map((t) => (
            <Card key={t.id}>
              <CardHeader className="flex flex-row items-start justify-between">
                <div>
                  <CardTitle className="text-base">{t.title}</CardTitle>
                  <p className="mt-1 text-xs text-slate-500">
                    诊断 {t.diagnosis_label} · {ticketStatus[t.status] ?? t.status}
                  </p>
                </div>
                <Badge tone={t.status === "done" ? "green" : t.status === "reopened" ? "red" : "amber"}>
                  {ticketStatus[t.status] ?? t.status}
                </Badge>
              </CardHeader>
              <CardContent className="space-y-2">
                <p className="text-sm text-slate-600">理由：{t.rationale}</p>
                <p className="text-sm text-slate-600">验收：{t.acceptance_criteria}</p>
                {t.verified_note ? <p className="text-xs text-slate-500">备注：{t.verified_note}</p> : null}
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" variant="outline" onClick={() => verifyTicket(t.id, false)}>
                    未确认
                  </Button>
                  <Button size="sm" onClick={() => verifyTicket(t.id, true)}>
                    确认验收
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => reopenTicket(t.id)}>
                    复测后重开
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
          <Card>
            <CardHeader>
              <CardTitle>从问句开验收工单</CardTitle>
            </CardHeader>
            <CardContent>
              <form className="space-y-3" onSubmit={addTicket}>
                <select
                  className="h-9 w-full rounded-md border border-slate-200 px-2 text-sm"
                  value={ticketForm.prompt_id}
                  onChange={(e) => setTicketForm({ ...ticketForm, prompt_id: e.target.value })}
                  required
                >
                  <option value="">选择问句</option>
                  {prompts.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.prompt_text}
                    </option>
                  ))}
                </select>
                <Input
                  placeholder="工单标题"
                  value={ticketForm.title}
                  onChange={(e) => setTicketForm({ ...ticketForm, title: e.target.value })}
                  required
                />
                <select
                  className="h-9 w-full rounded-md border border-slate-200 px-2 text-sm"
                  value={ticketForm.diagnosis}
                  onChange={(e) => setTicketForm({ ...ticketForm, diagnosis: e.target.value })}
                >
                  {diagnosisOptions.map(([k, v]) => (
                    <option key={k} value={k}>
                      {v}
                    </option>
                  ))}
                </select>
                <Textarea
                  placeholder="理由"
                  value={ticketForm.rationale}
                  onChange={(e) => setTicketForm({ ...ticketForm, rationale: e.target.value })}
                />
                <Textarea
                  placeholder="验收标准（不要写「已让引擎引用」）"
                  value={ticketForm.acceptance_criteria}
                  onChange={(e) => setTicketForm({ ...ticketForm, acceptance_criteria: e.target.value })}
                />
                <Button type="submit">开工单</Button>
              </form>
            </CardContent>
          </Card>
        </div>
      ) : null}

      {tab === "assets" ? (
        <div className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>llms.txt 草稿</CardTitle>
                <p className="mt-1 text-sm text-slate-500">本链资产，不是 SoV 看板。不会自动挂到客户域名。</p>
              </div>
              <Button variant="outline" onClick={generateLlms}>
                按选题生成
              </Button>
            </CardHeader>
            <CardContent className="space-y-3">
              {llms ? (
                <>
                  <Badge>{llms.status === "ready" ? "可交付" : "草稿"}</Badge>
                  <Textarea
                    className="min-h-[220px] font-mono"
                    defaultValue={llms.body}
                    key={llms.updated_at ?? llms.id}
                    onBlur={(e) => saveAsset(llms.id, e.target.value)}
                  />
                  <Button onClick={() => readyAsset(llms.id)}>我已确认，标记可交付</Button>
                </>
              ) : (
                <p className="text-sm text-slate-500">还没有草稿。</p>
              )}
            </CardContent>
          </Card>
          {cite ? (
            <Card>
              <CardHeader>
                <CardTitle>可引用性清单（资产）</CardTitle>
              </CardHeader>
              <CardContent>
                <Textarea
                  className="min-h-[160px]"
                  defaultValue={cite.body}
                  key={cite.updated_at ?? cite.id}
                  onBlur={(e) => saveAsset(cite.id, e.target.value)}
                />
              </CardContent>
            </Card>
          ) : null}
          <Card>
            <CardHeader>
              <CardTitle>挂在选题上的勾选</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <select
                className="h-9 w-full rounded-md border border-slate-200 px-2 text-sm"
                value={pageId}
                onChange={(e) => loadChecklist(e.target.value)}
              >
                <option value="">选择一篇选题</option>
                {pages.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.title}
                  </option>
                ))}
              </select>
              {items.map((i) => (
                <div key={i.id} className="flex items-center justify-between rounded-md border p-3">
                  <div>
                    <div className="font-medium">{i.label}</div>
                    <Badge tone={i.status === "untested" ? "amber" : i.status === "pass" ? "green" : "red"}>
                      {i.status === "untested" ? "未测" : i.status === "pass" ? "通过" : "未通过"}
                    </Badge>
                  </div>
                  <div className="flex gap-1">
                    <Button size="sm" variant="outline" onClick={() => setCheck(i.id, "untested")}>
                      未测
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => setCheck(i.id, "pass")}>
                      通过
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => setCheck(i.id, "fail")}>
                      未通过
                    </Button>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      ) : null}

      <Input placeholder="确认 / 验收备注" value={confirmNote} onChange={(e) => setConfirmNote(e.target.value)} />
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
    </div>
  );
}
