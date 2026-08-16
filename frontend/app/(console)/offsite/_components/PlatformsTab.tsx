import { FormEvent } from "react";
import { Search } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { PlatformAccount, PlatformConnector, SourcePlatform } from "@/lib/api";

import { platformTypeLabel, submissionLabel } from "../_helpers";

type PlatformStats = {
  active: number;
  manual: number;
  outreach: number;
  monitorOnly: number;
  socialProfiles: number;
  highRisk: number;
  withAccounts: number;
};

type PlatformForm = {
  platform_key: string;
  name: string;
  domain: string;
  source_type: string;
  regions: string;
  industry_tags: string;
  base_url: string;
  listing_model: string;
  submission_mode: string;
  has_official_api: boolean;
  risk_level: string;
  status: string;
  notes: string;
};

type AccountForm = {
  platform_id: string;
  label: string;
  login_identifier: string;
  auth_method: string;
  vault_ref: string;
  owner_hint: string;
  scope: string;
  status: string;
  risk_level: string;
  regions_allowed: string;
  notes: string;
};

type ConnectorForm = {
  platform_id: string;
  provider_key: string;
  auth_mode: string;
  capabilities: string;
  status: string;
  env_var: string;
  notes: string;
};

export function PlatformsTab({
  platforms,
  platformStats,
  seedPlatforms,
  platformQuery,
  setPlatformQuery,
  platformTypeFilter,
  setPlatformTypeFilter,
  platformRiskFilter,
  setPlatformRiskFilter,
  visiblePlatforms,
  accounts,
  connectors,
  platformForm,
  setPlatformForm,
  createPlatform,
  accountForm,
  setAccountForm,
  createAccount,
  connectorForm,
  setConnectorForm,
  createConnector,
}: {
  platforms: SourcePlatform[];
  platformStats: PlatformStats;
  seedPlatforms: () => void;
  platformQuery: string;
  setPlatformQuery: (value: string) => void;
  platformTypeFilter: string;
  setPlatformTypeFilter: (value: string) => void;
  platformRiskFilter: string;
  setPlatformRiskFilter: (value: string) => void;
  visiblePlatforms: SourcePlatform[];
  accounts: PlatformAccount[];
  connectors: PlatformConnector[];
  platformForm: PlatformForm;
  setPlatformForm: (form: PlatformForm) => void;
  createPlatform: (e: FormEvent) => void;
  accountForm: AccountForm;
  setAccountForm: (form: AccountForm) => void;
  createAccount: (e: FormEvent) => void;
  connectorForm: ConnectorForm;
  setConnectorForm: (form: ConnectorForm) => void;
  createConnector: (e: FormEvent) => void;
}) {
  return (
    <section className="grid gap-5 xl:grid-cols-[1fr_420px]">
      <div className="space-y-4">
        <div className="rounded-md border border-slate-200 bg-white p-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="font-semibold text-slate-950">主流平台主页与渠道库</h2>
              <p className="mt-1 text-sm leading-6 text-slate-500">
                先导入 LinkedIn、X、YouTube、Facebook、Instagram、TikTok、Pinterest、Google Business 和出口 B2B 权威源，再按客户行业补充垂直目录、协会、分销商和媒体。导入不会覆盖已有平台。
              </p>
            </div>
            <Button type="button" onClick={seedPlatforms}>导入主流平台</Button>
          </div>
          <div className="mt-4 grid gap-2 sm:grid-cols-3 xl:grid-cols-6">
            <div className="rounded-md bg-slate-50 p-3 text-sm"><div className="text-xs text-slate-500">平台总数</div><div className="mt-1 font-semibold">{platforms.length}</div></div>
            <div className="rounded-md bg-slate-50 p-3 text-sm"><div className="text-xs text-slate-500">可运营</div><div className="mt-1 font-semibold">{platformStats.active}</div></div>
            <div className="rounded-md bg-slate-50 p-3 text-sm"><div className="text-xs text-slate-500">人工登录</div><div className="mt-1 font-semibold">{platformStats.manual}</div></div>
            <div className="rounded-md bg-slate-50 p-3 text-sm"><div className="text-xs text-slate-500">邮件联系</div><div className="mt-1 font-semibold">{platformStats.outreach}</div></div>
            <div className="rounded-md bg-slate-50 p-3 text-sm"><div className="text-xs text-slate-500">社媒主页</div><div className="mt-1 font-semibold">{platformStats.socialProfiles}</div></div>
            <div className="rounded-md bg-slate-50 p-3 text-sm"><div className="text-xs text-slate-500">高风险</div><div className="mt-1 font-semibold">{platformStats.highRisk}</div></div>
          </div>
          <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-900">
            自动化边界：系统可以整理平台资料、生成待审文案、打开执行页、记录结果 URL、自动核验链接；不自动注册账号、不绕验证码、不自动群发、不自动购买链接或媒体位。
          </div>
          <div className="mt-4 grid gap-3 xl:grid-cols-[1fr_180px_160px]">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <Input
                className="pl-9"
                placeholder="搜索平台、域名、区域、行业标签或提交规则"
                value={platformQuery}
                onChange={(e) => setPlatformQuery(e.target.value)}
              />
            </div>
            <select className="h-10 rounded-md border border-slate-200 px-3 text-sm" value={platformTypeFilter} onChange={(e) => setPlatformTypeFilter(e.target.value)}>
              <option value="all">全部类型</option>
              {Object.entries(platformTypeLabel).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
            </select>
            <select className="h-10 rounded-md border border-slate-200 px-3 text-sm" value={platformRiskFilter} onChange={(e) => setPlatformRiskFilter(e.target.value)}>
              <option value="all">全部风险</option>
              <option value="low">低风险</option>
              <option value="medium">中风险</option>
              <option value="high">高风险</option>
            </select>
          </div>
        </div>
        <div className="grid gap-3 lg:grid-cols-2">
          {visiblePlatforms.map((p) => (
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
                  <span>类型：{platformTypeLabel[p.source_type] ?? p.source_type}</span>
                  <span>提交：{submissionLabel[p.submission_mode] ?? p.submission_mode}</span>
                  <span>账号：{p.accounts_count}</span>
                  <span>接入方式：{p.connectors_count}</span>
                  <span>区域：{p.regions || "未填"}</span>
                  <span>风险：{p.risk_level}</span>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {(p.industry_tags || "").split(",").map((tag) => tag.trim()).filter(Boolean).slice(0, 4).map((tag) => (
                    <Badge key={tag} tone="blue">{tag}</Badge>
                  ))}
                  {p.has_official_api ? <Badge tone="green">官方 API</Badge> : <Badge>无提交 API</Badge>}
                </div>
                {p.notes ? <p className="mt-3 text-sm leading-6 text-slate-600">{p.notes}</p> : null}
              </CardContent>
            </Card>
          ))}
          {visiblePlatforms.length === 0 ? (
            <div className="rounded-md border border-dashed border-slate-200 bg-white p-5 text-sm text-slate-500 lg:col-span-2">
              当前筛选下没有平台。可以清空筛选，或新增客户需要维护的 LinkedIn、X、YouTube、B2B 平台、行业目录、协会、分销商页面。
            </div>
          ) : null}
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
          <CardHeader><CardTitle>平台接入方式</CardTitle></CardHeader>
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
            )) : <p className="text-sm text-slate-500">还没有接入方式。没有官方 API 的平台保持人工处理。</p>}
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
                  <option value="community">问答/社区</option>
                  <option value="social_profile">社媒主页</option>
                  <option value="knowledge_graph">实体/知识图谱</option>
                  <option value="monitoring">核验/监控</option>
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
          <CardHeader><CardTitle>新增平台接入方式</CardTitle></CardHeader>
          <CardContent>
            <form className="space-y-3" onSubmit={createConnector}>
              <select className="h-10 w-full rounded-md border border-slate-200 px-3 text-sm" value={connectorForm.platform_id} onChange={(e) => setConnectorForm({ ...connectorForm, platform_id: e.target.value })} required>
                <option value="">选择平台</option>
                {platforms.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
              <Input placeholder="接入方式 key，例如 wordpress / gmail / manual_browser" value={connectorForm.provider_key} onChange={(e) => setConnectorForm({ ...connectorForm, provider_key: e.target.value })} required />
              <Input placeholder="能力，例如 draft_only,publish,sync_status" value={connectorForm.capabilities} onChange={(e) => setConnectorForm({ ...connectorForm, capabilities: e.target.value })} />
              <Input placeholder="环境变量名（可选）" value={connectorForm.env_var} onChange={(e) => setConnectorForm({ ...connectorForm, env_var: e.target.value })} />
              <Input placeholder="备注" value={connectorForm.notes} onChange={(e) => setConnectorForm({ ...connectorForm, notes: e.target.value })} />
              <Button type="submit" className="w-full">保存接入方式</Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
