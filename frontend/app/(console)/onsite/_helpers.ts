import type { OnsiteIssue, SeoPerformanceSummary } from "@/lib/api";

export const issuePlainTitle: Record<string, string> = {
  "收录状态未测（需 GSC）": "还没确认谷歌有没有收到这个页",
  "搜索是否收录尚未检查": "还没确认谷歌有没有收到这个页",
  "Canonical 未登记": "标准网址没写清，搜索可能认错页",
  "标准网址未登记": "标准网址没写清，搜索可能认错页",
  "缺少 JSON-LD / schema": "页面缺少给搜索看的说明",
  "缺少页面说明标记": "页面缺少给搜索看的说明",
  "首页公司说明标记缺失": "首页缺少公司介绍说明",
  "页面声明 noindex": "这个页告诉搜索不要收录",
  "缺少 H1": "页面缺少主标题",
  "缺少 Title": "搜索结果里可能没有标题",
  "Description 过短或为空": "搜索摘要几乎是空的",
  "页面摘要过短": "搜索摘要太短",
  "正文内容过薄": "正文太少，买家看不够",
  "图片 Alt 缺失": "图片没有文字说明",
  "缺少内链": "和其他页缺少互相链接",
  "URL 层级过深": "网址层级太深，不好被找到",
  "GEO-SCHEMA-002 Schema 类型与正文弱一致": "页面说明和正文对不上",
  "GEO-ENT-002 缺少 Organization / WebSite schema": "首页缺少公司介绍说明",
};

export function plainIssueTitle(title: string) {
  return issuePlainTitle[title] || title;
}

export const catLabel: Record<string, string> = {
  tdk: "标题与摘要",
  heading: "页面标题",
  internal_link: "站内链接",
  schema: "页面说明标记",
  index: "搜索是否收录",
  crawl: "页面能否打开",
  canonical: "标准网址",
  image: "图片",
  content: "正文",
  b2b: "询盘页",
};

export const sevLabel: Record<string, string> = { critical: "紧急", high: "优先", low: "常规" };
export const sevTone: Record<string, "red" | "amber" | "green"> = { critical: "red", high: "amber", low: "green" };
export const statusLabel: Record<string, string> = {
  open: "待写改法",
  drafted: "改法已写，待上线",
  draft_applied: "已交给执行",
  confirmed: "已修改，待复查",
  verified: "复查通过",
  wont_fix: "本轮不改",
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
  { key: "needs_review", label: "需确认" },
  { key: "critical", label: "紧急" },
  { key: "high", label: "优先" },
  { key: "low", label: "常规" },
  { key: "needs_draft", label: "待写改法" },
  { key: "ready_to_execute", label: "待上线" },
  { key: "waiting_retest", label: "待复查" },
  { key: "untested", label: "尚未检查" },
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
  if (issue.severity === "critical") return "紧急";
  if (issue.severity === "high" || issue.risk === "high") return "优先";
  if (issue.status === "confirmed") return "优先";
  return "常规";
}

export function priorityRank(issue: OnsiteIssue) {
  const severityRank: Record<string, number> = { critical: 0, high: 10, low: 20 };
  const statusRank: Record<string, number> = { confirmed: 0, drafted: 1, open: 2, draft_applied: 3 };
  return (severityRank[issue.severity] ?? 20) + (statusRank[issue.status] ?? 5);
}

export function nextStep(issue: OnsiteIssue) {
  if (issue.status === "confirmed") return "重新打开页面核对";
  if (issue.status === "draft_applied") return "等待修改后再复查";
  if (issue.status === "drafted") return issue.risk === "high" ? "确认后交给网站执行" : "交给执行修改";
  if (!issue.proposed_change.trim()) return "先写改法";
  return "保存改法并继续";
}

export function performanceVerdict(performance: SeoPerformanceSummary | null) {
  if (!performance) return { title: "正在读取搜索数据", text: "正在读取 Google / Bing 的展示、点击和页面速度。", tone: "default" as const };
  if (performance.gsc_status !== "已导入" && performance.bing_status !== "已导入") {
    return {
      title: "还没有真实搜索数据",
      text: "目前只看过网站页面，还不能判断在目标国家有没有被搜到、有没有人点进来。请先接入 Google 搜索数据，或导入表格。",
      tone: "amber" as const,
    };
  }
  if (performance.total_impressions > 0 && performance.total_clicks === 0) {
    return {
      title: "有人看到，但没有点进来",
      text: "优先改这些词对应页面的标题、摘要和首页承诺，让看得到的人愿意点开。",
      tone: "red" as const,
    };
  }
  if (performance.avg_ctr !== null && performance.avg_ctr < 1) {
    return {
      title: "点开率偏低",
      text: "搜索结果里已经出现，但标题或摘要不够吸引。先处理展示多、点击少的词，再过一段时间对照。",
      tone: "amber" as const,
    };
  }
  return {
    title: "已有搜索数据可作依据",
    text: "可以按国家、关键词和页面对齐改法，优先处理能带来访问的页面。",
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
