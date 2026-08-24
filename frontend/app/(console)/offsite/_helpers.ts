export const verifyLabel: Record<string, string> = {
  unverified: "待核验",
  valid: "已确认有效",
  dead: "链接失效",
  spam: "低质/垃圾",
};

export const verifyTone: Record<string, "amber" | "green" | "red" | "default"> = {
  unverified: "amber",
  valid: "green",
  dead: "red",
  spam: "default",
};

export const kindLabel: Record<string, string> = {
  inbound: "我方已获曝光",
  competitor: "竞品已覆盖",
};

export const gapLabel: Record<string, string> = {
  identified: "待判断价值",
  outreach: "跟进中",
  replied: "已有回复",
  converted_to_task: "已生成任务",
  in_progress: "执行中",
  needs_retest: "待复测",
  won: "已拿到曝光",
  lost: "本次失败",
  skipped: "本季不做",
  blocked: "受阻",
  closed: "已关闭",
  ignored: "暂不处理",
};

export function jobStatusText(job: { status: string; last_result?: string; blocked_reason?: string }) {
  if (
    job.status === "blocked" &&
    (job.last_result === "缺账号" || (job.blocked_reason || "").includes("needs_account"))
  ) {
    return "缺账号受阻";
  }
  return jobStatusLabel[job.status] ?? job.status;
}

export function jobChannelLabel(job: { platform_id?: string | null; provider_key: string }, platforms: { id: string; name: string }[]) {
  const platform = platforms.find((row) => row.id === job.platform_id);
  if (platform?.name) return platform.name;
  return "客户自己发";
}

const FILLBACK_NOT_SEND = "登记≠我们代发";

export function jobVerifyNote(job: { last_detail?: string; status?: string; result_url?: string }) {
  const detail = (job.last_detail || "").trim();
  if (!detail) return "";
  if (detail.includes(FILLBACK_NOT_SEND)) return detail;
  if (job.result_url || job.status === "submitted") {
    return `${detail}${FILLBACK_NOT_SEND}。`;
  }
  return detail;
}

export const jobStatusLabel: Record<string, string> = {
  draft: "草稿",
  ready: "资料齐全",
  in_progress: "执行中",
  submitted: "已回填",
  verifying: "核验中",
  done: "已完成",
  queued: "待人工执行",
  blocked: "配置受阻",
  blocked_unconfigured: "渠道未配置",
  sent: "已执行",
  failed: "执行失败",
  cancelled: "已取消",
};

export const taskTypeLabel: Record<string, string> = {
  profile_create: "新建平台档案",
  profile_update: "补全平台档案",
  brand_fix: "修正品牌信息",
  product_listing: "产品/规格上架",
  listicle_pitch: "申请进入榜单",
  guest_or_pr: "稿件/PR",
  distributor_align: "分销商页面对齐",
  link_claim: "认领未链接提及",
  monitor_only: "只监控",
  social_profile_update: "维护社媒主页",
  social_post_plan: "社媒发布计划",
};

export const platformTypeLabel: Record<string, string> = {
  directory: "行业目录",
  marketplace: "B2B 平台",
  association: "协会/标准",
  distributor: "分销商/渠道",
  media: "媒体",
  listicle: "榜单/测评",
  community: "问答/社区",
  social_profile: "社媒主页",
  knowledge_graph: "实体/知识图谱",
  monitoring: "核验/监控",
};

export const submissionLabel: Record<string, string> = {
  manual_login: "人工登录",
  email_outreach: "邮件联系",
  form_public: "公开表单",
  paid_placement: "付费位",
  api_none: "只读/监控",
};

export type Tab = "channels" | "opportunities" | "distribution" | "placements" | "content" | "platforms";
