import { FormEvent } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { BacklinkGap, ContentAsset, DistGuide, DistJob, DistProvider, PlacementCheck, SourcePlatform, PlatformAccount } from "@/lib/api";

import { jobStatusLabel, taskTypeLabel } from "../_helpers";

type DistForm = {
  gap_id: string;
  platform_id: string;
  account_id: string;
  content_asset_id: string;
  title: string;
  target_url: string;
  provider_key: string;
  task_type: string;
  payload_summary: string;
  owner_hint: string;
  result_url: string;
};

export function DistributionTab({
  providers,
  jobs,
  guides,
  placementChecks,
  resultForms,
  setResultForms,
  submitResult,
  loadGuide,
  checkPlacement,
  recordDistribution,
  distForm,
  setDistForm,
  gaps,
  platforms,
  accounts,
  assets,
  createJob,
}: {
  providers: DistProvider[];
  jobs: DistJob[];
  guides: Record<string, DistGuide>;
  placementChecks: Record<string, PlacementCheck>;
  resultForms: Record<string, string>;
  setResultForms: (forms: Record<string, string>) => void;
  submitResult: (job: DistJob) => void;
  loadGuide: (jobId: string) => void;
  checkPlacement: (jobId: string) => void;
  recordDistribution: (id: string, confirmed: boolean) => void;
  distForm: DistForm;
  setDistForm: (form: DistForm) => void;
  gaps: BacklinkGap[];
  platforms: SourcePlatform[];
  accounts: PlatformAccount[];
  assets: ContentAsset[];
  createJob: (e: FormEvent) => void;
}) {
  return (
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
                      {j.gap_id ? <Badge tone="blue">已绑定渠道</Badge> : null}
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
                      placeholder="结果页面 URL"
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
            还没有执行任务。先把社媒主页维护、B2B 平台资料、案例、新闻稿、行业问答或目录资料加入队列，再由人工确认执行。
          </p>
        )}
      </div>

      <Card className="h-fit rounded-md">
        <CardHeader>
          <CardTitle>新建执行任务</CardTitle>
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
              <option value="">不绑定渠道，手工任务</option>
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
              <option value="">不绑定对外提交文案</option>
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
  );
}
