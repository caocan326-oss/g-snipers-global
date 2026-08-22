"use client";

import { useEffect, useMemo, useState } from "react";

import {
  api,
  looksLikeSiteOrigin,
  type ExecutionBoard,
  type GscAuthUrl,
  type GscStatus,
  type ProjectTargets,
  type SiteArchive,
  type Workbench,
} from "@/lib/api";
import { crawlFinishedNote, isHostSwitch, recrawlSavedSite } from "@/lib/site-origin";

import { emptyTargetForm, formFromTargets, projectTargetsPayload, reportReadyChecks, seoPerformanceVerdict } from "./_helpers";
import { DeliveryBoundarySection } from "./_components/DeliveryBoundarySection";
import { DiagnosticTargetsSection } from "./_components/DiagnosticTargetsSection";
import { PillarsOverview } from "./_components/PillarsOverview";
import { PriorityQueueSection } from "./_components/PriorityQueueSection";
import { PriorityAndDataSourceSection } from "./_components/PriorityAndDataSourceSection";
import { QuickLinksSection } from "./_components/QuickLinksSection";
import { ReportReadinessSection } from "./_components/ReportReadinessSection";
import { SeoPerformanceSection } from "./_components/SeoPerformanceSection";
import { SiteArchivesSection } from "./_components/SiteArchivesSection";
import { WorkbenchSummaryHeader } from "./_components/WorkbenchSummaryHeader";

export default function HomePage() {
  const [data, setData] = useState<Workbench | null>(null);
  const [executionBoard, setExecutionBoard] = useState<ExecutionBoard | null>(null);
  const [targets, setTargets] = useState<ProjectTargets | null>(null);
  const [gsc, setGsc] = useState<GscStatus | null>(null);
  const [error, setError] = useState("");
  const [loadError, setLoadError] = useState("");
  const [executionError, setExecutionError] = useState("");
  const [note, setNote] = useState("");
  const [days, setDays] = useState(28);
  const [targetForm, setTargetForm] = useState(emptyTargetForm);
  const [executionLoading, setExecutionLoading] = useState(false);
  const [switchPending, setSwitchPending] = useState(false);
  const [savingTargets, setSavingTargets] = useState(false);
  const [archives, setArchives] = useState<SiteArchive[]>([]);
  const [archiveBusyId, setArchiveBusyId] = useState("");

  useEffect(() => {
    api<Workbench>(`/api/dashboard/workbench?days=${days}`)
      .then(setData)
      .catch((e) => setLoadError(e.message));
  }, [days]);

  useEffect(() => {
    loadExecutionBoard();
    api<ProjectTargets>("/api/project-targets")
      .then((res) => {
        setTargets(res);
        setTargetForm(formFromTargets(res));
      })
      .catch((e) => setLoadError(e.message));
    api<GscStatus>("/api/onsite/gsc/status")
      .then(setGsc)
      .catch(() => undefined);
    loadArchives();
  }, []);

  const reviewTotal = useMemo(() => {
    if (executionBoard) return executionBoard.total_open;
    return 0;
  }, [executionBoard]);

  if (loadError) return <p className="text-sm text-red-600">{loadError}</p>;
  if (!data) return <p className="text-sm text-slate-500">加载中…</p>;

  const perf = data.seo_performance;
  const seoVerdict = seoPerformanceVerdict(perf);
  const reportChecks = reportReadyChecks(data, targets, gsc);
  const passedChecks = reportChecks.filter((item) => item.ok).length;
  const reportReady = reportChecks.every((item) => item.ok);
  const highRisk = data.summary.onsite_open_critical + data.summary.onsite_open_high;
  const geoSampled = data.summary.geo_latest_sampled ?? 0;
  const untestedTotal = (geoSampled > 0 ? 0 : data.summary.geo_prompts) + (data.summary.onsite_pages === 0 ? 1 : 0);
  const geoRecorded = data.summary.geo_recorded;
  const geoStatusTone = geoSampled > 0 ? "green" : data.summary.geo_prompts > 0 ? "amber" : "default";
  const technicalTone = highRisk > 0 ? "red" : data.summary.onsite_pages > 0 ? "green" : "amber";
  const workTone = reviewTotal > 0 ? "amber" : "green";
  const executiveSummary = [
    {
      label: "网站风险",
      text: highRisk > 0 ? `当前有 ${highRisk} 个紧急或优先网站问题，先处理打不开、是否收录、标题和页面说明。` : "当前没有打开的紧急或优先网站问题，重点进入复查和说明整理。",
      tone: technicalTone,
    },
    {
      label: "AI 搜索",
      text: geoSampled > 0
        ? `最近联网搜索写了 ${geoSampled} 条记录。ChatGPT 等引擎空位不是这周的缺口。`
        : data.summary.geo_prompts > 0
          ? `${data.summary.geo_prompts} 个买家问题还没联网抽查。`
          : "还没有买家问题。",
      tone: geoStatusTone,
    },
    {
      label: "下一步",
      text: reviewTotal > 0 ? `处理清单里还有 ${reviewTotal} 条未关闭事项，先处理紧急网站改法、AI 搜索和站外曝光。` : "本周期暂无阻塞动作，可以进入客户说明或复查。",
      tone: workTone,
    },
  ];

  async function reloadWorkbench() {
    const [nextWorkbench, nextTargets, nextExecutionBoard] = await Promise.all([
      api<Workbench>(`/api/dashboard/workbench?days=${days}`),
      api<ProjectTargets>("/api/project-targets"),
      api<ExecutionBoard>("/api/execution/items"),
    ]);
    setData(nextWorkbench);
    setTargets(nextTargets);
    setExecutionBoard(nextExecutionBoard);
    setExecutionError("");
    setTargetForm(formFromTargets(nextTargets));
  }

  function loadExecutionBoard() {
    setExecutionLoading(true);
    setExecutionError("");
    api<ExecutionBoard>("/api/execution/items")
      .then(setExecutionBoard)
      .catch((e) => setExecutionError(e instanceof Error ? e.message : "待处理队列加载失败"))
      .finally(() => setExecutionLoading(false));
  }

  function loadArchives() {
    api<SiteArchive[]>("/api/site-context/archives")
      .then(setArchives)
      .catch(() => undefined);
  }

  async function saveTargets() {
    setError("");
    setNote("");
    if (!targetForm.site_origin.trim()) return setError("请先填写客户官网。");
    if (!looksLikeSiteOrigin(targetForm.site_origin)) return setError("官网地址无效。请填写带域名的网址，例如 https://www.ugreen.com。");
    if (isHostSwitch(targets?.site_origin || "", targetForm.site_origin)) {
      setSwitchPending(true);
      return;
    }
    await persistTargets(false);
  }

  function cancelSwitch() {
    setSwitchPending(false);
    setNote("没换站，还是当前网站。");
  }

  async function persistTargets(confirmSwitch: boolean) {
    const payload = projectTargetsPayload(targetForm, targets);
    if (!confirmSwitch) {
      if (!payload.markets.length) return setError("请至少点选 1 个目标国家。");
      if (!payload.keywords.length) return setError("请至少填写 1 个核心关键词。");
    }
    setSavingTargets(true);
    setError("");
    setNote("");
    try {
      const saved = await api<ProjectTargets>("/api/project-targets", {
        method: "PUT",
        body: JSON.stringify({
          tenant_name: targetForm.tenant_name,
          site_origin: targetForm.site_origin,
          markets: payload.markets,
          keywords: confirmSwitch ? [] : payload.keywords,
          competitors: confirmSwitch ? [] : payload.competitors,
          confirm_site_switch: confirmSwitch,
        }),
      });
      setTargets(saved);
      setTargetForm(formFromTargets(saved));
      setSwitchPending(false);
      setNote(confirmSwitch || !targets?.site_origin ? "已保存，正在重新抓取。" : saved.note || "诊断目标已保存。");
      if (confirmSwitch || !targets?.site_origin) {
        try {
          const session = await recrawlSavedSite();
          setNote(crawlFinishedNote(session));
        } catch (e) {
          setNote("已保存。自动抓取没跑成，请到网站检查点「扩大页面范围」。");
          setError(e instanceof Error ? e.message : "自动抓取失败");
        }
      }
      await reloadWorkbench();
      loadArchives();
    } catch (e) {
      setError(e instanceof Error ? e.message : "诊断目标保存失败");
    } finally {
      setSavingTargets(false);
    }
  }

  async function restoreArchive(item: SiteArchive) {
    setArchiveBusyId(item.id);
    setError("");
    try {
      const res = await api<{ note?: string }>(`/api/site-context/archives/${item.id}/restore`, { method: "POST" });
      setNote(res.note || `已恢复 ${item.site_origin}`);
      await reloadWorkbench();
      loadArchives();
    } catch (e) {
      setError(e instanceof Error ? e.message : "恢复历史网站失败");
    } finally {
      setArchiveBusyId("");
    }
  }

  async function deleteArchive(item: SiteArchive) {
    if (!window.confirm(`删除历史网站 ${item.site_origin}？删了不能恢复。`)) return;
    setArchiveBusyId(item.id);
    setError("");
    try {
      await api(`/api/site-context/archives/${item.id}`, {
        method: "DELETE",
        body: JSON.stringify({ confirm: "DELETE" }),
      });
      setNote(`已删除历史网站 ${item.site_origin}`);
      loadArchives();
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除历史网站失败");
    } finally {
      setArchiveBusyId("");
    }
  }

  async function authorizeGsc() {
    setError("");
    setNote("");
    try {
      const res = await api<GscAuthUrl>("/api/onsite/gsc/auth-url");
      if (!res.configured || !res.auth_url) return setError(res.note || "服务器未配置 Google Search Console OAuth。");
      window.location.href = res.auth_url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "获取 GSC 授权链接失败");
    }
  }

  return (
    <div className="space-y-6">
      <WorkbenchSummaryHeader data={data} targets={targets} executiveSummary={executiveSummary} />

      <DiagnosticTargetsSection
        targets={targets}
        targetForm={targetForm}
        setTargetForm={setTargetForm}
        saveTargets={saveTargets}
        confirmSwitch={() => void persistTargets(true)}
        cancelSwitch={cancelSwitch}
        switchPending={switchPending}
        saving={savingTargets}
        note={note}
        error={error}
      />

      <SiteArchivesSection
        archives={archives}
        archiveBusyId={archiveBusyId}
        restoreArchive={restoreArchive}
        deleteArchive={deleteArchive}
        loadArchives={loadArchives}
      />

      <PriorityQueueSection board={executionBoard} loading={executionLoading} error={executionError} reload={loadExecutionBoard} />

      <PillarsOverview
        data={data}
        highRisk={highRisk}
        technicalTone={technicalTone}
        geoStatusTone={geoStatusTone}
        geoRecorded={geoRecorded}
        workTone={workTone}
        reviewTotal={reviewTotal}
        perf={perf}
      />

      <ReportReadinessSection reportChecks={reportChecks} passedChecks={passedChecks} reportReady={reportReady} />

      <SeoPerformanceSection perf={perf} seoVerdict={seoVerdict} />

      <PriorityAndDataSourceSection data={data} gsc={gsc} untestedTotal={untestedTotal} perf={perf} authorizeGsc={authorizeGsc} />

      <DeliveryBoundarySection data={data} days={days} setDays={setDays} />

      <QuickLinksSection />
    </div>
  );
}
