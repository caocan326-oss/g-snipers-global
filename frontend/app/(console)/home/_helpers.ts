import type { GscStatus, ProjectTargets, Workbench, WorkbenchSeoPerformance } from "@/lib/api";

export const toneBorder: Record<string, string> = {
  default: "border-slate-200",
  green: "border-emerald-200",
  amber: "border-amber-200",
  blue: "border-sky-200",
  red: "border-red-200",
  brand: "border-brand-200",
};

export const toneAccent: Record<string, string> = {
  default: "bg-slate-500",
  green: "bg-emerald-600",
  amber: "bg-amber-500",
  blue: "bg-sky-600",
  red: "bg-red-600",
  brand: "bg-brand-600",
};

export function seoPerformanceVerdict(perf: WorkbenchSeoPerformance) {
  if (perf.data_status !== "已导入" && perf.serp_runs === 0) {
    return {
      title: "搜索表现还没有证据",
      text: "先接入 Google 搜索表现数据，或导入 Google/Bing 表格；再用目标国家和核心词做关键词排名检查，报告才能判断客户在 Google 上有没有真实曝光。",
      tone: "amber",
    };
  }
  if (perf.total_impressions > 0 && perf.total_clicks === 0) {
    return {
      title: "已有曝光，但没有形成访问",
      text: "重点检查标题、描述、搜索意图匹配和目标国家页面。这个阶段不是只修技术问题，而是要把能看到客户的人变成愿意点击的人。",
      tone: "red",
    };
  }
  if (perf.avg_ctr !== null && perf.avg_ctr < 1) {
    return {
      title: "点击率偏低，优先优化搜索摘要",
      text: "关键词已经有展示机会，但页面标题、描述或内容承诺不够有吸引力。建议优先处理高曝光低点击词和对应页面。",
      tone: "amber",
    };
  }
  if (perf.serp_runs > 0 && perf.serp_own_visible_runs === 0) {
    return {
      title: "目标关键词前 10 暂未看到客户",
      text: "关键词排名检查已执行，但我方域名没有进入目标关键词前 10。下一步需要围绕目标市场补内容、内链和可被引用的第三方曝光。",
      tone: "red",
    };
  }
  return {
    title: "搜索表现已有基础证据",
    text: "可以继续按国家、关键词和页面拆解机会，把高曝光词、可提升页面和竞品可见位置转成执行清单。",
    tone: "green",
  };
}

export function activeTargetMarkets(targets: ProjectTargets | null) {
  const markets = targets?.markets ?? [];
  const priority = markets.filter((market) => market.status === "priority");
  return priority.length ? priority : markets.filter((market) => market.status !== "paused");
}

export function splitKeywordInput(text: string) {
  return text
    .split(/[\n,，;；]+/)
    .flatMap((part) => {
      const value = part.trim();
      if (!value) return [];
      return /[\u4e00-\u9fff]/.test(value) ? value.split(/\s+/).map((item) => item.trim()).filter(Boolean) : [value];
    });
}

export function reportReadyChecks(data: Workbench, targets: ProjectTargets | null, gsc: GscStatus | null) {
  const perf = data.seo_performance;
  const highRisk = data.summary.onsite_open_critical + data.summary.onsite_open_high;
  return [
    {
      label: "客户目标",
      status: targets?.readiness === "ready" ? "通过" : "待补",
      ok: targets?.readiness === "ready",
      detail: targets?.readiness === "ready" ? "官网、目标国家、关键词和竞品已登记。" : "缺少目标国家、关键词或竞品会让诊断不够聚焦。",
    },
    {
      label: "站内抓取",
      status: data.summary.onsite_pages > 0 ? "通过" : "待抓取",
      ok: data.summary.onsite_pages > 0,
      detail: data.summary.onsite_pages > 0 ? `已登记 ${data.summary.onsite_pages} 个页面。` : "需要先抓取官网或登记核心页面。",
    },
    {
      label: "搜索表现",
      status: perf.data_status === "已导入" || perf.serp_runs > 0 || perf.latest_speed_score !== null ? "有记录" : "尚未检查",
      ok: perf.data_status === "已导入" || perf.serp_runs > 0 || perf.latest_speed_score !== null,
      detail: perf.data_status === "已导入" ? "已有 Google/Bing 搜索表现。" : perf.serp_runs > 0 ? "已有目标词位置检查。" : "建议接入 Google/Bing、网页速度或关键词位置检查。",
    },
    {
      label: "AI 搜索记录",
      status: (data.summary.geo_latest_sampled ?? 0) > 0 || data.summary.geo_recorded > 0 ? "有记录" : "尚未检查",
      ok: (data.summary.geo_latest_sampled ?? 0) > 0 || data.summary.geo_recorded > 0,
      detail:
        (data.summary.geo_latest_sampled ?? 0) > 0
          ? `最近联网抽查了 ${data.summary.geo_latest_sampled} 个买家问题。`
          : data.summary.geo_recorded > 0
            ? `已有 ${data.summary.geo_recorded} 条 AI 搜索记录。`
            : "需要联网或人工检查。引擎空位不算已经抽查。",
    },
    {
      label: "紧急 / 优先问题",
      status: highRisk > 0 ? "需说明" : "通过",
      ok: highRisk === 0,
      detail: highRisk > 0 ? `仍有 ${highRisk} 个紧急或优先问题，说明里要列入改法和复查。` : "没有打开的紧急或优先网站问题。",
    },
    {
      label: "Google 数据授权",
      status: gsc?.connected ? "已连接" : gsc?.configured ? "待授权" : "未配置",
      ok: Boolean(gsc?.connected),
      detail: gsc?.connected ? "可自动同步真实搜索表现。" : "不阻塞报告导出，但会降低搜索表现可信度。",
    },
  ];
}
