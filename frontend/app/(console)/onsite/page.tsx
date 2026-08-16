"use client";

import {
  AlertTriangle,
  BarChart3,
  Bot,
  CheckCircle2,
  ClipboardList,
  Copy,
  Download,
  Gauge,
  RefreshCcw,
  Search,
  Upload,
  Wrench,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  api,
  crawlStatusLabel,
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
  type IndexNowStatus,
  type IndexNowSubmitResult,
  type Market,
  type OnsiteBoard,
  type OnsiteIssue,
  type ProjectTargets,
  type SeoReport,
  type SeoReportTable,
  type SeoPerformanceSummary,
  type SeoPage,
  type SerpRunBatch,
  type SitePage,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const catLabel: Record<string, string> = {
  tdk: "TDK",
  heading: "标题",
  internal_link: "内链",
  schema: "JSON-LD",
  index: "收录",
  crawl: "抓取",
  canonical: "Canonical",
  image: "图片",
  content: "内容",
  b2b: "B2B",
};

const sevLabel: Record<string, string> = { critical: "Critical", high: "High", low: "Low" };
const sevTone: Record<string, "red" | "amber" | "green"> = { critical: "red", high: "amber", low: "green" };
const statusLabel: Record<string, string> = {
  open: "待写处理方案",
  drafted: "已有方案，待人工上线",
  draft_applied: "已交付执行人",
  confirmed: "已人工上线，待回抓",
  verified: "观察已验收",
  wont_fix: "不做",
};

const statusTone: Record<string, "default" | "amber" | "green" | "blue" | "red"> = {
  open: "amber",
  drafted: "blue",
  draft_applied: "amber",
  confirmed: "red",
  verified: "green",
  wont_fix: "default",
};

const filters = [
  { key: "all", label: "全部" },
  { key: "needs_review", label: "需人审" },
  { key: "critical", label: "Critical" },
  { key: "high", label: "High" },
  { key: "low", label: "Low" },
  { key: "needs_draft", label: "待方案" },
  { key: "ready_to_execute", label: "待人工上线" },
  { key: "waiting_retest", label: "待回抓验收" },
  { key: "untested", label: "未测" },
] as const;

const SNIPERS_TEST_ORIGIN = "https://www.snipers.com.cn";
const SNIPERS_TEST_PAGES = [
  { path: "/", locale: "zh-CN", title: "Snipers 官网首页" },
  { path: "/g-snipers/", locale: "zh-CN", title: "G-Snipers" },
  { path: "/category/seo/", locale: "zh-CN", title: "SEO 文章栏目" },
  { path: "/category/geo/", locale: "zh-CN", title: "GEO 文章栏目" },
];

type FilterKey = (typeof filters)[number]["key"];

function priorityLabel(issue: OnsiteIssue) {
  if (issue.severity === "critical") return "P0";
  if (issue.severity === "high" || issue.risk === "high") return "P1";
  if (issue.status === "confirmed") return "P1";
  return "P2";
}

function priorityRank(issue: OnsiteIssue) {
  const severityRank: Record<string, number> = { critical: 0, high: 10, low: 20 };
  const statusRank: Record<string, number> = { confirmed: 0, drafted: 1, open: 2, draft_applied: 3 };
  return (severityRank[issue.severity] ?? 20) + (statusRank[issue.status] ?? 5);
}

function nextStep(issue: OnsiteIssue) {
  if (issue.status === "confirmed") return "回抓验收";
  if (issue.status === "draft_applied") return "等待执行后复测";
  if (issue.status === "drafted") return issue.risk === "high" ? "交给技术/客户上线" : "交付执行";
  if (!issue.proposed_change.trim()) return "生成或填写处理方案";
  return "保存方案并推进";
}

function matchesFilter(issue: OnsiteIssue, filter: FilterKey) {
  if (filter === "all") return true;
  if (filter === "needs_review") return Boolean(issue.review_required);
  if (filter === "critical" || filter === "high" || filter === "low") return issue.severity === filter;
  if (filter === "needs_draft") return issue.status === "open" && !issue.proposed_change.trim();
  if (filter === "ready_to_execute") return issue.status === "drafted";
  if (filter === "waiting_retest") return issue.status === "confirmed" || issue.status === "draft_applied";
  if (filter === "untested") return issue.metric_status === "untested";
  return true;
}

export default function OnsiteBoardPage() {
  const [board, setBoard] = useState<OnsiteBoard | null>(null);
  const [pages, setPages] = useState<SitePage[]>([]);
  const [briefs, setBriefs] = useState<ContentBrief[]>([]);
  const [markets, setMarkets] = useState<Market[]>([]);
  const [seoTargets, setSeoTargets] = useState<SeoPage[]>([]);
  const [performance, setPerformance] = useState<SeoPerformanceSummary | null>(null);
  const [gsc, setGsc] = useState<GscStatus | null>(null);
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
  const [maxUrls, setMaxUrls] = useState(50);
  const [maxDepth, setMaxDepth] = useState(2);
  const [showGscSetup, setShowGscSetup] = useState(false);
  const [performanceSource, setPerformanceSource] = useState<"gsc_csv" | "bing_csv">("gsc_csv");
  const [form, setForm] = useState({ path: "/", locale: "en-US", title: "" });
  const [origin, setOrigin] = useState("");

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
      api<GscStatus>("/api/onsite/gsc/status"),
      api<BingStatus>("/api/onsite/bing/status"),
      api<IndexNowStatus>("/api/onsite/indexnow/status"),
      api<DataSyncStatus>("/api/onsite/data-sync/status"),
      api<ProjectTargets>("/api/project-targets"),
    ])
      .then(([b, p, br, s, cs, m, seo, perf, gscStatus, bingStatus, indexNowStatus, ds, targetConfig]) => {
        setBoard(b);
        setPages(p);
        setBriefs(br);
        setOrigin(s.site_origin || "");
        setSessions(cs);
        setMarkets(m);
        setSeoTargets(seo);
        setPerformance(perf);
        setGsc(gscStatus);
        setBing(bingStatus);
        setIndexNow(indexNowStatus);
        setSyncStatus(ds);
        setTargets(targetConfig);
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

  async function saveOrigin() {
    setError("");
    try {
      const res = await api<{ site_origin: string }>("/api/onsite/settings", {
        method: "PATCH",
        body: JSON.stringify({ site_origin: origin }),
      });
      setOrigin(res.site_origin);
      setNote(`已保存客户官网：${res.site_origin}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存官网失败");
    }
  }

  async function setupSnipersTest() {
    setError("");
    try {
      const saved = await api<{ site_origin: string }>("/api/onsite/settings", {
        method: "PATCH",
        body: JSON.stringify({ site_origin: SNIPERS_TEST_ORIGIN }),
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
      setNote(`已设为 Snipers 官网测试：${saved.site_origin}，新增 ${added} 个诊断页面。`);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "初始化 Snipers 官网测试失败");
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
      const res = await api<{ status: string; performance_score: number | null }[]>("/api/onsite/performance/pagespeed", {
        method: "POST",
        body: JSON.stringify({ urls: [], strategies: ["mobile", "desktop"], limit: 3 }),
      });
      const ok = res.filter((item) => item.status === "ok").length;
      setNote(`PageSpeed 免费测速完成：成功 ${ok} 项，失败 ${res.length - ok} 项。`);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "PageSpeed 测速失败");
    } finally {
      setBusyId("");
    }
  }

  async function runSerp() {
    setError("");
    setBusyId("serp");
    try {
      const country = targetMarkets[0]?.country_code || "US";
      const locale = targetMarkets[0]?.primary_locale || "en-US";
      const res = await api<SerpRunBatch>("/api/onsite/serp/run", {
        method: "POST",
        body: JSON.stringify({ keywords: [], country, locale, device: "desktop", limit: 10 }),
      });
      if (!res.configured) {
        setError(res.note || "Bright Data SERP 未配置。");
      } else {
        setNote(res.note || `SERP 查询完成：${res.ran} 个关键词。`);
      }
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "SERP 查询失败");
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
      const report = await api<SeoReport>("/api/onsite/report");
      const blob = new Blob([report.markdown], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `seo-report-${new Date(report.generated_at).toISOString().slice(0, 10)}.md`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setNote("SEO 诊断报告已生成。");
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
      setNote("SEO 诊断表格已生成。");
    } catch (e) {
      setError(e instanceof Error ? e.message : "表格生成失败");
    }
  }

  async function fetchPage(pageId: string) {
    setError("");
    try {
      const res = await api<FetchRegistered>(`/api/onsite/pages/${pageId}/fetch`, { method: "POST" });
      setNote(`${res.note} 状态 ${res.results[0]?.crawl_status ?? ""} · 验收 ${res.verified}`);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "回抓失败");
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
    setNote("正在生成本批 AI 整改建议，请稍等…");
    setBusyId("ai-batch");
    try {
      const res = await api<AiAssist>("/api/onsite/ai", {
        method: "POST",
        body: JSON.stringify({ step: "all", limit: 5 }),
      });
      const more = res.remaining ? ` 还有约 ${res.remaining} 条，继续点击可处理下一批。` : "";
      setNote((res.detail || `本批 AI 建议完成：${res.status}`) + more);
      if (res.status === "未配置") setError(res.detail || "AI 建议服务未配置，本次不会生成建议。");
      load();
    } catch (e) {
      const message = e instanceof Error ? e.message : "批量生成 AI 建议失败";
      setError(message.includes("Gateway Time-out") ? "网关超时：本批 AI 处理耗时过长。请稍后重试，系统现在已改为小批量处理。" : message);
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
        body: JSON.stringify({ step: "all" }),
      });
      setNote(res.detail || res.status);
      if (res.status === "未配置") setError(res.detail);
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
      setError("请先填写整改方案。AI 建议只提供参考，仍需要人工确认后执行。");
      return;
    }
    setBusyId(issue.id);
    try {
      await api(`/api/onsite/issues/${issue.id}/draft`, { method: "PATCH", body: JSON.stringify({ proposed_change: text }) });
      setNote("处理方案已保存，下一步交给执行人上线或进入人审。");
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
        setNote("已标记为交付执行人。执行完成后可回抓复测。");
      } else {
        await api(`/api/onsite/issues/${issue.id}/mark-executed`, {
          method: "POST",
          body: JSON.stringify({ confirmed: true, note: "人工确认已在客户网站或执行环境处理，等待系统复测。" }),
        });
        setNote("已记录人工执行，下一步回抓复测。");
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
      setNote(row.status === "verified" ? "复测通过，本条已验收。" : `复测完成，当前状态：${statusLabel[row.status] ?? row.status}`);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "复测失败");
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
      setNote("已忽略本条，不再进入优先处理清单。");
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
      setError("没有可复制的处理方案。");
      return;
    }
    await navigator.clipboard.writeText(text);
    setNote("处理方案已复制。");
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
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">SEO 诊断与整改工作台</h1>
          <p className="mt-1 text-sm text-slate-500">
            从客户官网抓取页面证据，按风险优先级生成整改清单、AI 建议和可导出的客户报告。
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={crawlOrSeed} variant="outline">
            <ClipboardList className="mr-2 h-4 w-4" />
            从内链扩清单
          </Button>
          <Button onClick={analyze} disabled={busyId === "ai-batch"}>
            <Bot className="mr-2 h-4 w-4" />
            {busyId === "ai-batch" ? "生成中…" : "批量生成 AI 整改建议"}
          </Button>
          <Button onClick={downloadReport} variant="outline">
            <Download className="mr-2 h-4 w-4" />
            导出客户报告
          </Button>
          <Button onClick={downloadReportTable} variant="outline">
            <Download className="mr-2 h-4 w-4" />
            导出执行表格
          </Button>
        </div>
      </div>

      <Card className="rounded-md">
        <CardHeader>
          <CardTitle>诊断网站</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 lg:grid-cols-[1fr_auto_auto]">
            <Input
              placeholder="https://www.customer.com"
              value={origin}
              onChange={(e) => setOrigin(e.target.value)}
            />
            <Button type="button" variant="outline" onClick={saveOrigin}>
              保存/切换网站
            </Button>
            <Button type="button" variant="outline" onClick={setupSnipersTest}>
              使用 Snipers 测试
            </Button>
          </div>
          <div className="grid gap-3 lg:grid-cols-[120px_120px_auto_auto_1fr]">
            <Input
              type="number"
              min={1}
              max={300}
              value={maxUrls}
              onChange={(e) => setMaxUrls(Number(e.target.value))}
              aria-label="最大 URL"
            />
            <Input
              type="number"
              min={0}
              max={5}
              value={maxDepth}
              onChange={(e) => setMaxDepth(Number(e.target.value))}
              aria-label="最大深度"
            />
            <Button type="button" onClick={fetchSite} variant="outline">
              <RefreshCcw className="mr-2 h-4 w-4" />
              抓已登记页
            </Button>
            <Button type="button" onClick={crawlSite} disabled={busyId === "crawl-site"}>
              <ClipboardList className="mr-2 h-4 w-4" />
              站点诊断抓取
            </Button>
            <div className="text-xs text-slate-500">
              当前：{origin || "未设置"} · URL 上限 {maxUrls} · 深度 {maxDepth}
            </div>
          </div>
          {sessions[0] ? (
            <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
              最近抓取：发现 {sessions[0].discovered} · 成功 {sessions[0].fetched} · 失败 {sessions[0].failed} · 新增问题 {sessions[0].created} · JS {sessions[0].needs_js}
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card className="rounded-md">
        <CardHeader>
          <CardTitle>诊断目标</CardTitle>
          <p className="mt-1 text-sm text-slate-500">SEO 诊断会围绕目标国家、核心搜索词、竞品和关键页面排序，让报告更贴近客户实际获客市场。</p>
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-3">
          <div className="rounded-md border border-slate-200 p-3">
            <div className="text-xs font-medium text-slate-500">目标国家 / 市场</div>
            <div className="mt-2 space-y-2">
              {targetMarkets.length ? (
                targetMarkets.map((market) => (
                  <div key={market.id} className="flex items-center justify-between gap-3 text-sm">
                    <span className="font-medium text-slate-800">{market.name}</span>
                    <span className="text-xs text-slate-500">{market.country_code} · {market.primary_locale}</span>
                  </div>
                ))
              ) : (
                <div className="text-sm text-slate-500">未设置。请先在首页填写客户诊断目标。</div>
              )}
            </div>
          </div>
          <div className="rounded-md border border-slate-200 p-3">
            <div className="text-xs font-medium text-slate-500">核心搜索词 / 选题</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {targetKeywords.length ? (
                targetKeywords.map((item) => (
                  <Badge key={item.id} tone={item.status === "ready" ? "green" : "blue"}>
                    {item.label}
                  </Badge>
                ))
              ) : (
                <div className="text-sm text-slate-500">未设置。先登记核心产品词、行业词和采购意图词。</div>
              )}
            </div>
          </div>
          <div className="rounded-md border border-slate-200 p-3">
            <div className="text-xs font-medium text-slate-500">搜索表现 / 测速</div>
            <div className="mt-2 space-y-2 text-sm text-slate-700">
              <div className="flex items-center justify-between gap-3">
                <span>Google Search Console</span>
                <Badge tone={performance?.gsc_status === "已导入" ? "green" : "amber"}>{performance?.gsc_status ?? "读取中"}</Badge>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span>Bing Webmaster</span>
                <Badge tone={performance?.bing_status === "已导入" ? "green" : "amber"}>{performance?.bing_status ?? "读取中"}</Badge>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span>PageSpeed Insights</span>
                <Badge tone={performance?.pagespeed_status === "已测速" ? "green" : "amber"}>{performance?.pagespeed_status ?? "读取中"}</Badge>
              </div>
              <p className="text-xs text-slate-500">接入或导入数据后，报告会带上曝光、点击、CTR、排名、SERP 和速度证据。</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-md">
        <CardHeader>
          <CardTitle>SEO 表现数据源</CardTitle>
          <p className="mt-1 text-sm text-slate-500">优先使用免费且可信的数据源：GSC/Bing 记录真实搜索表现，PageSpeed 记录速度体验，Bright Data 记录目标关键词的 Google SERP。</p>
        </CardHeader>
        <CardContent className="grid gap-4 xl:grid-cols-2">
          <div className="rounded-md border border-slate-200 p-4">
            <div className="flex items-center gap-2 text-sm font-medium text-slate-800">
              <Search className="h-4 w-4" />
              GSC 自动同步
            </div>
            <div className="mt-3 space-y-2 text-sm text-slate-700">
              <div className="flex items-center justify-between gap-3">
                <span>OAuth 配置</span>
                <Badge tone={gsc?.configured ? "green" : "amber"}>{gsc?.configured ? "已配置" : "未配置"}</Badge>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span>客户授权</span>
                <Badge tone={gsc?.connected ? "green" : "amber"}>{gsc?.connected ? "已连接" : "未连接"}</Badge>
              </div>
              <div className="truncate text-xs text-slate-500">{gsc?.site_url || gsc?.note || "读取中"}</div>
              {gsc?.last_sync_at ? <div className="text-xs text-slate-500">最近同步 {new Date(gsc.last_sync_at).toLocaleString("zh-CN")}</div> : null}
              {gsc?.last_error ? <div className="text-xs text-red-600">{gsc.last_error}</div> : null}
            </div>
            <div className="mt-3 grid gap-2">
              {gsc?.configured ? (
                <Button type="button" variant="outline" onClick={authorizeGsc}>
                  {gsc.connected ? "重新授权 GSC" : "打开 Google 授权页"}
                </Button>
              ) : (
                <Button type="button" variant="outline" onClick={() => setShowGscSetup((value) => !value)}>
                  查看配置要求
                </Button>
              )}
              <Button type="button" onClick={syncGsc} disabled={!gsc?.connected || busyId === "gsc-sync"}>
                {busyId === "gsc-sync" ? "同步中…" : "同步 28 天数据"}
              </Button>
            </div>
            {showGscSetup || !gsc?.configured ? (
              <div className="mt-3 rounded-md bg-amber-50 p-3 text-xs leading-5 text-amber-900">
                <div className="font-medium">为什么现在打不开？</div>
                <p className="mt-1">Google 授权页需要服务器先配置 OAuth Client ID / Secret。配置完成后，这里会变成“打开 Google 授权页”。</p>
                <div className="mt-2 rounded border border-amber-200 bg-white px-2 py-1 font-mono text-[11px] text-amber-950">
                  GSC_CLIENT_ID / GSC_CLIENT_SECRET / GSC_REDIRECT_URI
                </div>
              </div>
            ) : null}
          </div>
          <div className="rounded-md border border-slate-200 p-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <div className="flex items-center gap-2 text-sm font-medium text-slate-800">
                  <Upload className="h-4 w-4" />
                  导入搜索表现 CSV
                </div>
                <p className="mt-2 text-xs leading-5 text-slate-500">
                  适合客户暂时不能授权 GSC 时使用。支持 GSC/Bing 导出的关键词、页面、国家、设备、点击、曝光、CTR、平均排名字段。
                </p>
              </div>
              <Badge tone={(performance?.imports.length ?? 0) > 0 ? "green" : "amber"}>
                已导入 {performance?.imports.length ?? 0} 批
              </Badge>
            </div>
            <div className="mt-3 grid gap-2 md:grid-cols-[160px_minmax(0,1fr)]">
              <select
                className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm outline-none focus:border-emerald-500"
                value={performanceSource}
                onChange={(e) => setPerformanceSource(e.target.value as "gsc_csv" | "bing_csv")}
              >
                <option value="gsc_csv">GSC CSV</option>
                <option value="bing_csv">Bing CSV</option>
              </select>
              <Input
                className="min-w-0"
                type="file"
                accept=".csv,text/csv"
                onChange={importPerformanceFile}
                disabled={busyId === "performance-import"}
              />
            </div>
          </div>
          <div className="rounded-md border border-slate-200 p-4">
            <div className="flex items-center gap-2 text-sm font-medium text-slate-800">
              <Gauge className="h-4 w-4" />
              免费测速
            </div>
            <div className="mt-3 grid grid-cols-3 gap-2 text-center">
              <div className="rounded-md bg-slate-50 p-2">
                <div className="text-lg font-semibold">{performance?.speed_latest.length ?? 0}</div>
                <div className="text-[11px] text-slate-500">测速记录</div>
              </div>
              <div className="rounded-md bg-slate-50 p-2">
                <div className="text-lg font-semibold">{performance?.speed_latest[0]?.performance_score ?? "-"}</div>
                <div className="text-[11px] text-slate-500">最近性能</div>
              </div>
              <div className="rounded-md bg-slate-50 p-2">
                <div className="text-lg font-semibold">{performance?.speed_latest[0]?.seo_score ?? "-"}</div>
                <div className="text-[11px] text-slate-500">最近 SEO</div>
              </div>
            </div>
            <Button type="button" onClick={runPageSpeed} disabled={busyId === "pagespeed"} className="mt-3 w-full">
              <Gauge className="mr-2 h-4 w-4" />
              {busyId === "pagespeed" ? "测速中…" : "测首页和核心页"}
            </Button>
          </div>
          <div className="rounded-md border border-slate-200 p-4">
            <div className="flex items-center gap-2 text-sm font-medium text-slate-800">
              <Search className="h-4 w-4" />
              Bright Data SERP
            </div>
            <div className="mt-3 grid grid-cols-3 gap-2 text-center">
              <div className="rounded-md bg-slate-50 p-2">
                <div className="text-lg font-semibold">{performance?.serp?.total_runs ?? 0}</div>
                <div className="text-[11px] text-slate-500">查询轮次</div>
              </div>
              <div className="rounded-md bg-slate-50 p-2">
                <div className="text-lg font-semibold">{performance?.serp?.own_visible_runs ?? 0}</div>
                <div className="text-[11px] text-slate-500">我方出现</div>
              </div>
              <div className="rounded-md bg-slate-50 p-2">
                <div className="text-lg font-semibold">{performance?.serp?.competitor_visible_runs ?? 0}</div>
                <div className="text-[11px] text-slate-500">竞品出现</div>
              </div>
            </div>
            <Button type="button" onClick={runSerp} disabled={busyId === "serp"} className="mt-3 w-full">
              <Search className="mr-2 h-4 w-4" />
              {busyId === "serp" ? "查询中…" : "查询目标关键词 SERP"}
            </Button>
            <p className="mt-2 text-xs text-slate-500">
              {performance?.serp?.configured ? "按目标国家和核心搜索词查询 Google 前 10，作为市场可见度证据。" : "服务器尚未配置 Bright Data SERP，关键词排名保持未测。"}
            </p>
          </div>
          <div className="rounded-md border border-slate-200 p-4 xl:col-span-2">
            <div className="flex items-center gap-2 text-sm font-medium text-slate-800">
              <BarChart3 className="h-4 w-4" />
              搜索表现摘要
            </div>
            <div className="mt-3 grid gap-2 text-center sm:grid-cols-3">
              <div className="rounded-md bg-slate-50 p-2">
                <div className="text-lg font-semibold">{performance?.total_impressions ?? 0}</div>
                <div className="text-[11px] text-slate-500">曝光</div>
              </div>
              <div className="rounded-md bg-slate-50 p-2">
                <div className="text-lg font-semibold">{performance?.total_clicks ?? 0}</div>
                <div className="text-[11px] text-slate-500">点击</div>
              </div>
              <div className="rounded-md bg-slate-50 p-2">
                <div className="text-lg font-semibold">{performance?.avg_ctr ?? "-"}</div>
                <div className="text-[11px] text-slate-500">CTR%</div>
              </div>
            </div>
            <div className="mt-3 space-y-1 text-xs text-slate-600">
              {(performance?.by_query ?? []).slice(0, 3).map((item) => (
                <div key={item.key} className="flex items-center justify-between gap-2">
                  <span className="truncate">{item.key}</span>
                  <span className="shrink-0 text-slate-500">{item.impressions} / {item.clicks}</span>
                </div>
              ))}
              {performance?.by_query.length ? null : <div className="text-slate-500">导入 GSC/Bing CSV 后显示关键词表现。</div>}
            </div>
          </div>
        </CardContent>
        {performance?.serp?.latest_runs?.length ? (
          <CardContent className="border-t border-slate-100 pt-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div className="text-sm font-medium text-slate-800">最近关键词排名查询</div>
              <Badge tone="blue">SERP 证据</Badge>
            </div>
            <div className="grid gap-2 lg:grid-cols-2">
              {performance.serp.latest_runs.slice(0, 4).map((run) => (
                <div key={run.id} className="rounded-md border border-slate-200 p-3 text-sm">
                  <div className="flex items-center justify-between gap-3">
                    <span className="truncate font-medium text-slate-800">{run.keyword}</span>
                    <Badge tone={run.status === "ok" ? "green" : "red"}>{run.status}</Badge>
                  </div>
                  <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-slate-600">
                    <span>{run.country}/{run.device}</span>
                    <span>我方 {run.own_best_position ?? "未出现"}</span>
                    <span>竞品 {run.competitor_best_position ?? "未出现"}</span>
                  </div>
                  {run.error ? <p className="mt-2 text-xs text-red-600">{run.error}</p> : null}
                </div>
              ))}
            </div>
          </CardContent>
        ) : null}
        <CardContent className="grid gap-4 border-t border-slate-100 pt-4 lg:grid-cols-3">
          <div className="rounded-md border border-slate-200 p-3">
            <div className="text-sm font-medium text-slate-800">Bing Webmaster</div>
            <div className="mt-2 flex items-center justify-between gap-3 text-sm">
              <span>API Key</span>
              <Badge tone={bing?.configured ? "green" : "amber"}>{bing?.configured ? "已配置" : "未配置"}</Badge>
            </div>
            <p className="mt-2 text-xs text-slate-500">{bing?.note || "读取中"}</p>
          </div>
          <div className="rounded-md border border-slate-200 p-3">
            <div className="text-sm font-medium text-slate-800">IndexNow</div>
            <div className="mt-2 flex items-center justify-between gap-3 text-sm">
              <span>{indexNow?.host || "未设置官网"}</span>
              <Badge tone={indexNow?.configured ? "green" : "amber"}>{indexNow?.configured ? "可提交" : "未配置"}</Badge>
            </div>
            <p className="mt-2 truncate text-xs text-slate-500">{indexNow?.key_location || indexNow?.note || "读取中"}</p>
            {indexNow?.last_submitted_at ? <p className="mt-1 text-xs text-slate-500">最近提交 {new Date(indexNow.last_submitted_at).toLocaleString("zh-CN")}</p> : null}
            <Button type="button" variant="outline" onClick={submitIndexNow} disabled={!indexNow?.configured || busyId === "indexnow"} className="mt-3 w-full">
              {busyId === "indexnow" ? "提交中…" : "提交已抓取 URL"}
            </Button>
          </div>
          <div className="rounded-md border border-slate-200 p-3">
            <div className="flex items-center justify-between gap-3">
              <div className="text-sm font-medium text-slate-800">同步历史</div>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={runDueSync}
                disabled={!gsc?.connected || busyId === "run-due-sync"}
              >
                {busyId === "run-due-sync" ? "检查中…" : "运行到期同步"}
              </Button>
            </div>
            <div className="mt-2 space-y-2">
              {(syncStatus?.runs ?? []).slice(0, 3).map((run) => (
                <div key={run.id} className="flex items-center justify-between gap-3 text-xs text-slate-600">
                  <span>{run.source} · {run.mode} · {run.status}</span>
                  <span>{run.rows_imported ? `${run.rows_imported} 行` : run.submitted ? `${run.submitted} URL` : "-"}</span>
                </div>
              ))}
              {syncStatus?.runs.length ? null : <p className="text-xs text-slate-500">暂无同步记录。</p>}
            </div>
            <p className="mt-2 text-xs text-slate-500">服务器定时任务也可以调用同一个入口，避免依赖浏览器常开。</p>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-3 md:grid-cols-4 xl:grid-cols-10">
        <Card className="rounded-md">
          <CardContent className="py-4">
            <div className="text-2xl font-semibold">{board.pages}</div>
            <div className="text-xs text-slate-500">登记页面</div>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="py-4">
            <div className="text-2xl font-semibold">{stats.fetched}</div>
            <div className="text-xs text-slate-500">已抓取</div>
          </CardContent>
        </Card>
        <Card className="rounded-md border-red-200">
          <CardContent className="py-4">
            <div className="text-2xl font-semibold text-red-700">{board.counts.critical}</div>
            <div className="text-xs text-slate-500">Critical</div>
          </CardContent>
        </Card>
        <Card className="rounded-md border-amber-200">
          <CardContent className="py-4">
            <div className="text-2xl font-semibold text-amber-700">{board.counts.high}</div>
            <div className="text-xs text-slate-500">High</div>
          </CardContent>
        </Card>
        <Card className="rounded-md border-emerald-200">
          <CardContent className="py-4">
            <div className="text-2xl font-semibold text-emerald-700">{board.counts.low}</div>
            <div className="text-xs text-slate-500">Low</div>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="py-4">
            <div className="text-2xl font-semibold">{stats.waitingDraft}</div>
            <div className="text-xs text-slate-500">待方案</div>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="py-4">
            <div className="text-2xl font-semibold">{stats.needsReview}</div>
            <div className="text-xs text-slate-500">需人审</div>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="py-4">
            <div className="text-2xl font-semibold">{stats.readyToExecute}</div>
            <div className="text-xs text-slate-500">待上线</div>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="py-4">
            <div className="text-2xl font-semibold">{stats.waitingRetest}</div>
            <div className="text-xs text-slate-500">待回抓</div>
          </CardContent>
        </Card>
        <Card className="rounded-md">
          <CardContent className="py-4">
            <div className="text-2xl font-semibold text-emerald-700">{stats.solved}</div>
            <div className="text-xs text-slate-500">已解决</div>
          </CardContent>
        </Card>
      </div>

      {note ? <p className="text-sm text-slate-600">{note}</p> : null}
      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <Card className="rounded-md">
        <CardHeader className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
          <CardTitle>优先整改清单</CardTitle>
              <p className="mt-1 text-sm text-slate-500">默认按风险、执行状态和页面路径排序。点击问题即可查看证据、建议动作和复测方法。</p>
            </div>
            <Badge tone="amber">{visibleIssues.length} / {issues.length} 条</Badge>
          </div>
          <div className="grid gap-3 xl:grid-cols-[1fr_auto]">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <Input
                className="pl-9"
                placeholder="搜索 URL、页面名、问题类型或整改方案"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
            <div className="flex flex-wrap gap-2">
              {filters.map((item) => (
                <Button
                  key={item.key}
                  size="sm"
                  variant={filter === item.key ? "default" : "outline"}
                  onClick={() => setFilter(item.key)}
                >
                  {item.label}
                </Button>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {visibleIssues.length === 0 ? (
            <div className="rounded-md border border-dashed border-slate-200 p-5 text-sm text-slate-500">
              当前筛选下没有待处理问题。
            </div>
          ) : null}
          {visibleIssues.map((issue) => {
            const expanded = expandedId === issue.id;
            const severityTone = sevTone[issue.severity as keyof typeof sevTone] ?? "green";
            return (
              <div key={issue.id} className={cn("rounded-md border", expanded ? "border-brand-600" : "border-slate-200")}>
                <button
                  type="button"
                  className="grid w-full gap-3 p-4 text-left lg:grid-cols-[72px_1fr_180px_150px_110px]"
                  onClick={() => setExpandedId(expanded ? "" : issue.id)}
                >
                  <div>
                    <Badge tone={severityTone}>{priorityLabel(issue)}</Badge>
                    <div className="mt-2 text-xs text-slate-500">{sevLabel[issue.severity] ?? issue.severity}</div>
                  </div>
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-slate-900">{issue.title}</span>
                      <Badge>{catLabel[issue.category] ?? issue.category}</Badge>
                      <Badge tone="amber">{issue.metric_status === "untested" ? "未测" : issue.metric_status}</Badge>
                    </div>
                    <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-500">
                      <span className="text-brand-700">{issue.page_title || issue.page_path}</span>
                      <span>{issue.page_path}</span>
                    </div>
                  </div>
                  <div>
                    <Badge tone={statusTone[issue.status] ?? "default"}>{statusLabel[issue.status] ?? issue.status}</Badge>
                    <div className="mt-2 text-xs text-slate-500">{issue.risk === "high" ? "需要人审" : "低风险可先交付"}</div>
                  </div>
                  <div className="text-sm text-slate-600">{nextStep(issue)}</div>
                  <div className="text-right text-xs font-medium text-brand-700">{expanded ? "收起" : "展开处理"}</div>
                </button>

                {expanded ? (
                  <div className="border-t border-slate-100 bg-slate-50/60 p-4">
                    <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
                      <div className="space-y-2">
                        <div className="text-xs font-medium text-slate-500">诊断证据</div>
                        <p className="text-sm text-slate-700">{issue.detail || "暂无详情。"}</p>
                        {issue.evidence ? (
                          <pre className="max-h-44 overflow-auto whitespace-pre-wrap rounded-md bg-white p-3 text-xs text-slate-500">
                            {issue.evidence}
                          </pre>
                        ) : null}
                        {issue.ai_review ? <p className="text-xs text-slate-600">AI 初审：{issue.ai_review}</p> : null}
                        <div className="grid gap-2 pt-2 md:grid-cols-2">
                          <div className="rounded-md border border-slate-200 bg-white p-3">
                            <div className="text-xs font-medium text-slate-500">影响</div>
                            <p className="mt-1 text-sm text-slate-700">{issue.impact || "影响页面可被理解和复测。"}</p>
                          </div>
                          <div className="rounded-md border border-slate-200 bg-white p-3">
                            <div className="text-xs font-medium text-slate-500">执行角色</div>
                            <p className="mt-1 text-sm text-slate-700">{issue.owner_hint || "客户经理 / 执行人"}</p>
                          </div>
                        </div>
                      </div>
                      <div className="space-y-2">
                        <div className="text-xs font-medium text-slate-500">处理方案</div>
                        <div className="rounded-md border border-slate-200 bg-white p-3 text-sm text-slate-700">
                          <div className="text-xs font-medium text-slate-500">建议动作</div>
                          <p className="mt-1">{issue.recommended_action || "结合诊断证据补充处理方案，人工确认后执行。"}</p>
                          <div className="mt-3 text-xs font-medium text-slate-500">复测方法</div>
                          <p className="mt-1">{issue.retest_method || "执行后重新抓取页面并比对观察层。"}</p>
                        </div>
                        <Textarea
                          className="min-h-[120px] bg-white"
                          placeholder="填写给客户技术或内容执行人的整改方案。AI 建议不会自动执行。"
                          value={drafts[issue.id] ?? issue.proposed_change}
                          onChange={(e) => setDrafts({ ...drafts, [issue.id]: e.target.value })}
                        />
                        <div className="flex flex-wrap gap-2">
                          <Button asChild size="sm" variant="outline">
                            <Link href={`/onsite/${issue.page_id}`}>查看单页观察</Link>
                          </Button>
                          <Button size="sm" onClick={() => aiIssue(issue.id)} disabled={busyId === issue.id}>
                            <Bot className="mr-1.5 h-3.5 w-3.5" />
                            生成处理建议
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => saveDraft(issue)} disabled={busyId === issue.id}>
                            保存整改方案
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => copyDraft(issue)}>
                            <Copy className="mr-1.5 h-3.5 w-3.5" />
                            复制整改方案
                          </Button>
                          {issue.status === "confirmed" || issue.status === "draft_applied" ? (
                            <Button size="sm" variant="outline" onClick={() => retestIssue(issue)} disabled={busyId === issue.id}>
                              <RefreshCcw className="mr-1.5 h-3.5 w-3.5" />
                              复测本条
                            </Button>
                          ) : issue.severity === "low" && issue.risk === "low" ? (
                            <Button size="sm" variant="outline" onClick={() => apply(issue)} disabled={busyId === issue.id}>
                              交付执行人
                            </Button>
                          ) : (
                            <Button size="sm" onClick={() => apply(issue)} disabled={busyId === issue.id}>
                              <Wrench className="mr-1.5 h-3.5 w-3.5" />
                              标记已执行
                            </Button>
                          )}
                          <Button size="sm" variant="outline" onClick={() => ignoreIssue(issue)} disabled={busyId === issue.id}>
                            <XCircle className="mr-1.5 h-3.5 w-3.5" />
                            忽略
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
            );
          })}
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[1fr_0.9fr]">
        <Card className="rounded-md">
          <CardHeader>
          <CardTitle>登记重点页面</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="grid gap-3 md:grid-cols-4" onSubmit={create}>
              <Input placeholder="路径" value={form.path} onChange={(e) => setForm({ ...form, path: e.target.value })} required />
              <Input placeholder="语言" value={form.locale} onChange={(e) => setForm({ ...form, locale: e.target.value })} />
              <Input placeholder="页面名称" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
              <Button type="submit">加入诊断清单</Button>
            </form>
            <div className="mt-4 max-h-56 overflow-auto rounded-md border border-slate-200">
              {pages.map((p) => (
                <Link
                  key={p.id}
                  href={`/onsite/${p.id}`}
                  className="grid gap-1 border-b border-slate-100 px-3 py-2 text-sm last:border-b-0 hover:bg-slate-50 md:grid-cols-[1fr_auto]"
                >
                  <div>
                    <div className="font-medium text-brand-700">{p.path}</div>
                    <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-500">
                      <span>{p.priority_hint ?? "P2"}</span>
                      <span>{p.page_type ?? "other"}</span>
                      <span>深度 {p.url_depth ?? 0}</span>
                      <span>{p.discovery_source ?? "manual"}</span>
                      <span>sitemap {p.is_in_sitemap ?? "未测"}</span>
                      <span>字数 {p.word_count ?? 0}</span>
                      <span>缺 alt {p.images_missing_alt ?? 0}/{p.image_count ?? 0}</span>
                      <span>TTFB {p.ttfb_ms ?? "未测"}{p.ttfb_ms ? "ms" : ""}</span>
                      <span>跳转 {p.redirect_count ?? 0}</span>
                      <span>{p.content_type || "未知类型"}</span>
                    </div>
                  </div>
                  <div className="text-xs text-slate-500 md:text-right">
                    <div>{crawlStatusLabel[p.crawl_status] ?? p.crawl_status}</div>
                    {p.body_hash ? <div>hash {p.body_hash.slice(0, 8)}</div> : null}
                    <div>{p.fetched_at ? new Date(p.fetched_at).toLocaleString("zh-CN") : "尚未抓取"}</div>
                  </div>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-md">
          <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>内容选题辅助</CardTitle>
            <CheckCircle2 className="h-5 w-5 text-slate-400" />
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm text-slate-500">这里辅助内容生产。真正的 SEO 诊断仍以抓取、收录、搜索表现和高风险整改为主。</p>
            {briefs.length === 0 ? <p className="text-sm text-slate-500">还没有提纲。站内问题优先。</p> : null}
            {briefs.slice(0, 5).map((b) => (
              <div key={b.id} className="rounded-md border border-slate-200 p-3">
                <div className="font-medium">{b.title}</div>
                <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-500">
                  <span>{b.target_keyword}</span>
                  <span>{b.locale}</span>
                  <Badge tone="amber">SERP {b.serp_features}</Badge>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
