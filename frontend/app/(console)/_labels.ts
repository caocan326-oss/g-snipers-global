export const executionStatusLabel: Record<string, string> = {
  open: "待处理",
  drafted: "已有方案",
  draft_applied: "已交给执行",
  confirmed: "待复测",
  in_progress: "进行中",
  converted_to_task: "已生成任务",
  needs_retest: "待复测",
  blocked: "受阻",
  reopened: "已重开",
  identified: "已发现",
  replied: "已回复",
  outreach: "跟进中",
  lost: "已放弃",
  verify: "待复查",
  watching: "观察中",
  pending: "待处理",
  todo: "待办",
  sent_manual: "已人工发送",
  ignored: "已忽略",
  won: "已拿下",
  skipped: "已跳过",
};

export const priorityHintLabel: Record<string, string> = {
  P0: "紧急",
  P1: "优先",
  P2: "常规",
  P3: "观察",
};

export const pageTypeLabel: Record<string, string> = {
  other: "其他页",
  home: "首页",
  product: "产品页",
  category: "分类页",
  article: "文章",
  blog: "博客",
  landing: "落地页",
  about: "关于",
  contact: "联系",
};

export const discoverySourceLabel: Record<string, string> = {
  manual: "手工登记",
  crawl: "抓取",
  sitemap: "站点地图",
  seed: "演示导入",
};

export function labelOr(map: Record<string, string>, value: string | null | undefined, fallback = "未填写") {
  const key = (value || "").trim();
  if (!key) return fallback;
  return map[key] ?? key;
}
