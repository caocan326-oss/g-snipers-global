import { ExternalLink, KeyRound, PenLine, Radio } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { ContentAsset, DistJob, PlatformAccount, PlatformConnector, SourcePlatform } from "@/lib/api";

import { platformTypeLabel } from "../_helpers";

function sendWay(platform: SourcePlatform, connector?: PlatformConnector, account?: PlatformAccount) {
  if (connector && (connector.status === "ready" || connector.auth_mode === "api")) return "接口可发";
  if (platform.has_official_api) return "可接官方接口";
  if (account) return "已记下账号，自己登号发";
  if (platform.submission_mode === "manual_login") return "自己登号发";
  if (platform.submission_mode === "form_public") return "填公开表单";
  if (platform.submission_mode === "email_outreach") return "邮件联系";
  return "人工发出";
}

export function ChannelCards({
  platforms,
  accounts,
  connectors,
  jobs,
  assets,
  seedPlatforms,
  seedBusy,
  writeForChannel,
  queueOnChannel,
  writingId,
}: {
  platforms: SourcePlatform[];
  accounts: PlatformAccount[];
  connectors: PlatformConnector[];
  jobs: DistJob[];
  assets: ContentAsset[];
  seedPlatforms: () => void;
  seedBusy?: boolean;
  writeForChannel: (platform: SourcePlatform) => void;
  queueOnChannel: (platform: SourcePlatform) => void;
  writingId: string;
}) {
  const social = platforms.filter((p) => p.source_type === "social_profile");
  const others = platforms.filter((p) => p.source_type !== "social_profile");
  const groups = [
    { title: "新媒体", rows: social },
    { title: "目录 / 平台 / 媒体", rows: others },
  ];

  if (!platforms.length) {
    return (
      <Card className="rounded-md">
        <CardContent className="space-y-3 p-6">
          <h2 className="text-lg font-semibold text-slate-950">还没有渠道卡片</h2>
          <p className="text-sm leading-6 text-slate-500">
            一张卡片就是一个渠道。客户想发 LinkedIn、Facebook 或行业目录，点那张卡：AI 写稿、加上关键词，人用接口或自己登号发出去。不自动群发。
          </p>
          <Button onClick={seedPlatforms} disabled={seedBusy}>
            {seedBusy ? "载入中…" : "载入常用渠道"}
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-500">
        想发哪个就点哪张。AI 写文章、加关键词；发出去用他们的接口，或自己登号。内置浏览器还没做。
      </p>
      {groups.map((group) =>
        group.rows.length ? (
          <section key={group.title} className="space-y-3">
            <h2 className="text-sm font-semibold text-slate-800">{group.title}</h2>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {group.rows.map((platform) => {
                const account = accounts.find((row) => row.platform_id === platform.id);
                const connector = connectors.find((row) => row.platform_id === platform.id);
                const channelJobs = jobs.filter((job) => job.platform_id === platform.id);
                const drafts = assets.filter((asset) => asset.title.includes(platform.name)).length;
                return (
                  <Card key={platform.id} className="rounded-md">
                    <CardContent className="space-y-3 p-4">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="font-semibold text-slate-950">{platform.name}</div>
                          <p className="mt-1 text-xs text-slate-500">{platform.domain}</p>
                        </div>
                        <Badge>{platformTypeLabel[platform.source_type] ?? platform.source_type}</Badge>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        <Badge tone="blue">{sendWay(platform, connector, account)}</Badge>
                        {platform.has_official_api || platform.api_endpoint ? <Badge tone="green">官方接口可自己接</Badge> : <Badge tone="default">内置浏览器稍后</Badge>}
                      </div>
                      {platform.industry_tags ? (
                        <p className="text-xs leading-5 text-slate-500">关键词：{platform.industry_tags}</p>
                      ) : null}
                      <p className="text-xs text-slate-400">
                        稿 {drafts} · 待发 {channelJobs.filter((job) => !["sent", "done", "cancelled"].includes(job.status)).length}
                      </p>
                      <div className="flex flex-wrap gap-2">
                        <Button size="sm" onClick={() => writeForChannel(platform)} disabled={writingId === platform.id}>
                          <PenLine className="mr-1 h-3.5 w-3.5" />
                          {writingId === platform.id ? "在写…" : "AI 写一篇"}
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => queueOnChannel(platform)}>
                          <Radio className="mr-1 h-3.5 w-3.5" />
                          记下要发
                        </Button>
                        {platform.compose_url ? (
                          <a href={platform.compose_url} target="_blank" rel="noreferrer" className="inline-flex">
                            <Button size="sm" variant="outline">去官网发</Button>
                          </a>
                        ) : platform.base_url ? (
                          <a href={platform.base_url} target="_blank" rel="noreferrer" className="inline-flex">
                            <Button size="sm" variant="ghost">
                              <ExternalLink className="mr-1 h-3.5 w-3.5" />
                              打开
                            </Button>
                          </a>
                        ) : null}
                        {platform.docs_url ? (
                          <a href={platform.docs_url} target="_blank" rel="noreferrer" className="inline-flex">
                            <Button size="sm" variant="ghost">自己的接口说明</Button>
                          </a>
                        ) : null}
                        {account ? (
                          <span className="inline-flex items-center gap-1 text-xs text-slate-500">
                            <KeyRound className="h-3.5 w-3.5" />
                            {account.label || account.login_identifier}
                          </span>
                        ) : null}
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </section>
        ) : null
      )}
    </div>
  );
}
