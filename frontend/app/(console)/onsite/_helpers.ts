import type { OnsiteIssue, SeoPerformanceSummary } from "@/lib/api";

export const catLabel: Record<string, string> = {
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

export const sevLabel: Record<string, string> = { critical: "Critical", high: "High", low: "Low" };
export const sevTone: Record<string, "red" | "amber" | "green"> = { critical: "red", high: "amber", low: "green" };
export const statusLabel: Record<string, string> = {
  open: "待写处理方案",
  drafted: "已有方案，待人工上线",
  draft_applied: "已交付执行人",
  confirmed: "已人工上线，待回抓",
  verified: "观察已验收",
  wont_fix: "不做",
};

export const statusTone: Record<string, "default" | "amber" | "green" | "blue" | "red"> = {
  open: "amber",
  drafted: "blue",
  draft_applied: "amber",
  confirmed: "red",
  verified: "green",
  wont_fix: "default",
};

export const filters = [
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

export const SNIPERS_TEST_ORIGIN = "https://www.snipers.com.cn";
export const SNIPERS_TEST_PAGES = [
  { path: "/", locale: "zh-CN", title: "Snipers 官网首页" },
  { path: "/g-snipers/", locale: "zh-CN", title: "G-Snipers" },
  { path: "/category/seo/", locale: "zh-CN", title: "SEO 文章栏目" },
  { path: "/category/geo/", locale: "zh-CN", title: "GEO 文章栏目" },
];

export type FilterKey = (typeof filters)[number]["key"];

export function priorityLabel(issue: OnsiteIssue) {
  if (issue.severity === "critical") return "P0";
  if (issue.severity === "high" || issue.risk === "high") return "P1";
  if (issue.status === "confirmed") return "P1";
  return "P2";
}

export function priorityRank(issue: OnsiteIssue) {
  const severityRank: Record<string, number> = { critical: 0, high: 10, low: 20 };
  const statusRank: Record<string, number> = { confirmed: 0, drafted: 1, open: 2, draft_applied: 3 };
  return (severityRank[issue.severity] ?? 20) + (statusRank[issue.status] ?? 5);
}

export function nextStep(issue: OnsiteIssue) {
  if (issue.status === "confirmed") return "回抓验收";
  if (issue.status === "draft_applied") return "等待执行后复测";
  if (issue.status === "drafted") return issue.risk === "high" ? "交给技术/客户上线" : "交付执行";
  if (!issue.proposed_change.trim()) return "生成或填写处理方案";
  return "保存方案并推进";
}

export function performanceVerdict(performance: SeoPerformanceSummary | null) {
  if (!performance) return { title: "搜索表现读取中", text: "正在读取 Google/Bing 搜索表现、网页速度和关键词排名检查状态。", tone: "default" as const };
  if (performance.gsc_status !== "已导入" && performance.bing_status !== "已导入") {
    return {
      title: "缺少真实搜索表现",
      text: "当前只有网站抓取结果，还不能判断客户在目标国家有没有曝光、点击和排名机会。请先授权 Google 搜索表现数据，或导入 Google/Bing 导出的表格。",
      tone: "amber" as const,
    };
  }
  if (performance.total_impressions > 0 && performance.total_clicks === 0) {
    return {
      title: "有曝光但没有点击",
      text: "建议优先优化高曝光关键词对应页面的 Title、Description、首屏承诺和采购意图匹配。",
      tone: "red" as const,
    };
  }
  if (performance.avg_ctr !== null && performance.avg_ctr < 1) {
    return {
      title: "CTR 偏低",
      text: "已有搜索展示，但搜索摘要吸引力不足。先处理高曝光低点击词，再复测 28 天表现。",
      tone: "amber" as const,
    };
  }
  return {
    title: "搜索表现已有证据",
    text: "可以把关键词、国家、页面和排名检查结果一起纳入整改优先级，形成更像客户报告的结论。",
    tone: "green" as const,
  };
}

export function matchesFilter(issue: OnsiteIssue, filter: FilterKey) {
  if (filter === "all") return true;
  if (filter === "needs_review") return Boolean(issue.review_required);
  if (filter === "critical" || filter === "high" || filter === "low") return issue.severity === filter;
  if (filter === "needs_draft") return issue.status === "open" && !issue.proposed_change.trim();
  if (filter === "ready_to_execute") return issue.status === "drafted";
  if (filter === "waiting_retest") return issue.status === "confirmed" || issue.status === "draft_applied";
  if (filter === "untested") return issue.metric_status === "untested";
  return true;
}
