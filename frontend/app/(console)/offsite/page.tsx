"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
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
  type OffsiteOpportunityGeneration,
  type PlacementCheck,
  type PlatformAccount,
  type PlatformConnector,
  type SourcePlatform,
  type SourcePlatformSeed,
} from "@/lib/api";

import { ChannelCards } from "./_components/ChannelCards";
import { ContentTab } from "./_components/ContentTab";
import { DistributionTab } from "./_components/DistributionTab";
import { OpportunitiesTab } from "./_components/OpportunitiesTab";
import { PlacementsTab } from "./_components/PlacementsTab";
import { PlatformsTab } from "./_components/PlatformsTab";
import { SummaryHeader } from "./_components/SummaryHeader";
import { TabNav } from "./_components/TabNav";
import type { Tab } from "./_helpers";

export default function OffsitePage() {
  const [tab, setTab] = useState<Tab>("channels");
  const [writingId, setWritingId] = useState("");
  const [filter, setFilter] = useState<"all" | "unverified" | "valid" | "dead" | "spam">("all");
  const [platformQuery, setPlatformQuery] = useState("");
  const [platformTypeFilter, setPlatformTypeFilter] = useState("all");
  const [platformRiskFilter, setPlatformRiskFilter] = useState("all");
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
  const [seedBusy, setSeedBusy] = useState(false);
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
  const [generatingOpportunities, setGeneratingOpportunities] = useState(false);

  const stats = useMemo(() => {
    const activeOpportunities = gaps.filter((g) => !["won", "closed", "ignored", "skipped"].includes(g.status)).length;
    const validPlacements = gaps.filter((g) => g.verify_status === "valid").length;
    const needsReview = gaps.filter((g) => g.verify_status === "unverified").length;
    const openJobs = jobs.filter((j) => !["sent", "done"].includes(j.status)).length;
    const approvedAssets = assets.filter((a) => a.status === "human_approved").length;
    return { activeOpportunities, validPlacements, needsReview, openJobs, approvedAssets };
  }, [gaps, jobs, assets]);

  const platformStats = useMemo(() => {
    const active = platforms.filter((p) => p.status === "active").length;
    const manual = platforms.filter((p) => p.submission_mode === "manual_login").length;
    const outreach = platforms.filter((p) => p.submission_mode === "email_outreach").length;
    const monitorOnly = platforms.filter((p) => p.submission_mode === "api_none").length;
    const socialProfiles = platforms.filter((p) => p.source_type === "social_profile").length;
    const highRisk = platforms.filter((p) => p.risk_level === "high").length;
    const withAccounts = platforms.filter((p) => p.accounts_count > 0).length;
    return { active, manual, outreach, monitorOnly, socialProfiles, highRisk, withAccounts };
  }, [platforms]);

  const visiblePlatforms = useMemo(() => {
    const q = platformQuery.trim().toLowerCase();
    return platforms.filter((platform) => {
      if (platformTypeFilter !== "all" && platform.source_type !== platformTypeFilter) return false;
      if (platformRiskFilter !== "all" && platform.risk_level !== platformRiskFilter) return false;
      if (!q) return true;
      return [
        platform.name,
        platform.domain,
        platform.source_type,
        platform.regions,
        platform.industry_tags,
        platform.submission_mode,
        platform.notes,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(q);
    });
  }, [platformQuery, platformRiskFilter, platformTypeFilter, platforms]);

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
    setNote("站外渠道已加入待处理列表。");
    loadGaps();
  }

  async function generateOpportunitiesFromSignals() {
    setError("");
    setNote("");
    setGeneratingOpportunities(true);
    try {
      const res = await api<OffsiteOpportunityGeneration>("/api/offsite/gaps/generate-from-signals", { method: "POST" });
      setNote(`${res.note} 新增 ${res.created} 条，跳过重复 ${res.skipped} 条；来源：GEO ${res.from_geo}，SEO ${res.from_seo}，站内 ${res.from_onsite}。`);
      loadGaps();
    } catch (e) {
      setError(e instanceof Error ? e.message : "生成站外机会失败");
    } finally {
      setGeneratingOpportunities(false);
    }
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
      payload_summary: gap.recommended_action || gap.notes || `围绕 ${gap.referring_domain} 推进站外曝光渠道维护。`,
      owner_hint: gap.owner_hint || "站外执行",
      result_url: gap.result_url || "",
    });
    setTab("distribution");
    setNote("已把该站外渠道带入执行任务表单。");
  }

  async function updateGap(id: string, payload: Record<string, string>) {
    setError("");
    setNote("");
    await api(`/api/offsite/gaps/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
    setNote("站外渠道状态已更新。");
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
    setNote("站外结果核验状态已更新。");
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
    setNote("跟进记录已加入该渠道。");
    loadGaps();
  }

  async function createJob(e: FormEvent) {
    e.preventDefault();
    setError("");
    setNote("");
    await api("/api/distribution/jobs", { method: "POST", body: JSON.stringify(distForm) });
    setDistForm({ ...distForm, gap_id: "", platform_id: "", account_id: "", content_asset_id: "", title: "", payload_summary: "", result_url: "" });
    setNote("执行任务已创建，等待人工确认执行。");
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
    setSeedBusy(true);
    try {
      const res = await api<SourcePlatformSeed>("/api/offsite/platforms/seed-b2b", { method: "POST", timeoutMs: 120000 });
      const apis = await api<{ created: number; updated: number }>("/api/offsite/platforms/seed-official-apis", { method: "POST", timeoutMs: 60000 });
      setPlatforms(res.platforms);
      loadPlatforms();
      setNote(`已导入 ${res.created} 个渠道，跳过 ${res.skipped} 个。官方接口挂上 ${apis.created + apis.updated} 处：客户自己跳转发，或用自己的钥匙调接口。`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "载入渠道失败");
    } finally {
      setSeedBusy(false);
    }
  }

  async function saveFactPack(e: FormEvent) {
    e.preventDefault();
    setError("");
    setNote("");
    const saved = await api<FactPack>("/api/offsite/fact-packs", { method: "POST", body: JSON.stringify(factForm) });
    setFactForm({ ...factForm, name: "Default Fact Pack", legal_name: "", brand_names: "", website: "", product_categories_en: "", certifications: "", key_specs: "", banned_claims: "", contact_public: "", approved_boilerplate_en: "" });
    setAssetForm((current) => ({ ...current, fact_pack_id: saved.id }));
    setNote("客户事实资料已保存，批准后才能生成对外内容草稿。");
    loadContent();
  }

  async function approveFactPack(id: string) {
    setError("");
    setNote("");
    await api(`/api/offsite/fact-packs/${id}/approve`, { method: "POST", body: JSON.stringify({ confirmed: true, note: "人工确认事实源" }) });
    setNote("客户事实资料已人工批准。");
    loadContent();
  }

  async function saveAsset(e: FormEvent) {
    e.preventDefault();
    setError("");
    setNote("");
    await api("/api/offsite/content-assets", { method: "POST", body: JSON.stringify(assetForm) });
    setAssetForm({ ...assetForm, title: "", body_md: "", keywords: "", entities: "" });
    setNote("对外提交文案已保存为草稿。");
    loadContent();
  }

  async function writeForChannel(platform: SourcePlatform) {
    const fact = factPacks.find((row) => row.status === "approved") ?? factPacks[0];
    if (!fact || fact.status !== "approved") {
      setError("先到「对外稿」填好客户事实并批准，才能让 AI 按这个渠道写一篇。");
      setTab("content");
      return;
    }
    setError("");
    setNote("");
    setWritingId(platform.id);
    try {
      await api("/api/offsite/content-assets/generate", {
        method: "POST",
        timeoutMs: 90000,
        body: JSON.stringify({
          fact_pack_id: fact.id,
          asset_type: platform.source_type === "social_profile" ? "social_snippet" : "company_blurb",
          title: `${platform.name} 发布稿`,
          locale: "en",
        }),
      });
      setNote(`已为 ${platform.name} 写了一篇草稿。人看过再发，软件不会自己登号发出去。`);
      loadContent();
    } catch (e) {
      setError(e instanceof Error ? e.message : "写稿失败");
    } finally {
      setWritingId("");
    }
  }

  function queueOnChannel(platform: SourcePlatform) {
    const draft = assets.find((asset) => asset.title.includes(platform.name));
    setDistForm({
      gap_id: "",
      platform_id: platform.id,
      account_id: accounts.find((row) => row.platform_id === platform.id)?.id || "",
      content_asset_id: draft?.id || "",
      title: `在 ${platform.name} 发一篇`,
      target_url: "/",
      provider_key: connectors.find((row) => row.platform_id === platform.id)?.provider_key || providers[0]?.key || "directory",
      task_type: platform.source_type === "social_profile" ? "social_post_plan" : "profile_update",
      payload_summary: draft ? draft.body_md.slice(0, 400) : `用 AI 稿在 ${platform.name} 发出。人登号或走接口，不自动群发。`,
      owner_hint: "客户经理",
      result_url: "",
    });
    setTab("distribution");
    setNote(`已把 ${platform.name} 带到执行记录。发出去后把结果链接填上。`);
  }

  async function generateAsset() {
    if (!assetForm.fact_pack_id) {
      setError("请先选择已批准的客户事实资料。");
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
    setNote("已基于客户事实资料生成内容草稿。");
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
    setNote("对外提交文案已人工批准，可以绑定到执行任务。");
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
    setNote("平台接入方式已登记。后续真实 API 或授权会接到这里。");
    loadPlatforms();
  }

  async function submitResult(job: DistJob) {
    const resultUrl = (resultForms[job.id] ?? job.result_url ?? "").trim();
    if (!resultUrl) {
      setError("请先填写结果页面 URL，再记录站外结果。");
      return;
    }
    setError("");
    setNote("");
    await api(`/api/distribution/jobs/${job.id}/submit-result`, {
      method: "POST",
      body: JSON.stringify({ result_url: resultUrl, verify_status: "pending", evidence: "人工提交结果页面 URL，等待站外结果核验。" }),
    });
    setNote("结果页面 URL 已记录，并已回写到原始站外渠道。");
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
      <SummaryHeader stats={stats} platformsCount={platforms.length} />
      {note ? <p className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{note}</p> : null}
      {error ? <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}

      <TabNav tab={tab} setTab={setTab} />

      {tab === "channels" ? (
        <ChannelCards
          platforms={platforms}
          accounts={accounts}
          connectors={connectors}
          jobs={jobs}
          assets={assets}
          seedPlatforms={seedPlatforms}
          seedBusy={seedBusy}
          writeForChannel={writeForChannel}
          queueOnChannel={queueOnChannel}
          writingId={writingId}
        />
      ) : null}

      {tab === "opportunities" ? (
        <OpportunitiesTab
          gaps={gaps}
          contact={contact}
          setContact={setContact}
          aiGap={aiGap}
          addOutreach={addOutreach}
          prepareJobFromGap={prepareJobFromGap}
          updateGap={updateGap}
          form={form}
          setForm={setForm}
          addGap={addGap}
          generateOpportunitiesFromSignals={generateOpportunitiesFromSignals}
          generatingOpportunities={generatingOpportunities}
        />
      ) : null}

      {tab === "distribution" ? (
        <DistributionTab
          providers={providers}
          jobs={jobs}
          guides={guides}
          placementChecks={placementChecks}
          resultForms={resultForms}
          setResultForms={setResultForms}
          submitResult={submitResult}
          loadGuide={loadGuide}
          checkPlacement={checkPlacement}
          recordDistribution={recordDistribution}
          distForm={distForm}
          setDistForm={setDistForm}
          gaps={gaps}
          platforms={platforms}
          accounts={accounts}
          assets={assets}
          createJob={createJob}
        />
      ) : null}

      {tab === "placements" ? (
        <PlacementsTab gaps={gaps} filter={filter} setFilter={setFilter} visibleGaps={visibleGaps} setVerify={setVerify} />
      ) : null}

      {tab === "content" ? (
        <ContentTab
          factPacks={factPacks}
          assets={assets}
          approveFactPack={approveFactPack}
          reviewAsset={reviewAsset}
          approveAsset={approveAsset}
          factForm={factForm}
          setFactForm={setFactForm}
          saveFactPack={saveFactPack}
          assetForm={assetForm}
          setAssetForm={setAssetForm}
          generateAsset={generateAsset}
          saveAsset={saveAsset}
        />
      ) : null}

      {tab === "platforms" ? (
        <PlatformsTab
          platforms={platforms}
          platformStats={platformStats}
          seedPlatforms={seedPlatforms}
          seedBusy={seedBusy}
          platformQuery={platformQuery}
          setPlatformQuery={setPlatformQuery}
          platformTypeFilter={platformTypeFilter}
          setPlatformTypeFilter={setPlatformTypeFilter}
          platformRiskFilter={platformRiskFilter}
          setPlatformRiskFilter={setPlatformRiskFilter}
          visiblePlatforms={visiblePlatforms}
          accounts={accounts}
          connectors={connectors}
          platformForm={platformForm}
          setPlatformForm={setPlatformForm}
          createPlatform={createPlatform}
          accountForm={accountForm}
          setAccountForm={setAccountForm}
          createAccount={createAccount}
          connectorForm={connectorForm}
          setConnectorForm={setConnectorForm}
          createConnector={createConnector}
        />
      ) : null}

    </div>
  );
}
