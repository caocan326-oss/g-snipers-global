import type { GeoSampleRun, GeoSummary } from "@/lib/api";

export type Tab = "sample" | "tickets" | "assets";

export const obsLabel: Record<string, string> = {
  untested: "未测",
  mentioned: "出现",
  not_mentioned: "未出现",
  cited: "被引用",
  verified: "引用已核验",
};

export const obsTone: Record<string, "default" | "amber" | "green" | "red" | "blue"> = {
  untested: "amber",
  mentioned: "blue",
  not_mentioned: "default",
  cited: "green",
  verified: "green",
};

export const evidenceLabel: Record<string, string> = {
  none: "无证据",
  mentioned: "正文提及",
  cited: "引用待核验",
  verified: "引用已核验",
};

export const diagnosisOptions = [
  ["untested", "未测"],
  ["absent", "未出现"],
  ["mentioned", "被提及"],
  ["competitor_dominated", "竞品主导"],
  ["suspected_negative", "疑似负面"],
] as const;

export const ticketStatus: Record<string, string> = {
  open: "待办",
  in_progress: "执行中",
  verify: "待验收",
  done: "已验收",
  reopened: "已重开",
};

export const providerRoleLabel: Record<string, string> = {
  analysis: "分析建议",
  search: "联网搜索",
  grounded_answer: "联网答案",
  citation: "引用来源",
  crawler: "抓取证据",
};

export function geoEvidenceVerdict(summary: GeoSummary | null, runs: GeoSampleRun[]) {
  const results = runs.flatMap((run) => run.results);
  const webGrounded = results.filter((result) => result.web_grounded === "true");
  const verified = webGrounded.filter((result) => result.verification_status === "passed");
  const pendingOwned = webGrounded.filter((result) => result.owned_citations.length > 0 && result.verification_status !== "passed");
  const thirdPartyOnly = webGrounded.filter((result) => result.third_party_citations.length > 0 && result.owned_citations.length === 0);
  if (!summary?.recorded && runs.length === 0) {
    return {
      title: "还没有可写入报告的 GEO 证据",
      text: "先生成买家问题，再用联网 provider 或人工观测记录采样。未采样不能写成 AI 可见性结论。",
      tone: "amber" as const,
      level: "未采样",
    };
  }
  if (results.length > 0 && webGrounded.length === 0) {
    return {
      title: "当前主要是分析参考，不是联网引用证据",
      text: "DeepSeek/普通 LLM 可用于判断表达和生成建议，但没有联网 source URL 时，不能计入真实引用率。",
      tone: "blue" as const,
      level: "分析参考",
    };
  }
  if (verified.length > 0) {
    return {
      title: "已有可写入报告的核验引用",
      text: `已有 ${verified.length} 条联网引用通过核验，可以进入报告；未核验 URL 仍应标记为待确认。`,
      tone: "green" as const,
      level: "可交付",
    };
  }
  if (pendingOwned.length > 0) {
    return {
      title: "发现官网引用，但还需要核验",
      text: `已有 ${pendingOwned.length} 条疑似自有引用。请核验 URL 可访问、内容相关、确属客户资产后再写入正式结论。`,
      tone: "amber" as const,
      level: "待核验",
    };
  }
  if (thirdPartyOnly.length > 0) {
    return {
      title: "有第三方来源，可转站外机会",
      text: "当前更适合生成站外来源候选和 GEO 机会，不能直接算作客户官网被引用。",
      tone: "blue" as const,
      level: "来源发现",
    };
  }
  return {
    title: "证据不足，需要补采样",
    text: "已有观测记录，但缺少可追溯的联网 URL、品牌提及或引用核验。",
    tone: "amber" as const,
    level: "证据不足",
  };
}

export type GeoEvidenceVerdict = ReturnType<typeof geoEvidenceVerdict>;
