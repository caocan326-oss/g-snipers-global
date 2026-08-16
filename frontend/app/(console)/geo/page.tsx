"use client";

import { Download, Wand2 } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  api,
  type AiAssist,
  type GeoAsset,
  type GeoChecklistItem,
  type GeoPrompt,
  type GeoReport,
  type GeoReportTable,
  type GeoSampleRun,
  type GeoSummary,
  type GeoTicket,
  type GeoTicketDraft,
  type ProjectTargets,
  type SeoPage,
} from "@/lib/api";

const obsLabel: Record<string, string> = {
  untested: "未测",
  mentioned: "出现",
  not_mentioned: "未出现",
  cited: "被引用",
  verified: "引用已核验",
};

const obsTone: Record<string, "default" | "amber" | "green" | "red" | "blue"> = {
  untested: "amber",
  mentioned: "blue",
  not_mentioned: "default",
  cited: "green",
  verified: "green",
};

const evidenceLabel: Record<string, string> = {
  none: "无证据",
  mentioned: "正文提及",
  cited: "引用待核验",
  verified: "引用已核验",
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
  const [summary, setSummary] = useState<GeoSummary | null>(null);
  const [targets, setTargets] = useState<ProjectTargets | null>(null);
  const [tickets, setTickets] = useState<GeoTicket[]>([]);
  const [runs, setRuns] = useState<GeoSampleRun[]>([]);
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
  const [note, setNote] = useState("");
  const [busyAction, setBusyAction] = useState("");

  function loadPrompts() {
    Promise.all([api<GeoPrompt[]>("/api/geo/prompts"), api<GeoSummary>("/api/geo/summary")])
      .then(([rows, s]) => {
        setPrompts(rows);
        setSummary(s);
      })
      .catch((e) => setError(e.message));
  }
  function loadTickets() {
    api<GeoTicket[]>("/api/geo/tickets").then(setTickets).catch((e) => setError(e.message));
  }
  function loadRuns() {
    api<GeoSampleRun[]>("/api/geo/sample-runs").then(setRuns).catch((e) => setError(e.message));
  }
  function loadAssets() {
    api<GeoAsset[]>("/api/geo/assets").then(setAssets).catch((e) => setError(e.message));
  }

  useEffect(() => {
    loadPrompts();
    loadTickets();
    loadRuns();
    loadAssets();
    api<SeoPage[]>("/api/seo-pages").then(setPages).catch(() => undefined);
    api<ProjectTargets>("/api/project-targets").then(setTargets).catch(() => undefined);
  }, []);

  async function aiPrompt(id: string) {
    setError("");
    const res = await api<AiAssist>(`/api/geo/prompts/${id}/ai`, { method: "POST", body: JSON.stringify({ step: "analyze" }) });
    if (res.status === "未配置" || res.status === "未测") setError(res.detail || res.status);
    loadPrompts();
  }

  async function aiTicket(id: string) {
    setError("");
    const res = await api<AiAssist>(`/api/geo/tickets/${id}/ai`, { method: "POST", body: JSON.stringify({ step: "review" }) });
    if (res.status === "未配置") setError(res.detail);
    loadTickets();
  }

  async function aiAsset(id: string) {
    setError("");
    const res = await api<AiAssist>(`/api/geo/assets/${id}/ai`, { method: "POST", body: JSON.stringify({ step: "content" }) });
    if (res.status === "未配置") setError(res.detail);
    loadAssets();
  }

  async function addPrompt(e: FormEvent) {
    e.preventDefault();
    await api("/api/geo/prompts", { method: "POST", body: JSON.stringify(form) });
    setForm({ prompt_text: "", locale: "en-US" });
    loadPrompts();
  }

  async function setObs(id: string, status: string, extra: Record<string, string | null> = {}) {
    await api(`/api/geo/observations/${id}`, { method: "PATCH", body: JSON.stringify({ status, ...extra }) });
    loadPrompts();
  }

  async function seedPromptPanel() {
    setError("");
    setNote("");
    setBusyAction("seed-prompts");
    try {
      const res = await api<{ created: number; skipped: number; prompts: number; note: string }>("/api/geo/prompt-panel/seed", { method: "POST" });
      setNote(`${res.note} 新增 ${res.created} 条，跳过 ${res.skipped} 条。当前问句 ${res.prompts} 条。`);
      loadPrompts();
    } catch (e) {
      setError(e instanceof Error ? e.message : "生成问句失败");
    } finally {
      setBusyAction("");
    }
  }

  async function downloadGeoReport() {
    const report = await api<GeoReport>("/api/geo/report");
    const blob = new Blob([report.markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `geo-report-${new Date(report.generated_at).toISOString().slice(0, 10)}.md`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    setNote("GEO 报告已导出。");
  }

  async function downloadGeoTable() {
    const report = await api<GeoReportTable>("/api/geo/report-table");
    const blob = new Blob([report.csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = report.filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    setNote("GEO 采样证据表已导出。");
  }

  async function createEvidenceRun() {
    setError("");
    setNote("");
    setBusyAction("evidence-run");
    try {
      const run = await api<GeoSampleRun>("/api/geo/sample-runs/from-observations", {
        method: "POST",
        body: JSON.stringify({ note: "从当前人工 GEO 观测生成证据运行。" }),
      });
      setNote(`已生成证据运行 ${run.id}，包含 ${run.results_count} 条证据，config hash ${run.config_hash}。`);
      loadPrompts();
      loadRuns();
    } catch (e) {
      setError(e instanceof Error ? e.message : "生成证据运行失败");
    } finally {
      setBusyAction("");
    }
  }

  async function draftTicketsFromEvidence() {
    setError("");
    setNote("");
    setBusyAction("draft-tickets");
    try {
      const res = await api<GeoTicketDraft>("/api/geo/tickets/draft-from-evidence", { method: "POST" });
      setNote(`${res.note} 新增 ${res.created} 条，跳过 ${res.skipped} 条。`);
      loadTickets();
    } catch (e) {
      setError(e instanceof Error ? e.message : "生成工单失败");
    } finally {
      setBusyAction("");
    }
  }

  async function runAutoSample() {
    setError("");
    setNote("");
    setBusyAction("auto-sample");
    try {
      const run = await api<GeoSampleRun>("/api/geo/sample-runs/auto", {
        method: "POST",
        body: JSON.stringify({
          engine: "llm",
          trials: 1,
          limit: 8,
          web_grounded: "false",
          region_hint: "API",
        }),
      });
      setNote(`自动采样完成：run ${run.id}，证据 ${run.results_count} 条。若模型未联网，citation 仅作低权重观测。`);
      loadRuns();
      loadPrompts();
    } catch (e) {
      setError(e instanceof Error ? e.message : "自动采样失败");
    } finally {
      setBusyAction("");
    }
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
            <div key={o.id} className="w-full rounded-md border p-3 lg:w-[calc(50%-0.375rem)]">
              <div className="mb-2 flex items-center justify-between gap-3">
                <div className="text-xs font-medium text-slate-500">{o.engine_label || o.engine}</div>
                <Badge tone={obsTone[o.status]}>{obsLabel[o.status] ?? o.status}</Badge>
              </div>
              <div className="mb-2 flex flex-wrap gap-2 text-[11px] text-slate-500">
                <span>{o.surface || "manual_ai_answer"}</span>
                <span>{o.sample_type || "manual"}</span>
                <span>{o.evidence_label || evidenceLabel[o.evidence_tier || "none"]}</span>
                {o.observed_at ? <span>{new Date(o.observed_at).toLocaleString("zh-CN")}</span> : null}
              </div>
              <div className="mt-2 flex flex-wrap gap-1">
                {["untested", "not_mentioned", "mentioned", "cited", "verified"].map((s) => (
                  <Button key={s} size="sm" variant="ghost" onClick={() => setObs(o.id, s)}>
                    {obsLabel[s]}
                  </Button>
                ))}
              </div>
              <div className="mt-3 grid gap-2">
                <Textarea
                  className="min-h-[72px]"
                  placeholder="回答摘录：粘贴 AI 答案里和客户/竞品/来源相关的片段"
                  defaultValue={o.response_excerpt || ""}
                  onBlur={(e) => setObs(o.id, o.status, { response_excerpt: e.target.value })}
                />
                <Input
                  placeholder="引用 URL，一行或逗号分隔"
                  defaultValue={o.citation_urls || ""}
                  onBlur={(e) => setObs(o.id, o.status, { citation_urls: e.target.value })}
                />
                <div className="grid gap-2 md:grid-cols-2">
                  <Input
                    placeholder="品牌/产品提及"
                    defaultValue={o.brand_mentions || ""}
                    onBlur={(e) => setObs(o.id, o.status, { brand_mentions: e.target.value })}
                  />
                  <Input
                    placeholder="竞品提及"
                    defaultValue={o.competitor_mentions || ""}
                    onBlur={(e) => setObs(o.id, o.status, { competitor_mentions: e.target.value })}
                  />
                </div>
                <Input
                  placeholder="解释备注：例如 consumer_scrape / web_rank / api_proxy，不混同口径"
                  defaultValue={o.interpretation_note || o.notes || ""}
                  onBlur={(e) => setObs(o.id, o.status, { interpretation_note: e.target.value, notes: e.target.value })}
                />
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
        <h1 className="text-2xl font-semibold">GEO Prompt Lab</h1>
        <p className="mt-1 text-sm text-slate-500">
          围绕客户目标国家、关键词和竞品生成买家问句，人工记录真实 AI 采样。正文提及、引用、已核验引用分开计算。
        </p>
      </div>

      <div className="space-y-2">
        <div className="flex flex-wrap gap-2">
          <Button size="sm" onClick={seedPromptPanel} disabled={busyAction === "seed-prompts"}>
            <Wand2 className="mr-2 h-4 w-4" />
            {busyAction === "seed-prompts" ? "生成中…" : "从 SEO 目标生成问句"}
          </Button>
          <Button size="sm" variant="outline" onClick={createEvidenceRun} disabled={busyAction === "evidence-run"}>
            {busyAction === "evidence-run" ? "生成中…" : "生成证据运行"}
          </Button>
          <Button size="sm" variant="outline" onClick={draftTicketsFromEvidence} disabled={busyAction === "draft-tickets"}>
            {busyAction === "draft-tickets" ? "生成中…" : "从证据生成工单"}
          </Button>
          <Button size="sm" onClick={runAutoSample} disabled={busyAction === "auto-sample"}>
            {busyAction === "auto-sample" ? "采样中…" : "自动采样一轮"}
          </Button>
          <Button size="sm" variant="outline" onClick={downloadGeoReport}>
            <Download className="mr-2 h-4 w-4" />
            导出报告
          </Button>
          <Button size="sm" variant="outline" onClick={downloadGeoTable}>
            <Download className="mr-2 h-4 w-4" />
            导出证据表
          </Button>
        </div>
        {note ? <p className="text-sm text-emerald-700">{note}</p> : null}
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
      </div>

      <Card className="rounded-md">
        <CardHeader>
          <CardTitle>GEO 测试目标</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 lg:grid-cols-3">
          <div className="rounded-md border border-slate-200 p-3">
            <div className="text-xs font-medium text-slate-500">目标国家</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {(targets?.markets ?? []).slice(0, 6).map((market) => (
                <Badge key={market.id} tone={market.status === "priority" ? "brand" : "default"}>
                  {market.name} · {market.primary_locale}
                </Badge>
              ))}
              {targets?.markets.length ? null : <span className="text-sm text-slate-500">未设置</span>}
            </div>
          </div>
          <div className="rounded-md border border-slate-200 p-3">
            <div className="text-xs font-medium text-slate-500">问句来源关键词</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {(targets?.markets.flatMap((market) => market.demand_signals) ?? []).slice(0, 8).map((signal) => (
                <Badge key={signal.id} tone="blue">{signal.theme}</Badge>
              ))}
              {targets?.keyword_count ? null : <span className="text-sm text-slate-500">未设置</span>}
            </div>
          </div>
          <div className="rounded-md border border-slate-200 p-3">
            <div className="text-xs font-medium text-slate-500">竞品对照</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {(targets?.markets.flatMap((market) => market.competitors) ?? []).slice(0, 8).map((competitor) => (
                <Badge key={competitor.id}>{competitor.name}</Badge>
              ))}
              {targets?.competitor_count ? null : <span className="text-sm text-slate-500">未设置</span>}
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-3 md:grid-cols-5">
        <Card className="rounded-md">
          <CardContent className="py-4">
            <div className="text-2xl font-semibold">{summary?.prompts ?? 0}</div>
            <div className="text-xs text-slate-500">采样问句</div>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="py-4">
            <div className="text-2xl font-semibold">{summary?.recorded ?? 0}</div>
            <div className="text-xs text-slate-500">已记录槽位</div>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="py-4">
            <div className="text-2xl font-semibold">{summary?.mention_rate ?? "未测"}</div>
            <div className="text-xs text-slate-500">品牌提及率</div>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="py-4">
            <div className="text-2xl font-semibold">{summary?.cite_rate ?? "未测"}</div>
            <div className="text-xs text-slate-500">官网引用率</div>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="py-4">
            <div className="text-2xl font-semibold">{summary?.verified_citation_rate ?? "未测"}</div>
            <div className="text-xs text-slate-500">核验引用率</div>
          </CardContent>
        </Card>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <Card className="rounded-md">
          <CardContent className="flex items-center justify-between py-4 text-sm">
            <span className="text-slate-500">竞品提及率</span>
            <span className="font-semibold text-slate-900">{summary?.competitor_rate ?? "未测"}</span>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="flex items-center justify-between py-4 text-sm">
            <span className="text-slate-500">竞品提及槽位</span>
            <span className="font-semibold text-slate-900">{summary?.competitor_mentions ?? 0}</span>
          </CardContent>
        </Card>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        <Card className="rounded-md">
          <CardContent className="flex items-center justify-between py-4 text-sm">
            <span className="text-slate-500">证据运行</span>
            <span className="font-semibold text-slate-900">{summary?.sample_runs ?? 0}</span>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="flex items-center justify-between py-4 text-sm">
            <span className="text-slate-500">证据条目</span>
            <span className="font-semibold text-slate-900">{summary?.evidence_results ?? 0}</span>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="py-4 text-sm">
            <div className="text-slate-500">最近 run</div>
            <div className="mt-1 truncate font-mono text-xs text-slate-900">{summary?.latest_run_id ?? "暂无"}</div>
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-md">
        <CardHeader>
          <CardTitle>证据运行记录</CardTitle>
          <p className="text-sm text-slate-500">正式报告里的引用类结论，需要绑定 run_id、evidence_id、hash 和核验状态。</p>
        </CardHeader>
        <CardContent className="space-y-3">
          {runs.length ? runs.map((run) => (
            <div key={run.id} className="rounded-md border border-slate-200 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div className="font-mono text-xs text-slate-500">{run.id}</div>
                  <div className="mt-1 text-sm font-medium">
                    {run.protocol_version} · {run.prompt_set_id} · {run.results_count} 条证据
                  </div>
                </div>
                <Badge tone={run.status === "done" ? "green" : "amber"}>{run.status}</Badge>
              </div>
              <div className="mt-3 grid gap-2 text-xs text-slate-600 md:grid-cols-4">
                <div>config hash：<span className="font-mono">{run.config_hash}</span></div>
                <div>提及：{run.mention_rate}</div>
                <div>自有引用：{run.cite_rate}</div>
                <div>核验引用：{run.verified_citation_rate}</div>
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {run.results.slice(0, 6).map((result) => (
                  <Badge key={result.id} tone={result.verification_status === "passed" ? "green" : "default"}>
                    {result.evidence_id} · {result.engine_label ?? result.engine}
                  </Badge>
                ))}
              </div>
            </div>
          )) : <p className="text-sm text-slate-500">暂无证据运行。记录一条观测后，可以点击“生成证据运行”。</p>}
        </CardContent>
      </Card>

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
                  {p.prompt_key || "custom"} · {p.prompt_type || "custom"} · {p.prompt_pack_id || "custom"} · {p.locale} · 提及 {p.mention_rate ?? "未测"} · 引用 {p.cite_rate ?? "未测"} · 核验 {p.verified_citation_rate ?? "未测"} · 竞品 {p.competitor_rate ?? "未测"}
                </p>
                {p.evidence ? <pre className="mt-2 whitespace-pre-wrap text-xs text-slate-500">{p.evidence}</pre> : null}
                <div className="mt-2 flex items-center gap-2">
                  <Button size="sm" onClick={() => aiPrompt(p.id)}>
                    AI 诊断
                  </Button>
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
                {t.evidence ? <pre className="whitespace-pre-wrap text-xs text-slate-500">{t.evidence}</pre> : null}
                {t.ai_review ? <p className="text-sm text-slate-600">初审：{t.ai_review}</p> : null}
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" onClick={() => aiTicket(t.id)}>
                    AI 初审
                  </Button>
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
                  <Button variant="outline" onClick={() => aiAsset(llms.id)}>
                    AI 改稿
                  </Button>
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
    </div>
  );
}
