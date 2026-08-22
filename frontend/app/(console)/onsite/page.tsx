"use client";

import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";

import {
  api,
  downloadApiFile,
  looksLikeSiteOrigin,
  type AiAssist,
  type BingStatus,
  type ContentBrief,
  type CrawlSession,
  type DataSyncRunDueResult,
  type DataSyncStatus,
  type FetchRegistered,
  type GscAuthUrl,
  type GscStatus,
  type GscSyncResult,
  type IntegrationSettings,
  type IndexNowStatus,
  type IndexNowSubmitResult,
  type Market,
  type OnsiteBoard,
  type OnsiteGuide,
  type OnsiteIssue,
  type ProjectTargets,
  type SeoReportTable,
  type SeoPerformanceSummary,
  type SeoPage,
  type SerpRunBatch,
  type SitePage,
} from "@/lib/api";
import { explainServiceError } from "@/lib/errors";
import { crawlFinishedNote, isHostSwitch, recrawlSavedSite } from "@/lib/site-origin";

import { DiagnosisSection } from "./_components/DiagnosisSection";
import { IssueBoard } from "./_components/IssueBoard";
import { GuideHeader } from "./_components/GuideHeader";
import { PagesAndBriefsSection } from "./_components/PagesAndBriefsSection";
import { PerformanceDataCard } from "./_components/PerformanceDataCard";
import { RankAuthoritySection } from "./_components/RankAuthoritySection";
import { SiteSetupCard } from "./_components/SiteSetupCard";
import { StatsGrid } from "./_components/StatsGrid";
import { TargetMarketsCard } from "./_components/TargetMarketsCard";
import {
  type FilterKey,
  matchesFilter,
  performanceVerdict,
  plainIssueTitle,
  priorityRank,
  SNIPERS_TEST_ORIGIN,
  SNIPERS_TEST_PAGES,
  statusLabel,
} from "./_helpers";

export default function OnsiteBoardPage() {
  const [board, setBoard] = useState<OnsiteBoard | null>(null);
  const [pages, setPages] = useState<SitePage[]>([]);
  const [briefs, setBriefs] = useState<ContentBrief[]>([]);
  const [markets, setMarkets] = useState<Market[]>([]);
  const [seoTargets, setSeoTargets] = useState<SeoPage[]>([]);
  const [performance, setPerformance] = useState<SeoPerformanceSummary | null>(null);
  const [gsc, setGsc] = useState<GscStatus | null>(null);
  const [integrations, setIntegrations] = useState<IntegrationSettings | null>(null);
  const [bing, setBing] = useState<BingStatus | null>(null);
  const [indexNow, setIndexNow] = useState<IndexNowStatus | null>(null);
  const [syncStatus, setSyncStatus] = useState<DataSyncStatus | null>(null);
  const [targets, setTargets] = useState<ProjectTargets | null>(null);
  const [sessions, setSessions] = useState<CrawlSession[]>([]);
  const [filter, setFilter] = useState<FilterKey>("all");
  const [expandedId, setExpandedId] = useState("");
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [query, setQuery] = useState("");
  const [busyId, setBusyId] = useState("");
  const [draftProgress, setDraftProgress] = useState<{ written: number; remaining: number } | null>(null);
  const [maxUrls, setMaxUrls] = useState(50);
  const [maxDepth, setMaxDepth] = useState(2);
  const [showGscSetup, setShowGscSetup] = useState(false);
  const [integrationForm, setIntegrationForm] = useState({
    gsc_oauth_client_id: "",
    gsc_oauth_client_secret: "",
    gsc_oauth_redirect_uri: "",
    pagespeed_api_key: "",
    ce17_user: "",
    ce17_api_pwd: "",
    brightdata_dataset_api_key: "",
    brightdata_serp_zone: "",
    brightdata_serp_dataset_id: "",
    brightdata_serp_endpoint: "",
  });
  const [performanceSource, setPerformanceSource] = useState<"gsc_csv" | "bing_csv">("gsc_csv");
  const [form, setForm] = useState({ path: "/", locale: "en-US", title: "" });
  const [origin, setOrigin] = useState("");
  const [savedOrigin, setSavedOrigin] = useState("");
  const [switchPending, setSwitchPending] = useState(false);
  const [guide, setGuide] = useState<OnsiteGuide | null>(null);
  const [voicePending, setVoicePending] = useState(false);

  function load() {
    Promise.all([
      api<OnsiteBoard>("/api/onsite/board"),
      api<SitePage[]>("/api/onsite/pages"),
      api<ContentBrief[]>("/api/onsite/briefs"),
      api<{ site_origin: string }>("/api/onsite/settings"),
      api<CrawlSession[]>("/api/onsite/crawl-sessions"),
      api<Market[]>("/api/markets"),
      api<SeoPage[]>("/api/seo-pages"),
      api<SeoPerformanceSummary>("/api/onsite/performance"),
      api<IntegrationSettings>("/api/onsite/integrations"),
      api<GscStatus>("/api/onsite/gsc/status"),
      api<BingStatus>("/api/onsite/bing/status"),
      api<IndexNowStatus>("/api/onsite/indexnow/status"),
      api<DataSyncStatus>("/api/onsite/data-sync/status"),
      api<ProjectTargets>("/api/project-targets"),
      api<OnsiteGuide>("/api/onsite/guide"),
    ])
      .then(([b, p, br, s, cs, m, seo, perf, integrationStatus, gscStatus, bingStatus, indexNowStatus, ds, targetConfig, nextGuide]) => {
        setBoard(b);
        setPages(p);
        setBriefs(br);
        setOrigin(s.site_origin || "");
        setSavedOrigin(s.site_origin || "");
        setSessions(cs);
        setMarkets(m);
        setSeoTargets(seo);
        setPerformance(perf);
        setIntegrations(integrationStatus);
        setGsc(gscStatus);
        setBing(bingStatus);
        setIndexNow(indexNowStatus);
        setSyncStatus(ds);
        setTargets(targetConfig);
        setGuide(nextGuide);
        if (nextGuide.ai_status === "pending" || nextGuide.ai_status === "未配置") {
          if (nextGuide.ai_status === "pending") {
            setVoicePending(true);
            api<OnsiteGuide>("/api/onsite/guide/voice", { method: "POST" })
              .then((voiced) => setGuide(voiced))
              .catch(() => undefined)
              .finally(() => setVoicePending(false));
          }
        }
      })
      .catch((e) => setError(e.message));
  }

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    if (!code) return;
    api<GscStatus>("/api/onsite/gsc/connect", {
      method: "POST",
      body: JSON.stringify({ code, site_url: origin }),
    })
      .then((status) => {
        setGsc(status);
        setNote("Google Search Console 已连接。");
        window.history.replaceState({}, "", window.location.pathname);
        load();
      })
      .catch((e) => setError(e instanceof Error ? e.message : "GSC 授权接入失败"));
  }, [origin]);

  const issues = useMemo(() => {
    if (!board) return [];
    return Object.values(board.groups)
      .flat()
      .sort((a, b) => priorityRank(a) - priorityRank(b) || (a.page_path ?? "").localeCompare(b.page_path ?? ""));
  }, [board]);

  const visibleIssues = useMemo(() => {
    const q = query.trim().toLowerCase();
    return issues.filter((issue) => {
      if (!matchesFilter(issue, filter)) return false;
      if (!q) return true;
      return [
        issue.title,
        plainIssueTitle(issue.title),
        issue.page_title,
        issue.page_path,
        issue.category,
        issue.detail,
        issue.proposed_change,
        issue.ai_review,
        issue.recommended_action,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(q);
    });
  }, [filter, issues, query]);

  const stats = useMemo(() => {
    const fetched = pages.filter((p) => p.crawl_status === "ok").length;
    const waitingDraft = issues.filter((i) => i.status === "open" && !i.proposed_change.trim()).length;
    const readyToExecute = issues.filter((i) => i.status === "drafted").length;
    const waitingRetest = issues.filter((i) => i.status === "confirmed" || i.status === "draft_applied").length;
    const untested = issues.filter((i) => i.metric_status === "untested").length;
    const needsReview = issues.filter((i) => i.review_required && i.status === "drafted").length;
    const solved = board?.workflow_counts?.verified ?? issues.filter((i) => i.status === "verified").length;
    return { fetched, waitingDraft, readyToExecute, waitingRetest, untested, needsReview, solved };
  }, [board?.workflow_counts, issues, pages]);

  const targetMarkets = useMemo(() => {
    if (targets?.markets.length) {
      const priority = targets.markets.filter((m) => m.status === "priority");
      return (priority.length ? priority : targets.markets).slice(0, 4);
    }
    const priority = markets.filter((m) => m.status === "priority");
    return (priority.length ? priority : markets).slice(0, 4);
  }, [markets, targets?.markets]);

  const targetKeywords = useMemo(() => {
    const demand = targets?.markets.flatMap((m) => m.demand_signals.map((s) => ({ id: s.id, label: s.theme, status: "target" }))) ?? [];
    if (demand.length) return demand.slice(0, 8);
    return seoTargets.filter((item) => item.target_keyword.trim()).slice(0, 8).map((item) => ({ id: item.id, label: item.target_keyword, status: item.status }));
  }, [seoTargets, targets?.markets]);

  const diagnosisReadiness = useMemo(() => {
    if (!board) {
      return { pageCoverage: 0, hasSearchData: false, hasSpeed: false, hasSerp: false, unresolved: 0, ready: false };
    }
    const pageCoverage = board.pages ? Math.round((stats.fetched / board.pages) * 100) : 0;
    const hasSearchData = performance?.gsc_status === "已导入" || performance?.bing_status === "已导入";
    const hasSpeed = performance?.pagespeed_status === "已测速";
    const hasSerp = Boolean(performance?.serp?.total_runs);
    const unresolved = board.counts.critical + board.counts.high + board.counts.low;
    return {
      pageCoverage,
      hasSearchData,
      hasSpeed,
      hasSerp,
      unresolved,
      ready:
        board.pages > 0 &&
        stats.fetched > 0 &&
        (hasSearchData || hasSerp || hasSpeed) &&
        (stats.waitingDraft + stats.readyToExecute + stats.waitingRetest + unresolved >= 0),
    };
  }, [board, performance, stats.fetched, stats.readyToExecute, stats.waitingDraft, stats.waitingRetest]);

  const searchVerdict = performanceVerdict(performance);

  async function saveOrigin() {
    setError("");
    setNote("");
    if (!looksLikeSiteOrigin(origin)) {
      setError("官网地址无效。请填写带域名的网址，例如 https://www.ugreen.com。");
      return;
    }
    if (isHostSwitch(savedOrigin, origin)) {
      setSwitchPending(true);
      return;
    }
    await persistOrigin(origin, false);
  }

  function cancelSwitch() {
    setSwitchPending(false);
    setNote("没换站，还是当前网站。");
  }

  async function persistOrigin(nextOrigin: string, confirmSwitch: boolean) {
    setBusyId("save-origin");
    setError("");
    try {
      const res = await api<{ site_origin: string; note?: string }>("/api/onsite/settings", {
        method: "PATCH",
        body: JSON.stringify({ site_origin: nextOrigin, confirm_site_switch: confirmSwitch }),
      });
      setOrigin(res.site_origin);
      setSavedOrigin(res.site_origin);
      setSwitchPending(false);
      setNote(confirmSwitch || !savedOrigin ? "已保存，正在重新抓取。" : res.note && !res.note.startsWith("只抓") ? res.note : `已保存客户官网：${res.site_origin}`);
      if (confirmSwitch || !savedOrigin) {
        setBusyId("crawl-site");
        try {
          const session = await recrawlSavedSite(maxUrls, maxDepth);
          setNote(crawlFinishedNote(session));
        } catch (e) {
          setNote("已保存。自动抓取没跑成，请再点「扩大页面范围」。");
          setError(e instanceof Error ? e.message : "自动抓取失败");
        }
      }
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存官网失败");
    } finally {
      setBusyId("");
    }
  }

  async function setupSnipersTest() {
    setError("");
    try {
      const switching = isHostSwitch(savedOrigin, SNIPERS_TEST_ORIGIN);
      if (switching) {
        setOrigin(SNIPERS_TEST_ORIGIN);
        setSwitchPending(true);
        return;
      }
      const saved = await api<{ site_origin: string }>("/api/onsite/settings", {
        method: "PATCH",
        body: JSON.stringify({ site_origin: SNIPERS_TEST_ORIGIN, confirm_site_switch: switching }),
      });
      const known = new Set(pages.map((page) => page.path));
      let added = 0;
      for (const page of SNIPERS_TEST_PAGES) {
        if (known.has(page.path)) continue;
        await api<SitePage>("/api/onsite/pages", { method: "POST", body: JSON.stringify(page) });
        known.add(page.path);
        added += 1;
      }
      setOrigin(saved.site_origin);
      setSavedOrigin(saved.site_origin);
      setNote(`已设为 Snipers 官网测试：${saved.site_origin}，新增 ${added} 个诊断页面。`);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "初始化 Snipers 官网测试失败");
    }
  }

  async function fetchSite() {
    setError("");
    setBusyId("fetch-site");
    try {
      const res = await api<FetchRegistered>("/api/onsite/fetch-registered", { method: "POST" });
      setNote(`${res.note} 成功 ${res.fetched} · 失败 ${res.failed} · 验收 ${res.verified}`);
      load();
      document.getElementById("onsite-pages")?.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (e) {
      setError(e instanceof Error ? e.message : "抓取失败");
    } finally {
      setBusyId("");
    }
  }

  async function crawlSite() {
    setError("");
    setBusyId("crawl-site");
    try {
      const res = await api<CrawlSession>("/api/onsite/crawl-site", {
        method: "POST",
        body: JSON.stringify({ max_urls: maxUrls, max_depth: maxDepth }),
      });
      setNote(res.note);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "全站诊断抓取失败");
    } finally {
      setBusyId("");
    }
  }

  async function importPerformanceFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setError("");
    setBusyId("performance-import");
    try {
      const csvText = await file.text();
      const result = await api<{ rows_imported: number; filename: string }>("/api/onsite/performance/import-csv", {
        method: "POST",
        body: JSON.stringify({ source: performanceSource, filename: file.name, csv_text: csvText }),
      });
      setNote(`已导入 ${result.filename}，共 ${result.rows_imported} 行搜索表现数据。`);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "搜索表现 CSV 导入失败");
    } finally {
      setBusyId("");
    }
  }

  async function runPageSpeed() {
    setError("");
    setBusyId("pagespeed");
    try {
      const usingGoogle = Boolean(integrations?.google_relay_configured);
      const res = await api<{ status: string; performance_score: number | null; detail?: string }[]>("/api/onsite/performance/pagespeed", {
        method: "POST",
        body: JSON.stringify({ urls: [], strategies: ["mobile"], limit: 2 }),
        timeoutMs: 120000,
      });
      const failed = res.filter((item) => item.status !== "ok");
      const ok = res.length - failed.length;
      const label = usingGoogle ? "Google 测速" : "海外打开检查";
      if (!res.length || failed.length === res.length) {
        const reason = explainServiceError(
          failed[0]?.detail || (usingGoogle ? "没有测速结果。中转或 PageSpeed 可能超时。" : "没有测速结果。17CE 海外节点可能还没返回。"),
          "speed",
        );
        setError(`${label}未完成：${reason}`);
        return;
      }
      setNote(`${label}完成：成功 ${ok} 项，失败 ${failed.length} 项。`);
      if (failed.length) setError(explainServiceError(failed[0]?.detail || `部分页面${label}失败。`, "speed"));
      load();
    } catch (e) {
      setError(explainServiceError(e instanceof Error ? e.message : "测速失败", "speed"));
    } finally {
      setBusyId("");
    }
  }

  async function runSerp() {
    setError("");
    const keywords = targetKeywords.map((item) => item.label).filter((item) => item.trim());
    if (!performance?.serp?.configured) {
      setError("关键词排名数据源未配置，不能查询。不会在后台一直转。");
      return;
    }
    if (!keywords.length) {
      setError("没有可查询的关键词。请先回总览填写并保存搜索词，空着点不会去查，也不用等一分钟。");
      return;
    }
    setBusyId("serp");
    try {
      const country = targetMarkets[0]?.country_code || "US";
      const locale = targetMarkets[0]?.primary_locale || "en-US";
      const res = await api<SerpRunBatch>("/api/onsite/serp/run", {
        method: "POST",
        body: JSON.stringify({ keywords, country, locale, device: "desktop", limit: 50 }),
        timeoutMs: 60000,
      });
      if (!res.configured) {
        setError(res.note || "关键词排名数据源未配置。");
        return;
      }
      setNote(res.note || `SERP 查询完成：${res.ran} 个关键词。`);
      load();
    } catch (e) {
      setError(explainServiceError(e instanceof Error ? e.message : "SERP 查询失败", "rank"));
    } finally {
      setBusyId("");
    }
  }

  async function authorizeGsc() {
    setError("");
    try {
      const res = await api<GscAuthUrl>("/api/onsite/gsc/auth-url");
      if (!res.configured || !res.auth_url) {
        setError(res.note || "服务器未配置 GSC OAuth。");
        setShowGscSetup(true);
        return;
      }
      window.location.href = res.auth_url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "获取 GSC 授权链接失败");
    }
  }

  async function clearIntegrationKeys(keys: string[]) {
    setError("");
    setBusyId("integrations");
    try {
      const saved = await api<IntegrationSettings>("/api/onsite/integrations", {
        method: "PATCH",
        body: JSON.stringify({ clear_keys: keys }),
      });
      setIntegrations(saved);
      const nextGsc = await api<GscStatus>("/api/onsite/gsc/status");
      setGsc(nextGsc);
      setNote("已清除前台覆盖，改回服务器默认。");
      setShowGscSetup(true);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "清除配置失败");
    } finally {
      setBusyId("");
    }
  }

  async function saveIntegrationSettings() {
    setError("");
    setBusyId("integrations");
    try {
      const payload = Object.fromEntries(
        Object.entries(integrationForm).filter(([, value]) => value.trim())
      );
      if (!Object.keys(payload).length) {
        setError("请至少填写一个要保存的配置项。已保存的密钥会以掩码显示，不会回显原文。");
        return;
      }
      const saved = await api<IntegrationSettings>("/api/onsite/integrations", {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      setIntegrations(saved);
      setIntegrationForm({
        gsc_oauth_client_id: "",
        gsc_oauth_client_secret: "",
        gsc_oauth_redirect_uri: "",
        pagespeed_api_key: "",
        ce17_user: "",
        ce17_api_pwd: "",
        brightdata_dataset_api_key: "",
        brightdata_serp_zone: "",
        brightdata_serp_dataset_id: "",
        brightdata_serp_endpoint: "",
      });
      const nextGsc = await api<GscStatus>("/api/onsite/gsc/status");
      setGsc(nextGsc);
      setNote("数据源配置已保存。还可以继续改；留空的项保持原值。");
      setShowGscSetup(true);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存数据源配置失败");
    } finally {
      setBusyId("");
    }
  }

  async function syncGsc() {
    setError("");
    setBusyId("gsc-sync");
    try {
      const res = await api<GscSyncResult>("/api/onsite/gsc/sync", {
        method: "POST",
        body: JSON.stringify({ days: 28, row_limit: 25000 }),
      });
      setNote(`${res.note} ${res.date_start} 至 ${res.date_end}，导入 ${res.rows_imported} 行。`);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "GSC 同步失败");
    } finally {
      setBusyId("");
    }
  }

  async function submitIndexNow() {
    setError("");
    setBusyId("indexnow");
    try {
      const paths = pages.filter((p) => p.crawl_status === "ok").slice(0, 100).map((p) => p.path);
      const res = await api<IndexNowSubmitResult>("/api/onsite/indexnow/submit", {
        method: "POST",
        body: JSON.stringify({ paths: paths.length ? paths : ["/"] }),
      });
      setNote(`${res.note} 本次提交 ${res.submitted} 个 URL。`);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "IndexNow 提交失败");
    } finally {
      setBusyId("");
    }
  }

  async function runDueSync() {
    setError("");
    setBusyId("run-due-sync");
    try {
      const res = await api<DataSyncRunDueResult>("/api/onsite/data-sync/run-due", {
        method: "POST",
        body: JSON.stringify({ force: false, sources: ["gsc"] }),
      });
      setNote(res.note || (res.ran ? "到期同步已完成。" : "当前没有到期的数据源。"));
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "到期同步执行失败");
    } finally {
      setBusyId("");
    }
  }

  async function downloadReport() {
    setError("");
    try {
      const date = new Date().toISOString().slice(0, 10);
      await downloadApiFile("/api/onsite/report.pdf", `网站检查说明-${date}.pdf`);
      setNote("客户说明（PDF）已生成。");
    } catch (e) {
      setError(e instanceof Error ? e.message : "报告生成失败");
    }
  }

  async function downloadReportTable() {
    setError("");
    try {
      const report = await api<SeoReportTable>("/api/onsite/report-table");
      const blob = new Blob([report.csv], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = report.filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setNote("执行清单已生成。");
    } catch (e) {
      setError(e instanceof Error ? e.message : "表格生成失败");
    }
  }

  function focusIssues(nextFilter?: FilterKey) {
    if (nextFilter) setFilter(nextFilter);
    document.getElementById("onsite-issues")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function runPrimary() {
    if (!guide) return;
    if (guide.action_key === "save_origin") {
      if (!origin.trim()) {
        setError("请先在下面填上官网地址，再点保存。");
        document.getElementById("onsite-site-setup")?.scrollIntoView({ behavior: "smooth", block: "start" });
        return;
      }
      await saveOrigin();
      return;
    }
    if (guide.action_key === "fetch_site") {
      await fetchSite();
      return;
    }
    if (guide.action_key === "generate_drafts") {
      await writeDrafts();
      return;
    }
    if (guide.action_key === "review_drafts" || guide.action_key === "retest_queue") {
      focusIssues((guide.filter_key as FilterKey) || undefined);
      return;
    }
    if (guide.action_key === "export_report") {
      await downloadReport();
    }
  }

  async function crawlOrSeed() {
    setError("");
    const res = await api<{ seeded: number; note: string }>("/api/onsite/crawl-or-seed", { method: "POST" });
    setNote(res.note + `（新增 ${res.seeded} 页）`);
    load();
  }

  async function writeDrafts() {
    setError("");
    setBusyId("ai-batch");
    let written = 0;
    let remaining = -1;
    setDraftProgress({ written: 0, remaining: -1 });
    let stopped = "";
    try {
      while (remaining !== 0) {
        setNote(written ? `已写 ${written} 条，继续写剩下的…` : "正在写改法，不会再查一遍…");
        setDraftProgress({ written, remaining });
        const res = await api<AiAssist>("/api/onsite/ai", {
          method: "POST",
          body: JSON.stringify({ step: "content", limit: 5 }),
          timeoutMs: 90000,
        });
        written += res.processed ?? 0;
        remaining = res.remaining ?? 0;
        setDraftProgress({ written, remaining });
        if (res.status === "未配置") {
          stopped = res.detail || "AI 建议服务未配置，本次不会生成建议。";
          break;
        }
        if (res.processed === 0) break;
      }
      if (stopped) {
        setError(stopped);
      } else {
        setNote(
          remaining
            ? `已写 ${written} 条改法，还剩 ${remaining} 条，再点一次继续。这次只写改法，问题数不会因此变多。`
            : `已写完 ${written} 条改法。这次只写改法，问题数不会因此变多。`,
        );
      }
      load();
    } catch (e) {
      const message = e instanceof Error ? e.message : "写改法失败";
      setError(
        message.includes("Gateway Time-out") || message.includes("超时")
          ? `已写 ${written} 条。这次超时了，再点一次会从剩下的继续，不会从头再查。`
          : message,
      );
    } finally {
      setBusyId("");
    }
  }

  async function recheckSite() {
    setError("");
    setNote("正在再检查一遍，不会立刻写改法…");
    setBusyId("ai-recheck");
    try {
      const res = await api<AiAssist>("/api/onsite/ai", {
        method: "POST",
        body: JSON.stringify({ step: "analyze", limit: 5 }),
        timeoutMs: 90000,
      });
      setNote(res.detail || "检查完成。");
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "再检查失败");
    } finally {
      setBusyId("");
    }
  }

  async function aiIssue(id: string) {
    setError("");
    setBusyId(id);
    try {
      const res = await api<AiAssist>(`/api/onsite/issues/${id}/ai`, {
        method: "POST",
        timeoutMs: 120000,
        body: JSON.stringify({ step: "all" }),
      });
      if (res.status === "未配置") {
        setError(res.detail || "AI 建议未配置，没有写改法。");
      } else if (res.draft) {
        setDrafts((current) => ({ ...current, [id]: res.draft }));
        setNote("处理建议已写进方案框，请先看再保存。");
      } else {
        setNote(res.detail || "这次没有写出新的处理建议。");
      }
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "生成建议失败");
    } finally {
      setBusyId("");
    }
  }

  async function saveDraft(issue: OnsiteIssue) {
    const text = drafts[issue.id] ?? issue.proposed_change;
    if (!text?.trim()) {
      setError("请先填写改法。系统建议只作参考，仍需人工确认后再改网站。");
      return;
    }
    setBusyId(issue.id);
    try {
      await api(`/api/onsite/issues/${issue.id}/draft`, { method: "PATCH", body: JSON.stringify({ proposed_change: text }) });
      setNote("改法已保存。下一步交给执行修改，或进入人工确认。");
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存方案失败");
    } finally {
      setBusyId("");
    }
  }

  async function apply(issue: OnsiteIssue) {
    setError("");
    setBusyId(issue.id);
    try {
      if (issue.severity === "low" && issue.risk === "low") {
        await api(`/api/onsite/issues/${issue.id}/apply-draft`, { method: "POST" });
        setNote("已交给执行。修改完成后可复查。");
      } else {
        await api(`/api/onsite/issues/${issue.id}/mark-executed`, {
          method: "POST",
          body: JSON.stringify({ confirmed: true, note: "人工确认已在客户网站或执行环境处理，等待系统复测。" }),
        });
        setNote("已记录人工修改，下一步重新打开页面核对。");
      }
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "推进失败");
    } finally {
      setBusyId("");
    }
  }

  async function retestIssue(issue: OnsiteIssue) {
    setError("");
    setBusyId(issue.id);
    try {
      const row = await api<OnsiteIssue>(`/api/onsite/issues/${issue.id}/retest`, { method: "POST" });
      setNote(row.status === "verified" ? "复查通过，本条已完成。" : `复查完成，当前状态：${statusLabel[row.status] ?? row.status}`);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "复查失败");
    } finally {
      setBusyId("");
    }
  }

  async function ignoreIssue(issue: OnsiteIssue) {
    setError("");
    setBusyId(issue.id);
    try {
      await api<OnsiteIssue>(`/api/onsite/issues/${issue.id}/wont-fix`, {
        method: "POST",
        body: JSON.stringify({ note: "本轮测试暂不处理。" }),
      });
      setNote("本条已标为不改，不再进入优先清单。");
      if (expandedId === issue.id) setExpandedId("");
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "忽略失败");
    } finally {
      setBusyId("");
    }
  }

  async function copyDraft(issue: OnsiteIssue) {
    const text = drafts[issue.id] ?? issue.proposed_change;
    if (!text?.trim()) {
      setError("没有可复制的改法。");
      return;
    }
    await navigator.clipboard.writeText(text);
    setNote("改法已复制。");
  }

  async function create(e: FormEvent) {
    e.preventDefault();
    await api<SitePage>("/api/onsite/pages", { method: "POST", body: JSON.stringify(form) });
    setForm({ path: "/", locale: "en-US", title: "" });
    setNote("已加入诊断页面清单。");
    load();
  }

  if (!board) return <p className="text-sm text-slate-500">{error || "加载中…"}</p>;

  return (
    <div className="space-y-6">
      <GuideHeader
        guide={guide}
        voicePending={voicePending}
        busyId={busyId}
        draftProgress={draftProgress}
        onPrimary={() => void runPrimary()}
        crawlOrSeed={crawlOrSeed}
        writeDrafts={() => void writeDrafts()}
        recheckSite={() => void recheckSite()}
        downloadReport={downloadReport}
        downloadReportTable={downloadReportTable}
      />
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      {note ? <p className="text-sm text-emerald-700">{note}</p> : null}

      <SiteSetupCard
        origin={origin}
        savedOrigin={savedOrigin}
        setOrigin={setOrigin}
        saveOrigin={saveOrigin}
        confirmSwitch={() => void persistOrigin(origin, true)}
        cancelSwitch={cancelSwitch}
        switchPending={switchPending}
        setupSnipersTest={setupSnipersTest}
        maxUrls={maxUrls}
        setMaxUrls={setMaxUrls}
        maxDepth={maxDepth}
        setMaxDepth={setMaxDepth}
        fetchSite={fetchSite}
        crawlSite={crawlSite}
        busyId={busyId}
        sessions={sessions}
        note={note}
        error={error}
      />

      <TargetMarketsCard targetMarkets={targetMarkets} targetKeywords={targetKeywords} performance={performance} />

      <DiagnosisSection
        diagnosisReadiness={diagnosisReadiness}
        fetched={stats.fetched}
        totalPages={board.pages}
        searchVerdict={searchVerdict}
        performance={performance}
      />

      <RankAuthoritySection performance={performance} />

      <PerformanceDataCard
        gsc={gsc}
        integrations={integrations}
        bing={bing}
        indexNow={indexNow}
        syncStatus={syncStatus}
        performance={performance}
        showGscSetup={showGscSetup}
        setShowGscSetup={setShowGscSetup}
        integrationForm={integrationForm}
        setIntegrationForm={setIntegrationForm}
        authorizeGsc={authorizeGsc}
        saveIntegrationSettings={saveIntegrationSettings}
        clearIntegrationKeys={clearIntegrationKeys}
        syncGsc={syncGsc}
        busyId={busyId}
        performanceSource={performanceSource}
        setPerformanceSource={setPerformanceSource}
        importPerformanceFile={importPerformanceFile}
        runPageSpeed={runPageSpeed}
        runSerp={runSerp}
        submitIndexNow={submitIndexNow}
        runDueSync={runDueSync}
        actionError={error}
      />

      <div className="space-y-2">
        <StatsGrid board={board} stats={stats} />
        <p className="text-xs leading-5 text-slate-500">
          这些数字只算网站检查。紧急/优先是严重程度；需确认、待上线、待复查是进度，所以也会对不上。总览右侧「执行项」还加上了 AI 搜索和站外。
        </p>
      </div>

      <IssueBoard
        visibleIssues={visibleIssues}
        totalCount={issues.length}
        filter={filter}
        setFilter={setFilter}
        query={query}
        setQuery={setQuery}
        expandedId={expandedId}
        setExpandedId={setExpandedId}
        drafts={drafts}
        setDrafts={setDrafts}
        busyId={busyId}
        aiIssue={aiIssue}
        saveDraft={saveDraft}
        copyDraft={copyDraft}
        retestIssue={retestIssue}
        apply={apply}
        ignoreIssue={ignoreIssue}
      />

      <PagesAndBriefsSection pages={pages} form={form} setForm={setForm} create={create} briefs={briefs} />
    </div>
  );
}
