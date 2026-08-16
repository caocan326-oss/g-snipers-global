"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { Input } from "@/components/ui/input";
import {
  api,
  type AiAssist,
  type GeoAsset,
  type GeoChecklistItem,
  type GeoPrompt,
  type GeoProviderStatusList,
  type GeoReport,
  type GeoReportTable,
  type GeoSampleRun,
  type GeoSummary,
  type GeoTicket,
  type GeoTicketDraft,
  type ProjectTargets,
  type SeoPage,
} from "@/lib/api";

import { AssetsPanel } from "./_components/AssetsPanel";
import { EvidenceQualityCard, type ProviderQualityEntry } from "./_components/EvidenceQualityCard";
import { HeroSection } from "./_components/HeroSection";
import { MetricsGrid } from "./_components/MetricsGrid";
import { ProviderStatusCard } from "./_components/ProviderStatusCard";
import { SamplePromptsPanel } from "./_components/SamplePromptsPanel";
import { SampleRunsCard } from "./_components/SampleRunsCard";
import { TargetsCard } from "./_components/TargetsCard";
import { TabNav } from "./_components/TabNav";
import { TicketsPanel, type TicketForm } from "./_components/TicketsPanel";
import { geoEvidenceVerdict, type Tab } from "./_helpers";

export default function GeoPage() {
  const [tab, setTab] = useState<Tab>("sample");
  const [prompts, setPrompts] = useState<GeoPrompt[]>([]);
  const [summary, setSummary] = useState<GeoSummary | null>(null);
  const [targets, setTargets] = useState<ProjectTargets | null>(null);
  const [tickets, setTickets] = useState<GeoTicket[]>([]);
  const [runs, setRuns] = useState<GeoSampleRun[]>([]);
  const [providers, setProviders] = useState<GeoProviderStatusList | null>(null);
  const [assets, setAssets] = useState<GeoAsset[]>([]);
  const [pages, setPages] = useState<SeoPage[]>([]);
  const [pageId, setPageId] = useState("");
  const [items, setItems] = useState<GeoChecklistItem[]>([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ prompt_text: "", locale: "en-US" });
  const [ticketForm, setTicketForm] = useState<TicketForm>({
    prompt_id: "",
    title: "",
    diagnosis: "untested",
    rationale: "",
    acceptance_criteria: "",
  });
  const [confirmNote, setConfirmNote] = useState("");
  const [note, setNote] = useState("");
  const [busyAction, setBusyAction] = useState("");
  const [sampleProvider, setSampleProvider] = useState("deepseek");

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
    api<GeoProviderStatusList>("/api/geo/providers/status").then(setProviders).catch(() => undefined);
  }, []);

  useEffect(() => {
    const rows = providers?.providers ?? [];
    if (!rows.length) return;
    if (rows.some((provider) => provider.key === sampleProvider)) return;
    const preferred = rows.find((provider) => provider.configured && provider.role === "grounded_answer")
      ?? rows.find((provider) => provider.configured && provider.web_grounded)
      ?? rows.find((provider) => provider.configured)
      ?? rows[0];
    setSampleProvider(preferred.key);
  }, [providers, sampleProvider]);

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
        body: JSON.stringify({ note: "从当前人工 GEO 观测固化一批可追溯证据。" }),
      });
      setNote(`已固化一批 GEO 证据：${run.results_count} 条记录，批次 ${run.id}，配置指纹 ${run.config_hash}。`);
      loadPrompts();
      loadRuns();
    } catch (e) {
      setError(e instanceof Error ? e.message : "固化证据失败");
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
      setError(e instanceof Error ? e.message : "生成整改项失败");
    } finally {
      setBusyAction("");
    }
  }

  async function runAutoSample() {
    setError("");
    setNote("");
    setBusyAction("auto-sample");
    const selected = (providers?.providers ?? []).find((provider) => provider.key === sampleProvider);
    try {
      const run = await api<GeoSampleRun>("/api/geo/sample-runs/auto", {
        method: "POST",
        body: JSON.stringify({
          engine: sampleProvider,
          provider: sampleProvider,
          trials: 1,
          limit: 8,
          web_grounded: selected?.web_grounded ? "true" : "false",
          region_hint: selected?.label ?? "API",
        }),
      });
      setNote(`${selected?.label ?? sampleProvider} 采样完成：run ${run.id}，证据 ${run.results_count} 条。${selected?.web_grounded ? "返回引用来源时可计入联网引用证据。" : "该结果用于分析和品牌提及判断，不计入真实联网引用率。"}`);
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
  const selectedProvider = useMemo(
    () => (providers?.providers ?? []).find((provider) => provider.key === sampleProvider),
    [providers?.providers, sampleProvider]
  );
  const evidenceVerdict = useMemo(() => geoEvidenceVerdict(summary, runs), [runs, summary]);
  const providerQuality: ProviderQualityEntry[] = useMemo(() => {
    return (providers?.providers ?? []).map((provider) => {
      const providerRuns = runs.filter((run) => run.engines.includes(provider.key));
      const providerResults = providerRuns.flatMap((run) => run.results);
      const verified = providerResults.filter((result) => result.verification_status === "passed").length;
      const citations = providerResults.filter((result) => result.citations.length > 0).length;
      const status = !provider.configured
        ? "未配置"
        : providerResults.length === 0
          ? "待采样"
          : verified > 0
            ? "有核验证据"
            : citations > 0
              ? "有来源待核验"
              : provider.web_grounded
                ? "无来源"
                : "分析参考";
      return { provider, providerRuns, providerResults, verified, citations, status };
    });
  }, [providers?.providers, runs]);

  return (
    <div className="space-y-6">
      <HeroSection
        summary={summary}
        busyAction={busyAction}
        seedPromptPanel={seedPromptPanel}
        createEvidenceRun={createEvidenceRun}
        draftTicketsFromEvidence={draftTicketsFromEvidence}
        providers={providers}
        sampleProvider={sampleProvider}
        setSampleProvider={setSampleProvider}
        selectedProvider={selectedProvider}
        runAutoSample={runAutoSample}
        downloadGeoReport={downloadGeoReport}
        downloadGeoTable={downloadGeoTable}
        note={note}
        error={error}
      />

      <ProviderStatusCard providers={providers} />

      <EvidenceQualityCard
        evidenceVerdict={evidenceVerdict}
        runs={runs}
        summary={summary}
        providerQuality={providerQuality}
      />

      <TargetsCard targets={targets} />

      <MetricsGrid summary={summary} />

      <SampleRunsCard runs={runs} />

      <TabNav tab={tab} setTab={setTab} />

      {tab === "sample" ? (
        <SamplePromptsPanel
          prompts={prompts}
          form={form}
          setForm={setForm}
          addPrompt={addPrompt}
          aiPrompt={aiPrompt}
          setDiagnosis={setDiagnosis}
          setObs={setObs}
        />
      ) : null}

      {tab === "tickets" ? (
        <TicketsPanel
          tickets={tickets}
          prompts={prompts}
          ticketForm={ticketForm}
          setTicketForm={setTicketForm}
          addTicket={addTicket}
          aiTicket={aiTicket}
          verifyTicket={verifyTicket}
          reopenTicket={reopenTicket}
        />
      ) : null}

      {tab === "assets" ? (
        <AssetsPanel
          llms={llms}
          cite={cite}
          pages={pages}
          pageId={pageId}
          items={items}
          generateLlms={generateLlms}
          saveAsset={saveAsset}
          aiAsset={aiAsset}
          readyAsset={readyAsset}
          loadChecklist={loadChecklist}
          setCheck={setCheck}
        />
      ) : null}

      <Input placeholder="确认 / 验收备注" value={confirmNote} onChange={(e) => setConfirmNote(e.target.value)} />
    </div>
  );
}
