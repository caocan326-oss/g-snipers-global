"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { Input } from "@/components/ui/input";
import {
  api,
  downloadApiFile,
  type AiAssist,
  type GeoAsset,
  type GeoChecklistItem,
  type GeoGroundedBatch,
  type GeoPrompt,
  type GeoProviderStatusList,
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
import { localeForCode } from "@/lib/countries";

import { geoEvidenceVerdict, type Tab } from "./_helpers";

export default function GeoPage() {
  const [tab, setTab] = useState<Tab>("tickets");
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
  const [form, setForm] = useState({ prompt_text: "", country_code: "US" });
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
  const [sampleProvider, setSampleProvider] = useState("");
  const [providerPicked, setProviderPicked] = useState(false);

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
    api<ProjectTargets>("/api/project-targets")
      .then((res) => {
        setTargets(res);
        const preferred = res.markets.find((market) => market.status === "priority") ?? res.markets[0];
        if (preferred?.country_code) {
          setForm((current) => (current.prompt_text ? current : { ...current, country_code: preferred.country_code.toUpperCase() }));
        }
      })
      .catch(() => undefined);
    api<GeoProviderStatusList>("/api/geo/providers/status").then(setProviders).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (providerPicked) return;
    const rows = providers?.providers ?? [];
    if (!rows.length) return;
    const preferred =
      rows.find((provider) => provider.configured && provider.web_grounded)
      ?? rows.find((provider) => provider.configured)
      ?? rows[0];
    setSampleProvider(preferred.key);
  }, [providers, providerPicked]);

  async function aiPrompt(id: string) {
    setError("");
    const res = await api<AiAssist>(`/api/geo/prompts/${id}/ai`, { method: "POST", body: JSON.stringify({ step: "analyze" }) });
    if (res.status === "未配置" || res.status === "未测") setError(res.detail || res.status);
    loadPrompts();
  }

  async function aiAsset(id: string) {
    setError("");
    const res = await api<AiAssist>(`/api/geo/assets/${id}/ai`, { method: "POST", body: JSON.stringify({ step: "content" }) });
    if (res.status === "未配置") setError(res.detail);
    loadAssets();
  }

  async function addPrompt(e: FormEvent) {
    e.preventDefault();
    await api("/api/geo/prompts", { method: "POST", body: JSON.stringify({ prompt_text: form.prompt_text, locale: localeForCode(form.country_code) }) });
    setForm({ prompt_text: "", country_code: form.country_code });
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
      const summary = `${res.note} 新增 ${res.created} 条，跳过 ${res.skipped} 条。当前买家问题 ${res.prompts} 条。`;
      if (res.created === 0 && res.prompts === 0) {
        setError(summary);
      } else {
        setNote(summary);
      }
      loadPrompts();
    } catch (e) {
      setError(e instanceof Error ? e.message : "采用已记原句失败");
    } finally {
      setBusyAction("");
    }
  }

  async function downloadGeoReport() {
    setError("");
    const date = new Date().toISOString().slice(0, 10);
    try {
      await downloadApiFile("/api/geo/report.pdf", `AI搜索说明-${date}.pdf`);
      setNote("AI 搜索说明（PDF）已下载。");
    } catch (e) {
      setError(e instanceof Error ? e.message : "AI 搜索说明下载失败");
    }
  }

  async function downloadGeoTable() {
    setError("");
    try {
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
      setNote("AI 搜索检查记录已下载。");
    } catch (e) {
      setError(e instanceof Error ? e.message : "检查记录下载失败");
    }
  }

  async function createEvidenceRun() {
    setError("");
    setNote("");
    setBusyAction("evidence-run");
    try {
      const run = await api<GeoSampleRun>("/api/geo/sample-runs/from-observations", {
        method: "POST",
        body: JSON.stringify({ note: "从当前人工记录保存一批可追溯的检查结果。" }),
      });
      setNote(`已保存一批检查记录：${run.results_count} 条，批次 ${run.id}。`);
      loadPrompts();
      loadRuns();
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存记录失败");
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
      setError(e instanceof Error ? e.message : "生成待处理项失败");
    } finally {
      setBusyAction("");
    }
  }

  async function runGroundedBatch() {
    setError("");
    setNote("");
    setBusyAction("grounded-batch");
    try {
      const batch = await api<GeoGroundedBatch>("/api/geo/sample-runs/auto-grounded", {
        method: "POST",
        timeoutMs: 180000,
        body: JSON.stringify({ trials: 1, limit: 8, web_grounded: "true" }),
      });
      setNote(batch.note);
      if (batch.results_count === 0) {
        setError(batch.failed.length ? `这次没有写出记录。失败：${batch.failed.join("、")}` : "这次没有写出记录。");
      }
      loadRuns();
      loadPrompts();
      loadTickets();
    } catch (e) {
      setError(e instanceof Error ? e.message : "联网源抽查失败");
    } finally {
      setBusyAction("");
    }
  }

  async function retestSameQuestions() {
    const latest = runs[0];
    const promptIds = Array.from(new Set((latest?.results ?? []).map((row) => row.prompt_id).filter(Boolean)));
    if (!promptIds.length) {
      setError("还没有上一批买家问题，先抽查一次再复测。");
      return;
    }
    setError("");
    setNote("");
    setBusyAction("retest-same");
    try {
      const batch = await api<GeoGroundedBatch>("/api/geo/sample-runs/auto-grounded", {
        method: "POST",
        timeoutMs: 180000,
        body: JSON.stringify({
          prompt_ids: promptIds,
          trials: 1,
          limit: promptIds.length,
          web_grounded: "true",
        }),
      });
      setNote(`${batch.note} 复测只记有没有变化，不承诺这次会提到。`);
      if (batch.results_count === 0) {
        setError("同一问再测没有写出记录。看上面的说明，不要把空批次写成未测。");
      }
      loadRuns();
      loadPrompts();
      loadTickets();
    } catch (e) {
      setError(e instanceof Error ? e.message : "同一问再测失败");
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
          region_hint: targets?.markets[0]?.country_code || form.country_code || "",
        }),
      });
      if (run.results_count === 0) {
        setError(`${selected?.label ?? sampleProvider} 这次没有写出记录。${run.note || "看批次备注。"}`.trim());
        setNote("");
      } else {
        const extra = run.note && run.note.includes("失败") ? ` ${run.note}` : "";
        setNote(`${selected?.label ?? sampleProvider} 检查完成：${run.results_count} 条记录。${selected?.web_grounded ? "返回来源网址时，可算作给出了官网。" : "该结果用于分析和是否被提到，不算给出官网。"}${extra}`);
      }
      loadRuns();
      loadPrompts();
      loadTickets();
    } catch (e) {
      setError(e instanceof Error ? e.message : "自动检查失败");
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

  async function verifyOwnedCitation(resultId: string, checkedUrl: string, passed: boolean) {
    setError("");
    setNote("");
    setBusyAction(resultId);
    try {
      await api(`/api/geo/sample-results/${resultId}/verify`, {
        method: "POST",
        body: JSON.stringify({
          confirmed: true,
          checked_url: checkedUrl,
          passed,
          note: confirmNote || null,
        }),
      });
      setNote(passed ? "已记下：客户官网打开核对通过。" : "已记下：该官网链接打不开或不是客户页。");
      loadRuns();
      loadPrompts();
    } catch (e) {
      setError(e instanceof Error ? e.message : "官网核对失败");
    } finally {
      setBusyAction("");
    }
  }

  async function setHandoff(id: string, handoff: "drafted" | "sent" | "live", resultUrl = "") {
    setError("");
    try {
      await api(`/api/geo/tickets/${id}/handoff`, {
        method: "POST",
        body: JSON.stringify({ handoff, note: confirmNote, result_url: resultUrl }),
      });
      loadTickets();
    } catch (e) {
      setError(e instanceof Error ? e.message : "进度没记上");
    }
  }

  async function saveOffsite(id: string, postUrl: string) {
    setError("");
    try {
      await api(`/api/geo/tickets/${id}/offsite`, {
        method: "POST",
        body: JSON.stringify({ post_url: postUrl }),
      });
      setNote("已记下帖子链接。登记不等于我们代发。");
      loadTickets();
    } catch (e) {
      setError(e instanceof Error ? e.message : "帖子链接没记上");
    }
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
      const owned = providerResults.filter((result) => result.owned_citations.length > 0).length;
      const status = !provider.configured
        ? "未配置"
        : providerResults.length === 0
          ? "这次没选"
          : verified > 0
            ? "已核对来源"
            : owned > 0
              ? "有来源待核对"
              : citations > 0
                ? "有外来网址"
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
        setSampleProvider={(value) => {
          setProviderPicked(true);
          setSampleProvider(value);
        }}
        selectedProvider={selectedProvider}
        runAutoSample={runAutoSample}
        runGroundedBatch={runGroundedBatch}
        retestSameQuestions={retestSameQuestions}
        canRetestSame={Boolean(runs[0]?.results?.length)}
        downloadGeoReport={downloadGeoReport}
        downloadGeoTable={downloadGeoTable}
        note={note}
        error={error}
      />

      <details className="rounded-md border border-dashed border-slate-200 bg-white p-4">
        <summary className="cursor-pointer text-sm font-medium text-slate-700">客户经理工具：数据源状态 / 抽查质量 / 目标词</summary>
        <div className="mt-4 space-y-4">
          <ProviderStatusCard providers={providers} />
          <EvidenceQualityCard
            evidenceVerdict={evidenceVerdict}
            runs={runs}
            summary={summary}
            providerQuality={providerQuality}
          />
          <TargetsCard targets={targets} />
          <MetricsGrid summary={summary} />
          <Input placeholder="确认 / 复查备注（登记上线时可选）" value={confirmNote} onChange={(e) => setConfirmNote(e.target.value)} />
        </div>
      </details>

      <SampleRunsCard runs={runs} busyId={busyAction} verifyOwnedCitation={verifyOwnedCitation} />

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
          setHandoff={setHandoff}
          saveOffsite={saveOffsite}
          retestSameQuestions={retestSameQuestions}
          canRetestSame={Boolean(runs[0]?.results?.length)}
          busyAction={busyAction}
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
    </div>
  );
}
