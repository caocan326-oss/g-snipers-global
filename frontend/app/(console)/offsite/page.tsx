"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Bot,
  CheckCircle2,
  ClipboardList,
  ExternalLink,
  Link2,
  RadioTower,
  RefreshCw,
  Send,
  ShieldCheck,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  api,
  type AiAssist,
  type BacklinkGap,
  type ContentAsset,
  type ContentAssetReview,
  type DistGuide,
  type DistJob,
  type DistProvider,
  type FactPack,
  type PlacementCheck,
  type PlatformAccount,
  type PlatformConnector,
  type SourcePlatform,
  type SourcePlatformSeed,
} from "@/lib/api";

const verifyLabel: Record<string, string> = {
  unverified: "待核验",
  valid: "已确认有效",
  dead: "链接失效",
  spam: "低质/垃圾",
};

const verifyTone: Record<string, "amber" | "green" | "red" | "default"> = {
  unverified: "amber",
  valid: "green",
  dead: "red",
  spam: "default",
};

const kindLabel: Record<string, string> = {
  inbound: "我方已获曝光",
  competitor: "竞品曝光机会",
};

const gapLabel: Record<string, string> = {
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

const jobStatusLabel: Record<string, string> = {
  draft: "草稿",
  ready: "资料齐全",
  in_progress: "执行中",
  submitted: "已提交",
  verifying: "核验中",
  done: "已完成",
  queued: "待人工执行",
  blocked: "配置受阻",
  blocked_unconfigured: "渠道未配置",
  sent: "已执行",
  failed: "执行失败",
  cancelled: "已取消",
};

const taskTypeLabel: Record<string, string> = {
  profile_create: "新建平台档案",
  profile_update: "补全平台档案",
  brand_fix: "修正品牌信息",
  product_listing: "产品/规格上架",
  listicle_pitch: "申请进入榜单",
  guest_or_pr: "稿件/PR",
  distributor_align: "分销商页面对齐",
  link_claim: "认领未链接提及",
  monitor_only: "只监控",
};

type Tab = "opportunities" | "distribution" | "placements" | "content" | "platforms";

function StatTile({ label, value, helper }: { label: string; value: string | number; helper: string }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-slate-950">{value}</div>
      <div className="mt-1 text-xs leading-5 text-slate-500">{helper}</div>
    </div>
  );
}

function WorkflowStep({
  icon: Icon,
  title,
  value,
  helper,
}: {
  icon: typeof RadioTower;
  title: string;
  value: string | number;
  helper: string;
}) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-brand-700" />
        <div className="text-sm font-semibold text-slate-900">{title}</div>
      </div>
      <div className="mt-3 text-2xl font-semibold text-slate-950">{value}</div>
      <p className="mt-1 text-xs leading-5 text-slate-500">{helper}</p>
    </div>
  );
}

export default function OffsitePage() {
  const [tab, setTab] = useState<Tab>("opportunities");
  const [filter, setFilter] = useState<"all" | "unverified" | "valid" | "dead" | "spam">("all");
  const [gaps, setGaps] = useState<BacklinkGap[]>([]);
  const [providers, setProviders] = useState<DistProvider[]>([]);
  const [jobs, setJobs] = useState<DistJob[]>([]);
  const [platforms, setPlatforms] = useState<SourcePlatform[]>([]);
  const [accounts, setAccounts] = useState<PlatformAccount[]>([]);
  const [connectors, setConnectors] = useState<PlatformConnector[]>([]);
  const [factPacks, setFactPacks] = useState<FactPack[]>([]);
  const [assets, setAssets] = useState<ContentAsset[]>([]);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [form, setForm] = useState({
    title: "",
    issue_type: "competitor_gap",
    priority: "P2",
    owner_hint: "",
    competitor_name: "",
    referring_domain: "",
    link_url: "",
    kind: "competitor",
    acceptance_criteria: "",
    recommended_action: "",
    retest_method: "",
    notes: "",
  });
  const [contact, setContact] = useState("");
  const [distForm, setDistForm] = useState({
    gap_id: "",
    platform_id: "",
    account_id: "",
    content_asset_id: "",
    title: "",
    target_url: "/",
    provider_key: "directory",
    task_type: "profile_create",
    payload_summary: "",
    owner_hint: "",
    result_url: "",
  });
  const [platformForm, setPlatformForm] = useState({
    platform_key: "",
    name: "",
    domain: "",
    source_type: "directory",
    regions: "US",
    industry_tags: "",
    base_url: "",
    listing_model: "directory_profile",
    submission_mode: "manual_login",
    has_official_api: false,
    risk_level: "medium",
    status: "active",
    notes: "",
  });
  const [accountForm, setAccountForm] = useState({
    platform_id: "",
    label: "",
    login_identifier: "",
    auth_method: "manual_only",
    vault_ref: "",
    owner_hint: "",
    scope: "shared",
    status: "active",
    risk_level: "medium",
    regions_allowed: "",
    notes: "",
  });
  const [connectorForm, setConnectorForm] = useState({
    platform_id: "",
    provider_key: "",
    auth_mode: "manual",
    capabilities: "draft_only",
    status: "manual_only",
    env_var: "",
    notes: "",
  });
  const [factForm, setFactForm] = useState({
    name: "Default Fact Pack",
    legal_name: "",
    brand_names: "",
    website: "",
    product_categories_en: "",
    certifications: "",
    key_specs: "",
    banned_claims: "",
    contact_public: "",
    approved_boilerplate_en: "",
  });
  const [assetForm, setAssetForm] = useState({
    fact_pack_id: "",
    asset_type: "company_blurb",
    title: "",
    body_md: "",
    locale: "en",
    keywords: "",
    entities: "",
  });
  const [resultForms, setResultForms] = useState<Record<string, string>>({});
  const [guides, setGuides] = useState<Record<string, DistGuide>>({});
  const [placementChecks, setPlacementChecks] = useState<Record<string, PlacementCheck>>({});

  const stats = useMemo(() => {
    const activeOpportunities = gaps.filter((g) => !["won", "closed", "ignored", "skipped"].includes(g.status)).length;
    const validPlacements = gaps.filter((g) => g.verify_status === "valid").length;
    const needsReview = gaps.filter((g) => g.verify_status === "unverified").length;
    const openJobs = jobs.filter((j) => !["sent", "done"].includes(j.status)).length;
    const approvedAssets = assets.filter((a) => a.status === "human_approved").length;
    return { activeOpportunities, validPlacements, needsReview, openJobs, approvedAssets };
  }, [gaps, jobs, assets]);

  function loadGaps() {
    api<BacklinkGap[]>("/api/offsite/gaps").then(setGaps).catch((e) => setError(e.message));
  }

  function loadDist() {
    Promise.all([api<DistProvider[]>("/api/distribution/providers"), api<DistJob[]>("/api/distribution/jobs")])
      .then(([p, j]) => {
        setProviders(p);
        setJobs(j);
        if (p.length && !p.some((item) => item.key === distForm.provider_key)) {
          setDistForm((current) => ({ ...current, provider_key: p[0].key }));
        }
      })
      .catch((e) => setError(e.message));
  }

  function loadPlatforms() {
    Promise.all([
      api<SourcePlatform[]>("/api/offsite/platforms"),
      api<PlatformAccount[]>("/api/offsite/accounts"),
      api<PlatformConnector[]>("/api/offsite/connectors"),
    ])
      .then(([p, a, c]) => {
        setPlatforms(p);
        setAccounts(a);
        setConnectors(c);
        if (p.length) {
          setAccountForm((current) => ({ ...current, platform_id: current.platform_id || p[0].id }));
          setConnectorForm((current) => ({ ...current, platform_id: current.platform_id || p[0].id }));
        }
      })
      .catch((e) => setError(e.message));
  }

  function loadContent() {
    Promise.all([api<FactPack[]>("/api/offsite/fact-packs"), api<ContentAsset[]>("/api/offsite/content-assets")])
      .then(([facts, rows]) => {
        setFactPacks(facts);
        setAssets(rows);
        if (facts.length) {
          setAssetForm((current) => ({ ...current, fact_pack_id: current.fact_pack_id || facts[0].id }));
        }
      })
      .catch((e) => setError(e.message));
  }

  useEffect(() => {
    const queryTab = typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("tab") : "";
    if (queryTab === "dist") setTab("distribution");
    loadGaps();
    loadDist();
    loadPlatforms();
    loadContent();
  }, []);

  async function addGap(e: FormEvent) {
    e.preventDefault();
    setError("");
    setNote("");
    await api("/api/offsite/gaps", { method: "POST", body: JSON.stringify(form) });
    setForm({
      title: "",
      issue_type: "competitor_gap",
      priority: "P2",
      owner_hint: "",
      competitor_name: "",
      referring_domain: "",
      link_url: "",
      kind: "competitor",
      acceptance_criteria: "",
      recommended_action: "",
      retest_method: "",
      notes: "",
    });
    setNote("站外机会已加入机会池。");
    loadGaps();
  }

  function prepareJobFromGap(gap: BacklinkGap) {
    setDistForm({
      gap_id: gap.id,
      title: gap.title || `${gap.referring_domain} 站外曝光执行`,
      platform_id: platforms.find((p) => p.domain && gap.referring_domain.includes(p.domain))?.id || "",
      account_id: "",
      content_asset_id: "",
      target_url: gap.result_url || gap.link_url || "/",
      provider_key: providers[0]?.key || "directory",
      task_type: gap.issue_type === "unlinked_mention" ? "link_claim" : gap.kind === "inbound" ? "monitor_only" : "profile_create",
      payload_summary: gap.recommended_action || gap.notes || `围绕 ${gap.referring_domain} 推进站外曝光机会。`,
      owner_hint: gap.owner_hint || "站外执行",
      result_url: gap.result_url || "",
    });
    setTab("distribution");
    setNote("已把该站外机会带入分发任务表单。");
  }

  async function updateGap(id: string, payload: Record<string, string>) {
    setError("");
    setNote("");
    await api(`/api/offsite/gaps/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
    setNote("站外机会已更新。");
    loadGaps();
  }

  async function aiGap(id: string) {
    setError("");
    setNote("");
    const res = await api<AiAssist>(`/api/offsite/gaps/${id}/ai`, { method: "POST", body: JSON.stringify({ step: "evidence" }) });
    if (res.status === "未配置") setError(res.detail);
    else setNote("AI 已补充价值判断和证据说明。");
    loadGaps();
  }

  async function setVerify(id: string, verify_status: string) {
    setError("");
    const status = verify_status === "valid" ? "won" : verify_status === "dead" ? "needs_retest" : undefined;
    await api(`/api/offsite/gaps/${id}`, { method: "PATCH", body: JSON.stringify({ verify_status, ...(status ? { status } : {}) }) });
    setNote("Placement 核验状态已更新。");
    loadGaps();
  }

  async function addOutreach(gapId: string) {
    if (!contact.trim()) {
      setError("请先填写联系人、平台账号或跟进对象。");
      return;
    }
    setError("");
    await api(`/api/offsite/gaps/${gapId}/outreach`, {
      method: "POST",
      body: JSON.stringify({ contact, channel: "manual" }),
    });
    setContact("");
    setNote("跟进记录已加入该机会。");
    loadGaps();
  }

  async function createJob(e: FormEvent) {
    e.preventDefault();
    setError("");
    setNote("");
    await api("/api/distribution/jobs", { method: "POST", body: JSON.stringify(distForm) });
    setDistForm({ ...distForm, gap_id: "", platform_id: "", account_id: "", content_asset_id: "", title: "", payload_summary: "", result_url: "" });
    setNote("分发任务已创建，等待人工确认执行。");
    loadGaps();
    loadDist();
  }

  async function createPlatform(e: FormEvent) {
    e.preventDefault();
    setError("");
    setNote("");
    await api("/api/offsite/platforms", { method: "POST", body: JSON.stringify(platformForm) });
    setPlatformForm({ ...platformForm, platform_key: "", name: "", domain: "", base_url: "", industry_tags: "", notes: "" });
    setNote("平台已加入资源库。");
    loadPlatforms();
  }

  async function seedPlatforms() {
    setError("");
    setNote("");
    const res = await api<SourcePlatformSeed>("/api/offsite/platforms/seed-b2b", { method: "POST" });
    setPlatforms(res.platforms);
    setNote(`已导入 ${res.created} 个 B2B 常用平台，跳过 ${res.skipped} 个已有平台。`);
  }

  async function saveFactPack(e: FormEvent) {
    e.preventDefault();
    setError("");
    setNote("");
    const saved = await api<FactPack>("/api/offsite/fact-packs", { method: "POST", body: JSON.stringify(factForm) });
    setFactForm({ ...factForm, name: "Default Fact Pack", legal_name: "", brand_names: "", website: "", product_categories_en: "", certifications: "", key_specs: "", banned_claims: "", contact_public: "", approved_boilerplate_en: "" });
    setAssetForm((current) => ({ ...current, fact_pack_id: saved.id }));
    setNote("Fact Pack 已保存，批准后才能生成对外内容草稿。");
    loadContent();
  }

  async function approveFactPack(id: string) {
    setError("");
    setNote("");
    await api(`/api/offsite/fact-packs/${id}/approve`, { method: "POST", body: JSON.stringify({ confirmed: true, note: "人工确认事实源" }) });
    setNote("Fact Pack 已人工批准。");
    loadContent();
  }

  async function saveAsset(e: FormEvent) {
    e.preventDefault();
    setError("");
    setNote("");
    await api("/api/offsite/content-assets", { method: "POST", body: JSON.stringify(assetForm) });
    setAssetForm({ ...assetForm, title: "", body_md: "", keywords: "", entities: "" });
    setNote("内容资产已保存为草稿。");
    loadContent();
  }

  async function generateAsset() {
    if (!assetForm.fact_pack_id) {
      setError("请先选择已批准的 Fact Pack。");
      return;
    }
    setError("");
    setNote("");
    await api("/api/offsite/content-assets/generate", {
      method: "POST",
      body: JSON.stringify({
        fact_pack_id: assetForm.fact_pack_id,
        asset_type: assetForm.asset_type,
        title: assetForm.title,
        locale: assetForm.locale,
      }),
    });
    setNote("已基于 Fact Pack 生成内容草稿。");
    loadContent();
  }

  async function reviewAsset(id: string) {
    setError("");
    setNote("");
    const res = await api<ContentAssetReview>(`/api/offsite/content-assets/${id}/ai-review`, { method: "POST" });
    setNote(res.findings.length ? `AI 初审发现 ${res.findings.length} 个问题。` : "AI 初审通过，仍需人工批准。");
    loadContent();
  }

  async function approveAsset(id: string) {
    setError("");
    setNote("");
    await api(`/api/offsite/content-assets/${id}/approve`, { method: "POST", body: JSON.stringify({ confirmed: true, note: "人工终审通过" }) });
    setNote("内容资产已人工批准，可以绑定到分发任务。");
    loadContent();
  }

  async function createAccount(e: FormEvent) {
    e.preventDefault();
    setError("");
    setNote("");
    await api("/api/offsite/accounts", { method: "POST", body: JSON.stringify(accountForm) });
    setAccountForm({ ...accountForm, label: "", login_identifier: "", vault_ref: "", notes: "" });
    setNote("平台账号已保存。系统只保存 vault_ref，不保存明文密码。");
    loadPlatforms();
  }

  async function createConnector(e: FormEvent) {
    e.preventDefault();
    setError("");
    setNote("");
    await api("/api/offsite/connectors", { method: "POST", body: JSON.stringify(connectorForm) });
    setConnectorForm({ ...connectorForm, provider_key: "", env_var: "", notes: "" });
    setNote("Connector 已登记。后续真实 API/OAuth 会接到这里。");
    loadPlatforms();
  }

  async function submitResult(job: DistJob) {
    const resultUrl = (resultForms[job.id] ?? job.result_url ?? "").trim();
    if (!resultUrl) {
      setError("请先填写 result_url，再记录 Placement 结果。");
      return;
    }
    setError("");
    setNote("");
    await api(`/api/distribution/jobs/${job.id}/submit-result`, {
      method: "POST",
      body: JSON.stringify({ result_url: resultUrl, verify_status: "pending", evidence: "人工提交 result_url，等待 Placement 核验。" }),
    });
    setNote("result_url 已记录，并已回写到原始站外机会。");
    loadGaps();
    loadDist();
  }

  async function loadGuide(jobId: string) {
    setError("");
    const guide = await api<DistGuide>(`/api/distribution/jobs/${jobId}/guide`);
    setGuides({ ...guides, [jobId]: guide });
  }

  async function checkPlacement(jobId: string) {
    setError("");
    setNote("");
    const checked = await api<PlacementCheck>(`/api/distribution/jobs/${jobId}/check-placement`, { method: "POST" });
    setPlacementChecks({ ...placementChecks, [jobId]: checked });
    setNote(checked.note);
    loadGaps();
    loadDist();
  }

  async function recordDistribution(id: string, confirmed: boolean) {
    setError("");
    setNote("");
    if (!confirmed) {
      await api(`/api/distribution/jobs/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: "draft" }),
      });
      setNote("已保存为草稿，没有触发外部分发。");
      loadDist();
      return;
    }
    try {
      const res = await api<{ sent: boolean; provider_status: string; detail: string }>(
        `/api/distribution/jobs/${id}/send`,
        { method: "POST", body: JSON.stringify({ confirmed }) }
      );
      if (!res.sent) setError(res.detail);
      else setNote(confirmed ? "已记录一次人工确认执行。" : "已记录为未发送的人工草稿。");
      loadDist();
    } catch (e) {
      setError(e instanceof Error ? e.message : "执行记录失败");
    }
  }

  const visibleGaps = filter === "all" ? gaps : gaps.filter((g) => g.verify_status === filter);

  return (
    <div className="space-y-6">
      <section className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div className="max-w-4xl">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="brand">Offsite Exposure</Badge>
              <Badge tone="amber">人工确认后执行</Badge>
            </div>
            <h1 className="mt-3 text-2xl font-semibold text-slate-950">站外曝光工作台</h1>
            <p className="mt-2 text-sm leading-6 text-slate-500">
              用一条清晰链路管理 B2B 站外增长：先记录第三方平台和竞品机会，再生成可人工执行的分发任务，最后核验 Placement 是否真实存在并复测效果。
              当前不会自动群发、不会冒充权重数据，所有外部发布都需要人工确认。
            </p>
          </div>
          <div className="grid w-full gap-2 sm:grid-cols-2 xl:w-[420px]">
            <StatTile label="机会池" value={stats.activeOpportunities} helper="待判断、跟进中或已有回复的曝光机会" />
            <StatTile label="有效 Placement" value={stats.validPlacements} helper="已核验存在的第三方提及或外链" />
          </div>
        </div>
      </section>

      <section className="grid gap-3 lg:grid-cols-6">
        <WorkflowStep icon={RadioTower} title="Source Platform" value={gaps.length} helper="第三方来源、竞品曝光和我方已获链接" />
        <WorkflowStep icon={ClipboardList} title="Opportunity" value={stats.activeOpportunities} helper="可跟进的曝光机会，先判断价值再行动" />
        <WorkflowStep icon={Bot} title="Content Asset" value={stats.approvedAssets} helper="已人工批准、可用于站外提交的内容资产" />
        <WorkflowStep icon={Send} title="Distribution Task" value={stats.openJobs} helper="待人工确认的内容分发或投稿任务" />
        <WorkflowStep icon={Link2} title="Placement" value={stats.validPlacements} helper="真实存在、可被客户复核的站外证据" />
        <WorkflowStep icon={RefreshCw} title="Platform / Account" value={platforms.length} helper="平台资源、账号和可接入 Connector" />
      </section>

      <div className="flex flex-wrap gap-2">
        <Button size="sm" variant={tab === "opportunities" ? "default" : "outline"} onClick={() => setTab("opportunities")}>
          机会池
        </Button>
        <Button size="sm" variant={tab === "distribution" ? "default" : "outline"} onClick={() => setTab("distribution")}>
          分发任务
        </Button>
        <Button size="sm" variant={tab === "placements" ? "default" : "outline"} onClick={() => setTab("placements")}>
          Placement 核验
        </Button>
        <Button size="sm" variant={tab === "content" ? "default" : "outline"} onClick={() => setTab("content")}>
          内容资产
        </Button>
        <Button size="sm" variant={tab === "platforms" ? "default" : "outline"} onClick={() => setTab("platforms")}>
          平台与账号
        </Button>
      </div>

      {tab === "opportunities" ? (
        <section className="grid gap-5 xl:grid-cols-[1fr_360px]">
          <div className="space-y-3">
            {gaps.length ? (
              gaps.map((g) => (
                <Card key={g.id} className="rounded-md">
                  <CardHeader className="flex flex-row items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <CardTitle>{g.title || g.referring_domain}</CardTitle>
                        <Badge tone={g.priority === "P0" || g.priority === "P1" ? "red" : g.priority === "P2" ? "amber" : "default"}>{g.priority}</Badge>
                        <Badge>{kindLabel[g.kind] ?? g.kind}</Badge>
                        <Badge tone={verifyTone[g.verify_status]}>{verifyLabel[g.verify_status] ?? g.verify_status}</Badge>
                      </div>
                      <p className="mt-1 text-sm text-slate-500">
                        {g.competitor_name && g.competitor_name !== "—" ? `关联竞品：${g.competitor_name}` : "我方站外记录"}
                      </p>
                      <p className="mt-1 break-all font-mono text-xs text-slate-400">{g.link_url || g.competitor_url || "未登记 URL"}</p>
                    </div>
                    <Badge tone="amber">{gapLabel[g.status] ?? g.status}</Badge>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {g.notes ? <p className="text-sm leading-6 text-slate-600">{g.notes}</p> : null}
                    <div className="grid gap-2 md:grid-cols-2">
                      <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                        <div className="text-xs font-medium text-slate-500">推荐动作</div>
                        <p className="mt-1 text-sm leading-5 text-slate-700">{g.recommended_action || "待补充：判断该平台是否值得提交、认领或监控。"}</p>
                      </div>
                      <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                        <div className="text-xs font-medium text-slate-500">验收标准</div>
                        <p className="mt-1 text-sm leading-5 text-slate-700">{g.acceptance_criteria || "记录 result_url，并完成 Placement 核验。"}</p>
                      </div>
                      <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                        <div className="text-xs font-medium text-slate-500">负责人</div>
                        <p className="mt-1 text-sm leading-5 text-slate-700">{g.owner_hint || "未指定"}</p>
                      </div>
                      <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                        <div className="text-xs font-medium text-slate-500">复测方式</div>
                        <p className="mt-1 text-sm leading-5 text-slate-700">{g.retest_method || "复查 result_url 是否可访问、是否提及客户、是否链接到目标页。"}</p>
                      </div>
                    </div>
                    {g.result_url ? (
                      <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm">
                        <div className="font-medium text-emerald-900">Result URL</div>
                        <a className="mt-1 block break-all text-emerald-800 underline" href={g.result_url} target="_blank" rel="noreferrer">
                          {g.result_url}
                        </a>
                        {g.retest_result ? <p className="mt-2 text-emerald-800">{g.retest_result}</p> : null}
                      </div>
                    ) : null}
                    {g.evidence ? <pre className="whitespace-pre-wrap rounded-md bg-slate-50 p-3 text-xs leading-5 text-slate-600">{g.evidence}</pre> : null}
                    {g.ai_review ? <p className="rounded-md bg-brand-50 p-3 text-sm leading-6 text-brand-900">{g.ai_review}</p> : null}
                    <div className="flex flex-wrap items-center gap-2">
                      <Input
                        className="max-w-xs"
                        placeholder="联系人、平台账号或跟进对象"
                        value={contact}
                        onChange={(e) => setContact(e.target.value)}
                      />
                      <Button size="sm" onClick={() => aiGap(g.id)}>
                        <Bot className="mr-1.5 h-4 w-4" />
                        AI 判断价值
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => addOutreach(g.id)}>
                        添加跟进
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => prepareJobFromGap(g)}>
                        创建分发任务
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => updateGap(g.id, { status: "needs_retest" })}>
                        标记待复测
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => updateGap(g.id, { status: "closed" })}>
                        关闭
                      </Button>
                      {g.link_url ? (
                        <a className="inline-flex items-center gap-1 text-sm font-medium text-brand-700" href={g.link_url} target="_blank" rel="noreferrer">
                          打开页面 <ExternalLink className="h-3.5 w-3.5" />
                        </a>
                      ) : null}
                    </div>
                    {g.outreach.length ? (
                      <div className="space-y-1 rounded-md border border-slate-200 bg-slate-50 p-3 text-sm">
                        {g.outreach.map((o) => (
                          <div key={o.id} className="flex flex-wrap justify-between gap-2">
                            <span>{o.contact}</span>
                            <span className="text-slate-500">{o.channel} · {o.status === "todo" ? "待跟进" : o.status === "sent_manual" ? "已人工发送" : o.status}</span>
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </CardContent>
                </Card>
              ))
            ) : (
              <p className="rounded-md border border-dashed border-slate-300 bg-white px-4 py-6 text-sm text-slate-500">
                还没有站外机会。可以先登记竞品出现的平台、行业目录、媒体提及、协会页面、测评文章或客户案例页面。
              </p>
            )}
          </div>

          <Card className="h-fit rounded-md">
            <CardHeader>
              <CardTitle>登记站外机会</CardTitle>
            </CardHeader>
            <CardContent>
              <form className="space-y-3" onSubmit={addGap}>
                <Input
                  placeholder="机会标题，例如：ThomasNet 供应商档案缺席"
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                />
                <div className="grid gap-2 sm:grid-cols-2">
                  <select
                    className="h-10 w-full rounded-md border border-slate-200 px-3 text-sm"
                    value={form.issue_type}
                    onChange={(e) => setForm({ ...form, issue_type: e.target.value })}
                  >
                    <option value="competitor_gap">竞品有我无</option>
                    <option value="unlinked_mention">未链接提及</option>
                    <option value="lost_link">已获链接失效</option>
                    <option value="authority_source">权威第三方源缺失</option>
                    <option value="monitor_only">仅监控</option>
                  </select>
                  <select
                    className="h-10 w-full rounded-md border border-slate-200 px-3 text-sm"
                    value={form.priority}
                    onChange={(e) => setForm({ ...form, priority: e.target.value })}
                  >
                    <option value="P1">P1 高优先级</option>
                    <option value="P2">P2 常规机会</option>
                    <option value="P3">P3 观察</option>
                    <option value="P0">P0 立即处理</option>
                  </select>
                </div>
                <select
                  className="h-10 w-full rounded-md border border-slate-200 px-3 text-sm"
                  value={form.kind}
                  onChange={(e) => setForm({ ...form, kind: e.target.value })}
                >
                  <option value="competitor">竞品曝光机会</option>
                  <option value="inbound">我方已获曝光</option>
                </select>
                <Input
                  placeholder="来源域名，例如 industrytoday.com"
                  value={form.referring_domain}
                  onChange={(e) => setForm({ ...form, referring_domain: e.target.value })}
                  required
                />
                <Input
                  placeholder="第三方页面 URL"
                  value={form.link_url}
                  onChange={(e) => setForm({ ...form, link_url: e.target.value })}
                />
                <Input
                  placeholder="关联竞品（可选）"
                  value={form.competitor_name}
                  onChange={(e) => setForm({ ...form, competitor_name: e.target.value })}
                />
                <Input
                  placeholder="负责人，例如：站外执行 / 客户经理"
                  value={form.owner_hint}
                  onChange={(e) => setForm({ ...form, owner_hint: e.target.value })}
                />
                <Input
                  placeholder="推荐动作，例如：提交供应商资料并补官网链接"
                  value={form.recommended_action}
                  onChange={(e) => setForm({ ...form, recommended_action: e.target.value })}
                />
                <Input
                  placeholder="验收标准，例如：资料页上线并记录 result_url"
                  value={form.acceptance_criteria}
                  onChange={(e) => setForm({ ...form, acceptance_criteria: e.target.value })}
                />
                <Input
                  placeholder="复测方式，例如：检查页面可访问、链接属性和品牌提及"
                  value={form.retest_method}
                  onChange={(e) => setForm({ ...form, retest_method: e.target.value })}
                />
                <Input placeholder="价值判断或备注" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
                <Button type="submit" className="w-full">加入机会池</Button>
              </form>
            </CardContent>
          </Card>
        </section>
      ) : null}

      {tab === "distribution" ? (
        <section className="grid gap-5 xl:grid-cols-[1fr_380px]">
          <div className="space-y-3">
            <div className="grid gap-3 md:grid-cols-3">
              {providers.map((p) => (
                <div key={p.key} className="rounded-md border border-slate-200 bg-white p-4">
                  <div className="flex items-center justify-between gap-2">
                    <div className="font-medium text-slate-950">{p.label}</div>
                    <Badge tone={p.configured ? "green" : "amber"}>{p.status}</Badge>
                  </div>
                  <p className="mt-2 text-xs leading-5 text-slate-500">配置项：{p.env_var}</p>
                </div>
              ))}
            </div>
            {jobs.length ? (
              jobs.map((j) => (
                <Card key={j.id} className="rounded-md">
                  <CardContent className="p-4">
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <div className="font-semibold text-slate-950">{j.title}</div>
                          <Badge tone={j.status === "sent" ? "green" : j.status === "failed" ? "red" : "amber"}>
                            {jobStatusLabel[j.status] ?? j.status}
                          </Badge>
                          <Badge>{taskTypeLabel[j.task_type] ?? j.task_type}</Badge>
                          {j.gap_id ? <Badge tone="blue">已绑定机会</Badge> : null}
                        </div>
                        <p className="mt-1 break-all font-mono text-xs text-slate-400">{j.target_url}</p>
                        <p className="mt-2 text-sm leading-6 text-slate-600">{j.payload_summary || "未填写内容摘要"}</p>
                        <div className="mt-2 grid gap-2 text-xs text-slate-500 md:grid-cols-3">
                          <span>负责人：{j.owner_hint || "未指定"}</span>
                          <span>核验：{j.verify_status || "pending"}</span>
                          <span>渠道：{j.provider_key}</span>
                        </div>
                        {j.result_url ? (
                          <a className="mt-2 block break-all text-sm font-medium text-brand-700 underline" href={j.result_url} target="_blank" rel="noreferrer">
                            {j.result_url}
                          </a>
                        ) : null}
                        {j.last_detail ? <p className="mt-2 text-xs leading-5 text-slate-500">{j.last_detail}</p> : null}
                        {guides[j.id] ? (
                          <div className="mt-3 grid gap-2 text-sm md:grid-cols-2">
                            <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                              <div className="font-medium text-slate-900">执行材料</div>
                              <ul className="mt-2 space-y-1 text-xs leading-5 text-slate-600">
                                {guides[j.id].materials.map((item) => <li key={item}>- {item}</li>)}
                              </ul>
                            </div>
                            <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                              <div className="font-medium text-slate-900">人工执行清单</div>
                              <ul className="mt-2 space-y-1 text-xs leading-5 text-slate-600">
                                {guides[j.id].checklist.map((item) => <li key={item}>- {item}</li>)}
                              </ul>
                            </div>
                            <div className="rounded-md border border-amber-200 bg-amber-50 p-3 md:col-span-2">
                              <div className="font-medium text-amber-900">边界提醒</div>
                              <ul className="mt-2 space-y-1 text-xs leading-5 text-amber-800">
                                {guides[j.id].risk_notes.map((item) => <li key={item}>- {item}</li>)}
                              </ul>
                            </div>
                          </div>
                        ) : null}
                        {placementChecks[j.id] ? (
                          <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-4">
                            <span className="rounded-md bg-slate-50 px-3 py-2">HTTP：{placementChecks[j.id].http_status ?? "未返回"}</span>
                            <span className="rounded-md bg-slate-50 px-3 py-2">可访问：{placementChecks[j.id].is_live ? "是" : "否"}</span>
                            <span className="rounded-md bg-slate-50 px-3 py-2">目标链接：{placementChecks[j.id].target_link_found ? "发现" : "未确认"}</span>
                            <span className="rounded-md bg-slate-50 px-3 py-2">rel：{placementChecks[j.id].link_attr}</span>
                          </div>
                        ) : null}
                      </div>
                      <div className="flex shrink-0 flex-wrap gap-2 lg:max-w-xs">
                        <Input
                          className="h-9 min-w-[220px]"
                          placeholder="result_url"
                          value={resultForms[j.id] ?? j.result_url ?? ""}
                          onChange={(e) => setResultForms({ ...resultForms, [j.id]: e.target.value })}
                        />
                        <Button size="sm" variant="outline" onClick={() => submitResult(j)}>
                          记录结果 URL
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => loadGuide(j.id)}>
                          执行指南
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => checkPlacement(j.id)}>
                          核验 URL
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => recordDistribution(j.id, false)}>
                          仅保存草稿
                        </Button>
                        <Button size="sm" onClick={() => recordDistribution(j.id, true)}>
                          人工确认执行
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            ) : (
              <p className="rounded-md border border-dashed border-slate-300 bg-white px-4 py-6 text-sm text-slate-500">
                还没有分发任务。先把可发布的案例、新闻稿、行业问答或目录资料加入队列，再由人工确认发布。
              </p>
            )}
          </div>

          <Card className="h-fit rounded-md">
            <CardHeader>
              <CardTitle>新建分发任务</CardTitle>
            </CardHeader>
            <CardContent>
              <form className="space-y-3" onSubmit={createJob}>
                <select
                  className="h-10 w-full rounded-md border border-slate-200 px-3 text-sm"
                  value={distForm.gap_id}
                  onChange={(e) => {
                    const gap = gaps.find((item) => item.id === e.target.value);
                    setDistForm({
                      ...distForm,
                      gap_id: e.target.value,
                      title: gap ? gap.title || `${gap.referring_domain} 站外曝光执行` : distForm.title,
                      payload_summary: gap ? gap.recommended_action || gap.notes || distForm.payload_summary : distForm.payload_summary,
                      owner_hint: gap ? gap.owner_hint || distForm.owner_hint : distForm.owner_hint,
                    });
                  }}
                >
                  <option value="">不绑定机会，手工任务</option>
                  {gaps.map((g) => (
                    <option key={g.id} value={g.id}>
                      {g.priority} · {g.title || g.referring_domain}
                    </option>
                  ))}
                </select>
                <select
                  className="h-10 w-full rounded-md border border-slate-200 px-3 text-sm"
                  value={distForm.platform_id}
                  onChange={(e) => setDistForm({ ...distForm, platform_id: e.target.value, account_id: "" })}
                >
                  <option value="">不绑定平台</option>
                  {platforms.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} · {p.submission_mode}
                    </option>
                  ))}
                </select>
                <select
                  className="h-10 w-full rounded-md border border-slate-200 px-3 text-sm"
                  value={distForm.account_id}
                  onChange={(e) => setDistForm({ ...distForm, account_id: e.target.value })}
                >
                  <option value="">不绑定账号</option>
                  {accounts
                    .filter((a) => !distForm.platform_id || a.platform_id === distForm.platform_id)
                    .map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.label} · {a.status}
                      </option>
                    ))}
                </select>
                <select
                  className="h-10 w-full rounded-md border border-slate-200 px-3 text-sm"
                  value={distForm.content_asset_id}
                  onChange={(e) => {
                    const asset = assets.find((item) => item.id === e.target.value);
                    setDistForm({
                      ...distForm,
                      content_asset_id: e.target.value,
                      payload_summary: asset ? asset.body_md : distForm.payload_summary,
                    });
                  }}
                >
                  <option value="">不绑定内容资产</option>
                  {assets
                    .filter((asset) => asset.status === "human_approved")
                    .map((asset) => (
                      <option key={asset.id} value={asset.id}>
                        {asset.title} · {asset.asset_type}
                      </option>
                    ))}
                </select>
                <Input
                  placeholder="任务标题，例如：提交到行业目录"
                  value={distForm.title}
                  onChange={(e) => setDistForm({ ...distForm, title: e.target.value })}
                  required
                />
                <Input
                  placeholder="要推广的客户 URL"
                  value={distForm.target_url}
                  onChange={(e) => setDistForm({ ...distForm, target_url: e.target.value })}
                />
                <select
                  className="h-10 w-full rounded-md border border-slate-200 px-3 text-sm"
                  value={distForm.provider_key}
                  onChange={(e) => setDistForm({ ...distForm, provider_key: e.target.value })}
                >
                  {providers.map((p) => (
                    <option key={p.key} value={p.key}>
                      {p.label}
                    </option>
                  ))}
                </select>
                <select
                  className="h-10 w-full rounded-md border border-slate-200 px-3 text-sm"
                  value={distForm.task_type}
                  onChange={(e) => setDistForm({ ...distForm, task_type: e.target.value })}
                >
                  {Object.entries(taskTypeLabel).map(([key, label]) => (
                    <option key={key} value={key}>
                      {label}
                    </option>
                  ))}
                </select>
                <Input
                  placeholder="负责人，例如：站外执行"
                  value={distForm.owner_hint}
                  onChange={(e) => setDistForm({ ...distForm, owner_hint: e.target.value })}
                />
                <Input
                  placeholder="内容摘要、提交口径或人工注意事项"
                  value={distForm.payload_summary}
                  onChange={(e) => setDistForm({ ...distForm, payload_summary: e.target.value })}
                />
                <Input
                  placeholder="已有结果 URL，可稍后补"
                  value={distForm.result_url}
                  onChange={(e) => setDistForm({ ...distForm, result_url: e.target.value })}
                />
                <Button type="submit" className="w-full">加入分发队列</Button>
              </form>
            </CardContent>
          </Card>
        </section>
      ) : null}

      {tab === "placements" ? (
        <section className="space-y-4">
          <div className="grid gap-3 md:grid-cols-4">
            {(["unverified", "valid", "dead", "spam"] as const).map((s) => (
              <button key={s} type="button" className="text-left" onClick={() => setFilter(filter === s ? "all" : s)}>
                <Card className={filter === s ? "rounded-md border-brand-600" : "rounded-md"}>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-sm">
                      {s === "valid" ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <ShieldCheck className="h-4 w-4 text-slate-400" />}
                      {verifyLabel[s]}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="text-2xl font-semibold">
                    {gaps.filter((g) => g.verify_status === s).length}
                  </CardContent>
                </Card>
              </button>
            ))}
          </div>
          <div className="space-y-3">
            {visibleGaps.map((g) => (
              <div key={g.id} className="rounded-md border border-slate-200 bg-white p-4">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <div className="font-semibold text-slate-950">{g.referring_domain}</div>
                      <Badge tone={verifyTone[g.verify_status]}>{verifyLabel[g.verify_status] ?? g.verify_status}</Badge>
                    </div>
                    <p className="mt-1 break-all font-mono text-xs text-slate-400">{g.link_url || g.competitor_url || "未登记 URL"}</p>
                    <p className="mt-2 text-sm text-slate-500">{g.notes || "暂无备注"}</p>
                  </div>
                  <div className="flex shrink-0 flex-wrap gap-1">
                    {(["unverified", "valid", "dead", "spam"] as const).map((s) => (
                      <Button key={s} size="sm" variant="outline" onClick={() => setVerify(g.id, s)}>
                        {verifyLabel[s]}
                      </Button>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {tab === "content" ? (
        <section className="grid gap-5 xl:grid-cols-[1fr_420px]">
          <div className="space-y-4">
            <Card className="rounded-md">
              <CardHeader>
                <CardTitle>Fact Pack</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {factPacks.length ? factPacks.map((fact) => (
                  <div key={fact.id} className="rounded-md border border-slate-200 p-4">
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="font-semibold text-slate-950">{fact.name}</h3>
                          <Badge tone={fact.status === "approved" ? "green" : "amber"}>{fact.status === "approved" ? "已批准" : "草稿"}</Badge>
                        </div>
                        <p className="mt-1 text-sm text-slate-500">{fact.legal_name || "未填写公司英文名"} · {fact.website || "未填写官网"}</p>
                        <p className="mt-2 text-sm leading-6 text-slate-600">{fact.approved_boilerplate_en || "还没有标准英文简介。"}</p>
                        <div className="mt-2 grid gap-2 text-xs text-slate-500 md:grid-cols-2">
                          <span>品牌：{fact.brand_names || "未填"}</span>
                          <span>品类：{fact.product_categories_en || "未填"}</span>
                          <span>认证：{fact.certifications || "未填"}</span>
                          <span>禁用语：{fact.banned_claims || "未填"}</span>
                        </div>
                      </div>
                      <Button size="sm" variant="outline" onClick={() => approveFactPack(fact.id)} disabled={fact.status === "approved"}>
                        批准事实包
                      </Button>
                    </div>
                  </div>
                )) : <p className="text-sm text-slate-500">还没有 Fact Pack。先让客户确认事实源，再生成对外内容。</p>}
              </CardContent>
            </Card>

            <Card className="rounded-md">
              <CardHeader>
                <CardTitle>Content Asset</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {assets.length ? assets.map((asset) => (
                  <div key={asset.id} className="rounded-md border border-slate-200 p-4">
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="font-semibold text-slate-950">{asset.title}</h3>
                          <Badge>{asset.asset_type}</Badge>
                          <Badge tone={asset.status === "human_approved" ? "green" : asset.ai_review_status === "fail" ? "red" : "amber"}>
                            {asset.status === "human_approved" ? "人工已批准" : asset.ai_review_status === "fail" ? "初审未过" : asset.status}
                          </Badge>
                        </div>
                        <p className="mt-1 text-xs text-slate-500">{asset.fact_pack_name || "未绑定 Fact Pack"} · {asset.locale} · v{asset.version}</p>
                        <p className="mt-3 whitespace-pre-wrap rounded-md bg-slate-50 p-3 text-sm leading-6 text-slate-700">{asset.body_md}</p>
                        {asset.ai_review ? <p className="mt-2 whitespace-pre-wrap text-xs leading-5 text-slate-500">{asset.ai_review}</p> : null}
                      </div>
                      <div className="flex shrink-0 flex-wrap gap-2 lg:w-40">
                        <Button size="sm" variant="outline" onClick={() => reviewAsset(asset.id)}>AI 初审</Button>
                        <Button size="sm" onClick={() => approveAsset(asset.id)} disabled={asset.status === "human_approved"}>人工批准</Button>
                      </div>
                    </div>
                  </div>
                )) : <p className="text-sm text-slate-500">还没有内容资产。可以手工粘贴，也可以基于已批准 Fact Pack 生成草稿。</p>}
              </CardContent>
            </Card>
          </div>

          <div className="space-y-4">
            <Card className="rounded-md">
              <CardHeader><CardTitle>新增 Fact Pack</CardTitle></CardHeader>
              <CardContent>
                <form className="space-y-3" onSubmit={saveFactPack}>
                  <Input placeholder="事实包名称" value={factForm.name} onChange={(e) => setFactForm({ ...factForm, name: e.target.value })} />
                  <Input placeholder="公司英文全称" value={factForm.legal_name} onChange={(e) => setFactForm({ ...factForm, legal_name: e.target.value })} />
                  <Input placeholder="品牌名，多个用逗号" value={factForm.brand_names} onChange={(e) => setFactForm({ ...factForm, brand_names: e.target.value })} />
                  <Input placeholder="官网" value={factForm.website} onChange={(e) => setFactForm({ ...factForm, website: e.target.value })} />
                  <Input placeholder="英文品类词" value={factForm.product_categories_en} onChange={(e) => setFactForm({ ...factForm, product_categories_en: e.target.value })} />
                  <Input placeholder="认证/资质，仅填已确认" value={factForm.certifications} onChange={(e) => setFactForm({ ...factForm, certifications: e.target.value })} />
                  <Input placeholder="公开参数/规格" value={factForm.key_specs} onChange={(e) => setFactForm({ ...factForm, key_specs: e.target.value })} />
                  <Input placeholder="禁用宣传语，例如 world leader" value={factForm.banned_claims} onChange={(e) => setFactForm({ ...factForm, banned_claims: e.target.value })} />
                  <Input placeholder="公开联系方式" value={factForm.contact_public} onChange={(e) => setFactForm({ ...factForm, contact_public: e.target.value })} />
                  <textarea className="min-h-24 w-full rounded-md border border-slate-200 px-3 py-2 text-sm" placeholder="客户批准的标准英文简介" value={factForm.approved_boilerplate_en} onChange={(e) => setFactForm({ ...factForm, approved_boilerplate_en: e.target.value })} />
                  <Button type="submit" className="w-full">保存 Fact Pack</Button>
                </form>
              </CardContent>
            </Card>

            <Card className="rounded-md">
              <CardHeader><CardTitle>新增内容资产</CardTitle></CardHeader>
              <CardContent>
                <form className="space-y-3" onSubmit={saveAsset}>
                  <select className="h-10 w-full rounded-md border border-slate-200 px-3 text-sm" value={assetForm.fact_pack_id} onChange={(e) => setAssetForm({ ...assetForm, fact_pack_id: e.target.value })}>
                    <option value="">选择 Fact Pack</option>
                    {factPacks.map((fact) => <option key={fact.id} value={fact.id}>{fact.name} · {fact.status}</option>)}
                  </select>
                  <select className="h-10 w-full rounded-md border border-slate-200 px-3 text-sm" value={assetForm.asset_type} onChange={(e) => setAssetForm({ ...assetForm, asset_type: e.target.value })}>
                    <option value="company_blurb">公司简介</option>
                    <option value="profile_fields">平台档案字段</option>
                    <option value="product_spec">产品/规格</option>
                    <option value="faq">FAQ</option>
                    <option value="listicle_pitch">榜单 Pitch</option>
                    <option value="pr_draft">PR 草稿</option>
                  </select>
                  <Input placeholder="标题" value={assetForm.title} onChange={(e) => setAssetForm({ ...assetForm, title: e.target.value })} required />
                  <textarea className="min-h-32 w-full rounded-md border border-slate-200 px-3 py-2 text-sm" placeholder="正文，手工粘贴或点击下方生成草稿" value={assetForm.body_md} onChange={(e) => setAssetForm({ ...assetForm, body_md: e.target.value })} />
                  <Input placeholder="关键词" value={assetForm.keywords} onChange={(e) => setAssetForm({ ...assetForm, keywords: e.target.value })} />
                  <div className="grid gap-2 sm:grid-cols-2">
                    <Button type="button" variant="outline" onClick={generateAsset}>从 Fact Pack 生成草稿</Button>
                    <Button type="submit">保存内容资产</Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </div>
        </section>
      ) : null}

      {tab === "platforms" ? (
        <section className="grid gap-5 xl:grid-cols-[1fr_420px]">
          <div className="space-y-4">
            <div className="rounded-md border border-slate-200 bg-white p-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <h2 className="font-semibold text-slate-950">B2B 平台资源库</h2>
                  <p className="mt-1 text-sm leading-6 text-slate-500">
                    先导入常用出口 B2B 站外源，再按客户行业补充垂直目录、协会、分销商和媒体。导入不会覆盖已有平台。
                  </p>
                </div>
                <Button type="button" onClick={seedPlatforms}>导入 B2B 常用平台</Button>
              </div>
            </div>
            <div className="grid gap-3 lg:grid-cols-2">
              {platforms.map((p) => (
                <Card key={p.id} className="rounded-md">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="font-semibold text-slate-950">{p.name}</div>
                        <p className="mt-1 text-xs text-slate-500">{p.domain || p.base_url || p.platform_key}</p>
                      </div>
                      <Badge tone={p.status === "active" ? "green" : "default"}>{p.status}</Badge>
                    </div>
                    <div className="mt-3 grid gap-2 text-xs text-slate-500 sm:grid-cols-2">
                      <span>类型：{p.source_type}</span>
                      <span>提交：{p.submission_mode}</span>
                      <span>账号：{p.accounts_count}</span>
                      <span>Connector：{p.connectors_count}</span>
                      <span>区域：{p.regions || "未填"}</span>
                      <span>风险：{p.risk_level}</span>
                    </div>
                    {p.notes ? <p className="mt-3 text-sm leading-6 text-slate-600">{p.notes}</p> : null}
                  </CardContent>
                </Card>
              ))}
            </div>

            <Card className="rounded-md">
              <CardHeader><CardTitle>平台账号</CardTitle></CardHeader>
              <CardContent className="space-y-2">
                {accounts.length ? accounts.map((a) => (
                  <div key={a.id} className="rounded-md border border-slate-200 p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="font-medium text-slate-900">{a.label}</div>
                      <Badge tone={a.status === "active" ? "green" : "amber"}>{a.status}</Badge>
                    </div>
                    <p className="mt-1 text-xs text-slate-500">{a.platform_name} · {a.scope} · {a.auth_method}</p>
                    <p className="mt-1 text-xs text-slate-500">vault_ref：{a.vault_ref || "未填，业务库不存明文密码"}</p>
                  </div>
                )) : <p className="text-sm text-slate-500">还没有平台账号。</p>}
              </CardContent>
            </Card>

            <Card className="rounded-md">
              <CardHeader><CardTitle>Connector 能力</CardTitle></CardHeader>
              <CardContent className="space-y-2">
                {connectors.length ? connectors.map((c) => (
                  <div key={c.id} className="rounded-md border border-slate-200 p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="font-medium text-slate-900">{c.provider_key}</div>
                      <Badge tone={c.status === "configured" ? "green" : "amber"}>{c.status}</Badge>
                    </div>
                    <p className="mt-1 text-xs text-slate-500">{c.platform_name} · {c.auth_mode} · {c.capabilities}</p>
                    <p className="mt-1 text-xs text-slate-500">env：{c.env_var || "无"}</p>
                  </div>
                )) : <p className="text-sm text-slate-500">还没有 Connector。没有官方 API 的平台保持 manual_only。</p>}
              </CardContent>
            </Card>
          </div>

          <div className="space-y-4">
            <Card className="rounded-md">
              <CardHeader><CardTitle>新增平台</CardTitle></CardHeader>
              <CardContent>
                <form className="space-y-3" onSubmit={createPlatform}>
                  <Input placeholder="平台 key，例如 thomasnet" value={platformForm.platform_key} onChange={(e) => setPlatformForm({ ...platformForm, platform_key: e.target.value })} required />
                  <Input placeholder="平台名称" value={platformForm.name} onChange={(e) => setPlatformForm({ ...platformForm, name: e.target.value })} required />
                  <Input placeholder="域名" value={platformForm.domain} onChange={(e) => setPlatformForm({ ...platformForm, domain: e.target.value })} />
                  <Input placeholder="Base URL" value={platformForm.base_url} onChange={(e) => setPlatformForm({ ...platformForm, base_url: e.target.value })} />
                  <div className="grid gap-2 sm:grid-cols-2">
                    <select className="h-10 rounded-md border border-slate-200 px-3 text-sm" value={platformForm.source_type} onChange={(e) => setPlatformForm({ ...platformForm, source_type: e.target.value })}>
                      <option value="directory">行业目录</option>
                      <option value="marketplace">B2B 平台</option>
                      <option value="media">媒体</option>
                      <option value="association">协会</option>
                      <option value="listicle">榜单/测评</option>
                      <option value="distributor">分销商</option>
                    </select>
                    <select className="h-10 rounded-md border border-slate-200 px-3 text-sm" value={platformForm.submission_mode} onChange={(e) => setPlatformForm({ ...platformForm, submission_mode: e.target.value })}>
                      <option value="manual_login">人工登录</option>
                      <option value="form_public">公开表单</option>
                      <option value="email_outreach">邮件联系</option>
                      <option value="paid_placement">付费位</option>
                      <option value="api_none">仅监控</option>
                    </select>
                  </div>
                  <Input placeholder="国家/区域，例如 US, EU" value={platformForm.regions} onChange={(e) => setPlatformForm({ ...platformForm, regions: e.target.value })} />
                  <Input placeholder="行业标签" value={platformForm.industry_tags} onChange={(e) => setPlatformForm({ ...platformForm, industry_tags: e.target.value })} />
                  <Input placeholder="备注/提交规则" value={platformForm.notes} onChange={(e) => setPlatformForm({ ...platformForm, notes: e.target.value })} />
                  <Button type="submit" className="w-full">保存平台</Button>
                </form>
              </CardContent>
            </Card>

            <Card className="rounded-md">
              <CardHeader><CardTitle>新增账号</CardTitle></CardHeader>
              <CardContent>
                <form className="space-y-3" onSubmit={createAccount}>
                  <select className="h-10 w-full rounded-md border border-slate-200 px-3 text-sm" value={accountForm.platform_id} onChange={(e) => setAccountForm({ ...accountForm, platform_id: e.target.value })} required>
                    <option value="">选择平台</option>
                    {platforms.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                  <Input placeholder="账号标签" value={accountForm.label} onChange={(e) => setAccountForm({ ...accountForm, label: e.target.value })} required />
                  <Input placeholder="登录名/邮箱（非密码）" value={accountForm.login_identifier} onChange={(e) => setAccountForm({ ...accountForm, login_identifier: e.target.value })} />
                  <Input placeholder="vault_ref，不填密码明文" value={accountForm.vault_ref} onChange={(e) => setAccountForm({ ...accountForm, vault_ref: e.target.value })} />
                  <div className="grid gap-2 sm:grid-cols-2">
                    <select className="h-10 rounded-md border border-slate-200 px-3 text-sm" value={accountForm.auth_method} onChange={(e) => setAccountForm({ ...accountForm, auth_method: e.target.value })}>
                      <option value="manual_only">人工登录</option>
                      <option value="password_vault">密码库</option>
                      <option value="oauth">OAuth</option>
                      <option value="api_key_vault">API Key 引用</option>
                      <option value="sso">SSO</option>
                    </select>
                    <select className="h-10 rounded-md border border-slate-200 px-3 text-sm" value={accountForm.scope} onChange={(e) => setAccountForm({ ...accountForm, scope: e.target.value })}>
                      <option value="shared">团队共用</option>
                      <option value="customer_exclusive">客户专属</option>
                    </select>
                  </div>
                  <Input placeholder="负责人" value={accountForm.owner_hint} onChange={(e) => setAccountForm({ ...accountForm, owner_hint: e.target.value })} />
                  <Button type="submit" className="w-full">保存账号</Button>
                </form>
              </CardContent>
            </Card>

            <Card className="rounded-md">
              <CardHeader><CardTitle>新增 Connector</CardTitle></CardHeader>
              <CardContent>
                <form className="space-y-3" onSubmit={createConnector}>
                  <select className="h-10 w-full rounded-md border border-slate-200 px-3 text-sm" value={connectorForm.platform_id} onChange={(e) => setConnectorForm({ ...connectorForm, platform_id: e.target.value })} required>
                    <option value="">选择平台</option>
                    {platforms.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                  <Input placeholder="provider_key，例如 wordpress / gmail / manual_browser" value={connectorForm.provider_key} onChange={(e) => setConnectorForm({ ...connectorForm, provider_key: e.target.value })} required />
                  <Input placeholder="能力，例如 draft_only,publish,sync_status" value={connectorForm.capabilities} onChange={(e) => setConnectorForm({ ...connectorForm, capabilities: e.target.value })} />
                  <Input placeholder="环境变量名（可选）" value={connectorForm.env_var} onChange={(e) => setConnectorForm({ ...connectorForm, env_var: e.target.value })} />
                  <Input placeholder="备注" value={connectorForm.notes} onChange={(e) => setConnectorForm({ ...connectorForm, notes: e.target.value })} />
                  <Button type="submit" className="w-full">保存 Connector</Button>
                </form>
              </CardContent>
            </Card>
          </div>
        </section>
      ) : null}

      {note ? <p className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{note}</p> : null}
      {error ? <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
    </div>
  );
}
