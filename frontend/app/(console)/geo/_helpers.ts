import type { GeoSampleRun, GeoSummary } from "@/lib/api";

export type Tab = "sample" | "tickets" | "assets";

export const obsLabel: Record<string, string> = {
  untested: "尚未检查",
  mentioned: "被提到",
  not_mentioned: "未提到",
  cited: "给出了官网",
  verified: "官网来源已核对",
};

export const obsTone: Record<string, "default" | "amber" | "green" | "red" | "blue"> = {
  untested: "amber",
  mentioned: "blue",
  not_mentioned: "default",
  cited: "green",
  verified: "green",
};

export const evidenceLabel: Record<string, string> = {
  none: "尚无记录",
  mentioned: "正文提到",
  cited: "给出官网，待核对",
  verified: "官网来源已核对",
};

export const diagnosisOptions = [
  ["untested", "尚未检查"],
  ["absent", "未提到"],
  ["mentioned", "被提到"],
  ["competitor_dominated", "主要在推竞品"],
  ["suspected_negative", "可能偏负面"],
] as const;

export const ticketStatus: Record<string, string> = {
  open: "待处理",
  in_progress: "进行中",
  verify: "待复查",
  done: "已完成",
  reopened: "已重开",
};

export const providerRoleLabel: Record<string, string> = {
  analysis: "分析建议",
  search: "联网搜索",
  grounded_answer: "联网回答",
  citation: "来源网址",
  crawler: "网页记录",
};

export function geoEvidenceVerdict(summary: GeoSummary | null, runs: GeoSampleRun[]) {
  const results = runs.flatMap((run) => run.results);
  const webGrounded = results.filter((result) => result.web_grounded === "true");
  const verified = webGrounded.filter((result) => result.verification_status === "passed");
  const pendingOwned = webGrounded.filter((result) => result.owned_citations.length > 0 && result.verification_status !== "passed");
  const thirdPartyOnly = webGrounded.filter((result) => result.third_party_citations.length > 0 && result.owned_citations.length === 0);
  if (!summary?.recorded && runs.length === 0 && !(summary?.evidence_results || summary?.latest_sampled)) {
    return {
      title: "还没有可写入说明的检查记录",
      text: "先生成买家问题，再用联网数据源或人工记录回答。尚未检查时，不能写成 AI 已经提到你们。",
      tone: "amber" as const,
      level: "尚未检查",
    };
  }
  if (results.length > 0 && webGrounded.length === 0) {
    return {
      title: "目前只是分析参考，不是联网来源",
      text: "普通大模型可以判断说法、生成建议；没有联网来源网址时，不能算作给出了官网。",
      tone: "blue" as const,
      level: "分析参考",
    };
  }
  if (verified.length > 0) {
    return {
      title: "已有可写入说明的核对来源",
      text: `已有 ${verified.length} 条联网来源通过核对，可以写入说明；未核对的网址仍应标为待确认。`,
      tone: "green" as const,
      level: "可交付",
    };
  }
  if (pendingOwned.length > 0) {
    return {
      title: "发现疑似官网来源，还需核对",
      text: `已有 ${pendingOwned.length} 条疑似客户自己的网址。请在检查批次里打开客户官网链接，点「打开过，核对通过」后再写入正式结论。购物页不能勾通过。`,
      tone: "amber" as const,
      level: "待核对",
    };
  }
  const mentionedNoOwned = webGrounded.filter((result) => result.mentioned && result.owned_citations.length === 0);
  if (mentionedNoOwned.length > 0) {
    return {
      title: "提到了品牌，但没有客户官网链接",
      text: "正文里提到了客户，抽查链接里没有客户域名，所以页面上不会出现「核对通过」。上线地址栏填的官网不算抽查给出了官网。要等下一轮抽查真的带回客户官网链接，才能核对。",
      tone: "amber" as const,
      level: "缺官网链接",
    };
  }
  if (thirdPartyOnly.length > 0) {
    return {
      title: "有第三方来源，可转站外跟进",
      text: "当前更适合记为外部曝光线索，不能直接算作客户官网被给出。",
      tone: "blue" as const,
      level: "发现来源",
    };
  }
  return {
    title: "记录不足，需要再检查",
    text: "已有回答记录，但缺少可追溯的联网网址、品牌提及或来源核对。",
    tone: "amber" as const,
    level: "记录不足",
  };
}

export type GeoEvidenceVerdict = ReturnType<typeof geoEvidenceVerdict>;

export const diagnosisLabel: Record<string, string> = Object.fromEntries(diagnosisOptions);

export function displayRate(value: string | null | undefined) {
  if (!value || value === "未测") return "尚未检查";
  return value;
}

export function formatCheckAt(value: string | null | undefined) {
  if (!value) return "暂无";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "暂无";
  return date.toLocaleString("zh-CN", {
    timeZone: "Asia/Shanghai",
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
