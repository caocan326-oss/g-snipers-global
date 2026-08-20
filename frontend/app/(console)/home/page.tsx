"use client";

import { useEffect, useMemo, useState } from "react";

import {
  api,
  confirmSiteSwitch,
  looksLikeSiteOrigin,
  siteOriginHost,
  type ExecutionBoard,
  type GscAuthUrl,
  type GscStatus,
  type ProjectTargets,
  type SiteArchive,
  type SiteArchiveRestore,
  type Workbench,
} from "@/lib/api";

import { activeTargetMarkets, reportReadyChecks, seoPerformanceVerdict, splitKeywordInput } from "./_helpers";
import { DeliveryBoundarySection } from "./_components/DeliveryBoundarySection";
import { DiagnosticTargetsSection, type TargetForm } from "./_components/DiagnosticTargetsSection";
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
  const [archives, setArchives] = useState<SiteArchive[]>([]);
  const [gsc, setGsc] = useState<GscStatus | null>(null);
  const [error, setError] = useState("");
  const [executionError, setExecutionError] = useState("");
  const [note, setNote] = useState("");
  const [days, setDays] = useState(28);
  const [targetForm, setTargetForm] = useState<TargetForm>({ site_origin: "", markets: "", keywords: "", competitors: "" });
  const [archiveBusyId, setArchiveBusyId] = useState("");
  const [executionLoading, setExecutionLoading] = useState(false);

  useEffect(() => {
    api<Workbench>(`/api/dashboard/workbench?days=${days}`)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [days]);

  useEffect(() => {
    loadExecutionBoard();
    api<ProjectTargets>("/api/project-targets")
      .then((res) => {
        setTargets(res);
        const targetMarkets = activeTargetMarkets(res);
        setTargetForm({
          site_origin: res.site_origin || "",
          markets: targetMarkets.map((m) => [m.name, m.region, m.country_code, m.primary_locale].filter(Boolean).join(" | ")).join("\n"),
          keywords: targetMarkets.flatMap((m) => m.demand_signals.map((s) => s.theme)).join("\n"),
          competitors: targetMarkets.flatMap((m) => m.competitors.map((c) => [c.name, c.website].filter(Boolean).join(" | "))).join("\n"),
        });
      })
      .catch((e) => setError(e.message));
    api<GscStatus>("/api/onsite/gsc/status")
      .then(setGsc)
      .catch(() => undefined);
    loadArchives();
  }, []);

  const reviewTotal = useMemo(() => {
    if (executionBoard) return executionBoard.total_open;
    if (!data) return 0;
    return data.summary.onsite_open_critical + data.summary.onsite_open_high + data.summary.geo_tickets_open + data.summary.offsite_gaps;
  }, [data, executionBoard]);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!data) return <p className="text-sm text-slate-500">加载中…</p>;

  const perf = data.seo_performance;
  const seoVerdict = seoPerformanceVerdict(perf);
  const reportChecks = reportReadyChecks(data, targets, gsc);
  const passedChecks = reportChecks.filter((item) => item.ok).length;
  const reportReady = reportChecks.every((item) => item.ok);
  const highRisk = data.summary.onsite_open_critical + data.summary.onsite_open_high;
  const untestedTotal = data.summary.geo_untested + (data.summary.onsite_pages === 0 ? 1 : 0);
  const geoRecorded = data.summary.geo_recorded;
  const geoStatusTone = data.summary.geo_untested > 0 ? "amber" : geoRecorded > 0 ? "green" : "default";
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
      text: geoRecorded > 0 ? `已有 ${geoRecorded} 条 AI 搜索记录，可整理有没有被提到、有没有给出官网。` : `还有 ${data.summary.geo_untested} 条检查尚未做（${data.summary.geo_prompts} 个买家问题），说明里只能写尚未检查。`,
      tone: geoStatusTone,
    },
    {
      label: "下一步",
      text: reviewTotal > 0 ? `处理清单里还有 ${reviewTotal} 条未关闭事项，先处理紧急网站改法、AI 搜索和站外曝光。` : "本周期暂无阻塞动作，可以进入客户说明或复查。",
      tone: workTone,
    },
  ];

  function parseMarkets(text: string) {
    return text
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const [name, region = "", country_code = "", primary_locale = "en-US"] = line.split("|").map((item) => item.trim());
        return { name, region, country_code: country_code || name.slice(0, 2).toUpperCase(), primary_locale, status: "priority", opportunity_score: 70 };
      });
  }

  function parseKeywords(text: string) {
    return splitKeywordInput(text).map((theme) => ({ theme, locale: "en-US", intent: "commercial", intensity: 4 }));
  }

  function parseCompetitors(text: string) {
    return text
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const [name, website = ""] = line.split("|").map((item) => item.trim());
        return { name, website };
      });
  }

  async function reloadWorkbench() {
    const [nextWorkbench, nextTargets, nextArchives, nextExecutionBoard] = await Promise.all([
      api<Workbench>(`/api/dashboard/workbench?days=${days}`),
      api<ProjectTargets>("/api/project-targets"),
      api<SiteArchive[]>("/api/site-context/archives"),
      api<ExecutionBoard>("/api/execution/items"),
    ]);
    setData(nextWorkbench);
    setTargets(nextTargets);
    setArchives(nextArchives);
    setExecutionBoard(nextExecutionBoard);
    setExecutionError("");
    const targetMarkets = activeTargetMarkets(nextTargets);
    setTargetForm({
      site_origin: nextTargets.site_origin || "",
      markets: targetMarkets.map((m) => [m.name, m.region, m.country_code, m.primary_locale].filter(Boolean).join(" | ")).join("\n"),
      keywords: targetMarkets.flatMap((m) => m.demand_signals.map((s) => s.theme)).join("\n"),
      competitors: targetMarkets.flatMap((m) => m.competitors.map((c) => [c.name, c.website].filter(Boolean).join(" | "))).join("\n"),
    });
  }

  function loadArchives() {
    api<SiteArchive[]>("/api/site-context/archives")
      .then(setArchives)
      .catch(() => undefined);
  }

  function loadExecutionBoard() {
    setExecutionLoading(true);
    setExecutionError("");
    api<ExecutionBoard>("/api/execution/items")
      .then(setExecutionBoard)
      .catch((e) => setExecutionError(e instanceof Error ? e.message : "待处理队列加载失败"))
      .finally(() => setExecutionLoading(false));
  }

  async function restoreArchive(item: SiteArchive) {
    setError("");
    setNote("");
    setArchiveBusyId(item.id);
    try {
      const res = await api<SiteArchiveRestore>(`/api/site-context/archives/${item.id}/restore`, { method: "POST" });
      await reloadWorkbench();
      setNote(res.note || `已恢复 ${res.site_origin}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "恢复历史网站失败");
    } finally {
      setArchiveBusyId("");
    }
  }

  async function deleteArchive(item: SiteArchive) {
    const confirmText = window.prompt(`删除 ${item.site_origin} 的历史数据？\n会删除该历史快照中的抓取记录、AI 搜索检查、测速、排名和说明记录。\n请输入网站域名或 DELETE 确认。`);
    if (!confirmText) return;
    setError("");
    setNote("");
    setArchiveBusyId(item.id);
    try {
      await api(`/api/site-context/archives/${item.id}`, { method: "DELETE", body: JSON.stringify({ confirm: confirmText }) });
      await reloadWorkbench();
      setNote(`已删除历史网站：${item.site_origin}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除历史网站失败");
    } finally {
      setArchiveBusyId("");
    }
  }

  async function saveTargets() {
    setError("");
    setNote("");
    try {
      const parsedMarkets = parseMarkets(targetForm.markets);
      const parsedKeywords = parseKeywords(targetForm.keywords);
      const parsedCompetitors = parseCompetitors(targetForm.competitors);
      if (!targetForm.site_origin.trim()) return setError("请先填写客户官网。");
      if (!looksLikeSiteOrigin(targetForm.site_origin)) return setError("官网地址无效。请填写带域名的网址，例如 https://www.snipers.com.cn。");
      if (!parsedMarkets.length) return setError("请至少填写 1 个目标国家，例如：United States | North America | US | en-US");
      if (!parsedKeywords.length) return setError("请至少填写 1 个核心关键词。");
      const currentHost = siteOriginHost(targets?.site_origin || "");
      const nextHost = siteOriginHost(targetForm.site_origin);
      const switching = Boolean(currentHost && nextHost && currentHost !== nextHost);
      if (switching && !confirmSiteSwitch(targets?.site_origin || "", targetForm.site_origin.trim())) return;
      const saved = await api<ProjectTargets>("/api/project-targets", {
        method: "PUT",
        body: JSON.stringify({
          site_origin: targetForm.site_origin,
          markets: parsedMarkets,
          keywords: parsedKeywords,
          competitors: parsedCompetitors,
          confirm_site_switch: switching,
        }),
      });
      setTargets(saved);
      const targetMarkets = activeTargetMarkets(saved);
      setTargetForm({
        site_origin: saved.site_origin || targetForm.site_origin,
        markets: targetMarkets.map((m) => [m.name, m.region, m.country_code, m.primary_locale].filter(Boolean).join(" | ")).join("\n"),
        keywords: targetMarkets.flatMap((m) => m.demand_signals.map((s) => s.theme)).join("\n"),
        competitors: targetMarkets.flatMap((m) => m.competitors.map((c) => [c.name, c.website].filter(Boolean).join(" | "))).join("\n"),
      });
      setNote(saved.note || "诊断目标已保存。");
      await reloadWorkbench();
    } catch (e) {
      setError(e instanceof Error ? e.message : "诊断目标保存失败");
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

      <DiagnosticTargetsSection targets={targets} targetForm={targetForm} setTargetForm={setTargetForm} saveTargets={saveTargets} note={note} error={error} />

      <SiteArchivesSection
        archives={archives}
        archiveBusyId={archiveBusyId}
        restoreArchive={restoreArchive}
        deleteArchive={deleteArchive}
        loadArchives={loadArchives}
      />

      <DeliveryBoundarySection data={data} days={days} setDays={setDays} />

      <QuickLinksSection />
    </div>
  );
}
