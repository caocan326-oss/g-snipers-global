import { FormEvent } from "react";
import { Bot, ExternalLink, RefreshCw, Wand2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { BacklinkGap } from "@/lib/api";

import { gapLabel, kindLabel, verifyLabel, verifyTone } from "../_helpers";

type GapForm = {
  title: string;
  issue_type: string;
  priority: string;
  owner_hint: string;
  competitor_name: string;
  referring_domain: string;
  link_url: string;
  kind: string;
  acceptance_criteria: string;
  recommended_action: string;
  retest_method: string;
  notes: string;
};

export function OpportunitiesTab({
  gaps,
  contact,
  setContact,
  aiGap,
  addOutreach,
  prepareJobFromGap,
  updateGap,
  form,
  setForm,
  addGap,
  generateOpportunitiesFromSignals,
  generatingOpportunities,
}: {
  gaps: BacklinkGap[];
  contact: string;
  setContact: (value: string) => void;
  aiGap: (id: string) => void;
  addOutreach: (gapId: string) => void;
  prepareJobFromGap: (gap: BacklinkGap) => void;
  updateGap: (id: string, payload: Record<string, string>) => void;
  form: GapForm;
  setForm: (form: GapForm) => void;
  addGap: (e: FormEvent) => void;
  generateOpportunitiesFromSignals: () => void;
  generatingOpportunities: boolean;
}) {
  const sourceLabel: Record<string, string> = {
    geo: "来自 GEO",
    seo: "来自 SEO 表现",
    onsite: "来自站内诊断",
    manual: "手动登记",
  };
  const issueTypeLabel: Record<string, string> = {
    competitor_gap: "竞品有我无",
    unlinked_mention: "未链接提及",
    lost_link: "已获链接失效",
    authority_source: "权威第三方源缺失",
    social_profile: "官方社媒主页维护",
    monitor_only: "仅监控",
    geo_citation_gap: "AI 引用缺口",
    onsite_content_gap: "内容素材缺口",
    seo_keyword_gap: "搜索表现缺口",
    serp_visibility_gap: "SERP 可见度缺口",
  };

  return (
    <section className="grid gap-5 xl:grid-cols-[1fr_360px]">
      <div className="space-y-3">
        <Card className="rounded-md border-brand-100 bg-brand-50/50">
          <CardContent className="flex flex-col gap-3 p-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-950">
                <Wand2 className="h-4 w-4 text-brand-700" />
                从检查记录里捡线索
              </div>
              <p className="mt-1 text-sm leading-6 text-slate-600">
                这里不是发帖入口。要发新媒体，回「渠道卡片」。这里只把检查里看到的站外缺口记下来。
              </p>
            </div>
            <Button onClick={generateOpportunitiesFromSignals} disabled={generatingOpportunities}>
              <RefreshCw className={`mr-1.5 h-4 w-4 ${generatingOpportunities ? "animate-spin" : ""}`} />
              {generatingOpportunities ? "正在整理" : "整理线索"}
            </Button>
          </CardContent>
        </Card>

        {gaps.length ? (
          gaps.map((g) => (
            <Card key={g.id} className="rounded-md">
              <CardHeader className="flex flex-row items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <CardTitle>{g.title || g.referring_domain}</CardTitle>
                    <Badge tone={g.priority === "P0" || g.priority === "P1" ? "red" : g.priority === "P2" ? "amber" : "default"}>{g.priority}</Badge>
                    <Badge tone={g.source === "manual" ? "default" : "brand"}>{sourceLabel[g.source] ?? g.source}</Badge>
                    <Badge>{issueTypeLabel[g.issue_type] ?? g.issue_type}</Badge>
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
                    <p className="mt-1 text-sm leading-5 text-slate-700">{g.recommended_action || "待补充：判断该渠道是否值得维护、认领、提交资料或持续监控。"}</p>
                  </div>
                  <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                    <div className="text-xs font-medium text-slate-500">验收标准</div>
                    <p className="mt-1 text-sm leading-5 text-slate-700">{g.acceptance_criteria || "记录结果页面 URL，并完成上线结果核验。"}</p>
                  </div>
                  <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                    <div className="text-xs font-medium text-slate-500">负责人</div>
                    <p className="mt-1 text-sm leading-5 text-slate-700">{g.owner_hint || "未指定"}</p>
                  </div>
                  <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                    <div className="text-xs font-medium text-slate-500">复测方式</div>
                    <p className="mt-1 text-sm leading-5 text-slate-700">{g.retest_method || "复查结果页面是否可访问、是否提及客户、是否链接到目标页。"}</p>
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
                    创建执行任务
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
            还没有待处理渠道。可以先登记 LinkedIn/X/YouTube 等客户官方主页、竞品出现的平台、行业目录、媒体提及、协会页面、测评文章或客户案例页面。
          </p>
        )}
      </div>

      <Card className="h-fit rounded-md">
        <CardHeader>
          <CardTitle>登记曝光渠道或平台问题</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-3" onSubmit={addGap}>
            <Input
              placeholder="标题，例如：LinkedIn 公司主页资料未补全"
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
                <option value="social_profile">官方社媒主页维护</option>
                <option value="monitor_only">仅监控</option>
              </select>
              <select
                className="h-10 w-full rounded-md border border-slate-200 px-3 text-sm"
                value={form.priority}
                onChange={(e) => setForm({ ...form, priority: e.target.value })}
              >
                <option value="P1">P1 高优先级</option>
                <option value="P2">P2 常规维护</option>
                <option value="P3">P3 观察</option>
                <option value="P0">P0 立即处理</option>
              </select>
            </div>
            <select
              className="h-10 w-full rounded-md border border-slate-200 px-3 text-sm"
              value={form.kind}
              onChange={(e) => setForm({ ...form, kind: e.target.value })}
            >
              <option value="competitor">竞品已覆盖</option>
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
              placeholder="验收标准，例如：资料页上线并记录结果页面 URL"
              value={form.acceptance_criteria}
              onChange={(e) => setForm({ ...form, acceptance_criteria: e.target.value })}
            />
            <Input
              placeholder="复测方式，例如：检查页面可访问、链接属性和品牌提及"
              value={form.retest_method}
              onChange={(e) => setForm({ ...form, retest_method: e.target.value })}
            />
            <Input placeholder="价值判断或备注" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
            <Button type="submit" className="w-full">加入待处理渠道</Button>
          </form>
        </CardContent>
      </Card>
    </section>
  );
}
