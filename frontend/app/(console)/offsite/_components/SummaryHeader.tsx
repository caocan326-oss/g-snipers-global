import { Bot, ClipboardList, Link2, RadioTower, RefreshCw, Send } from "lucide-react";

import { Badge } from "@/components/ui/badge";

import { StatTile } from "./StatTile";
import { WorkflowStep } from "./WorkflowStep";

type Stats = {
  activeOpportunities: number;
  validPlacements: number;
  needsReview: number;
  openJobs: number;
  approvedAssets: number;
};

type PlatformStats = {
  active: number;
  manual: number;
  outreach: number;
  monitorOnly: number;
  socialProfiles: number;
  highRisk: number;
  withAccounts: number;
};

export function SummaryHeader({
  stats,
  platformStats,
  platformsCount,
}: {
  stats: Stats;
  platformStats: PlatformStats;
  platformsCount: number;
}) {
  return (
    <>
      <section className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div className="max-w-4xl">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="brand">站外曝光</Badge>
              <Badge tone="amber">人工确认后执行</Badge>
            </div>
            <h1 className="mt-3 text-2xl font-semibold text-slate-950">站外曝光工作台</h1>
            <p className="mt-2 text-sm leading-6 text-slate-500">
              管理客户官网之外的海外公开阵地：LinkedIn、X、YouTube、Facebook、Instagram、B2B 平台、行业目录、协会、媒体和分销商页面。
              先判断哪些渠道值得维护，再准备客户确认过的对外材料，人工执行后核验结果页面是否真实存在并复测效果。
              当前不会自动群发、不会冒充权重数据，所有外部发布都需要人工确认。
            </p>
          </div>
          <div className="grid w-full gap-2 sm:grid-cols-2 xl:w-[420px]">
            <StatTile label="待处理渠道" value={stats.activeOpportunities} helper="待判断、跟进中或已有回复的站外渠道" />
            <StatTile label="有效站外结果" value={stats.validPlacements} helper="已核验存在的第三方提及或外链" />
          </div>
        </div>
      </section>

      <section className="grid gap-3 lg:grid-cols-6">
        <WorkflowStep icon={RadioTower} title="可维护平台" value={platformsCount} helper="社媒主页、B2B 平台、目录、协会和媒体" />
        <WorkflowStep icon={ClipboardList} title="待处理渠道" value={stats.activeOpportunities} helper="先判断价值，再安排维护或跟进" />
        <WorkflowStep icon={Bot} title="对外材料" value={stats.approvedAssets} helper="已人工批准、可用于平台提交的文案" />
        <WorkflowStep icon={Send} title="执行任务" value={stats.openJobs} helper="待人工确认的提交、投稿或联系任务" />
        <WorkflowStep icon={Link2} title="站外结果" value={stats.validPlacements} helper="真实存在、可被客户复核的证据页面" />
        <WorkflowStep icon={RefreshCw} title="社媒主页" value={platformStats.socialProfiles} helper="LinkedIn、X、YouTube 等基础阵地" />
      </section>
    </>
  );
}
