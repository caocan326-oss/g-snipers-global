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
import { api, type AiAssist, type BacklinkGap, type DistJob, type DistProvider } from "@/lib/api";

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

type Tab = "opportunities" | "distribution" | "placements";

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
    title: "",
    target_url: "/",
    provider_key: "directory",
    task_type: "profile_create",
    payload_summary: "",
    owner_hint: "",
    result_url: "",
  });
  const [resultForms, setResultForms] = useState<Record<string, string>>({});

  const stats = useMemo(() => {
    const activeOpportunities = gaps.filter((g) => !["won", "closed", "ignored", "skipped"].includes(g.status)).length;
    const validPlacements = gaps.filter((g) => g.verify_status === "valid").length;
    const needsReview = gaps.filter((g) => g.verify_status === "unverified").length;
    const openJobs = jobs.filter((j) => !["sent", "done"].includes(j.status)).length;
    return { activeOpportunities, validPlacements, needsReview, openJobs };
  }, [gaps, jobs]);

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

  useEffect(() => {
    const queryTab = typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("tab") : "";
    if (queryTab === "dist") setTab("distribution");
    loadGaps();
    loadDist();
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
    setDistForm({ ...distForm, gap_id: "", title: "", payload_summary: "", result_url: "" });
    setNote("分发任务已创建，等待人工确认执行。");
    loadGaps();
    loadDist();
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

      <section className="grid gap-3 lg:grid-cols-5">
        <WorkflowStep icon={RadioTower} title="Source Platform" value={gaps.length} helper="第三方来源、竞品曝光和我方已获链接" />
        <WorkflowStep icon={ClipboardList} title="Opportunity" value={stats.activeOpportunities} helper="可跟进的曝光机会，先判断价值再行动" />
        <WorkflowStep icon={Send} title="Distribution Task" value={stats.openJobs} helper="待人工确认的内容分发或投稿任务" />
        <WorkflowStep icon={Link2} title="Placement" value={stats.validPlacements} helper="真实存在、可被客户复核的站外证据" />
        <WorkflowStep icon={RefreshCw} title="Retest" value={stats.needsReview} helper="待复测或待核验的站外记录" />
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

      {note ? <p className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{note}</p> : null}
      {error ? <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
    </div>
  );
}
